"""Cost-aware cascade router with multi-provider failover.

Pipeline (see docs/architecture.md):
    cache -> tier selection (by difficulty) -> provider selection w/ failover
          -> budget gate -> telemetry (the RouteDecision)

The cascade is conservative: when the difficulty estimate is uncertain, route
*up* a tier, never down (ADR-0002). The quality floor is never breached — the
router degrades for availability or budget only within tiers >= the floor.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence

from src.budget import BudgetPolicy, BudgetVerdict
from src.cache import ResponseCache
from src.cost import estimate_cost
from src.providers import DEFAULT_PROVIDERS, Provider
from src.request import InferenceRequest, ModelTier

CONFIDENCE_THRESHOLD = 0.70


@dataclass(frozen=True)
class RouteDecision:
    """The router's output and the per-request telemetry record (ADR-0001)."""

    served: bool
    tier: Optional[ModelTier]
    provider: Optional[str]
    estimated_cost: Decimal
    reason: str
    cache_hit: bool = False
    degraded: bool = False
    budget_verdict: str = "ALLOW"


def _base_tier(difficulty: float) -> ModelTier:
    if difficulty < 0.34:
        return ModelTier.CHEAP
    if difficulty < 0.67:
        return ModelTier.MID
    return ModelTier.STRONG


def select_tier(req: InferenceRequest) -> tuple[ModelTier, str]:
    """Pick a tier from difficulty. Conservative: escalate up when unsure."""
    tier = _base_tier(req.difficulty)
    reason = f"difficulty {req.difficulty:.2f} -> {tier.name}"

    if req.difficulty_confidence < CONFIDENCE_THRESHOLD and tier < ModelTier.STRONG:
        tier = ModelTier(tier + 1)
        reason += (
            f"; low confidence {req.difficulty_confidence:.2f} -> escalated up to {tier.name}"
        )

    if tier < req.required_quality:
        tier = req.required_quality
        reason += f"; raised to required quality floor {tier.name}"

    return tier, reason


class Router:
    def __init__(
        self,
        providers: Sequence[Provider] = DEFAULT_PROVIDERS,
        budget: Optional[BudgetPolicy] = None,
        cache: Optional[ResponseCache] = None,
    ):
        self._providers = list(providers)
        self._budget = budget or BudgetPolicy(per_request_ceiling=Decimal("0.0030"))
        self._cache = cache

    # --- provider selection -------------------------------------------------
    def _cheapest_in_tier(
        self, req: InferenceRequest, tier: ModelTier
    ) -> Optional[tuple[Provider, Decimal]]:
        candidates = [
            p
            for p in self._providers
            if p.tier == tier and p.healthy and p.p50_latency_ms <= req.latency_budget_ms
        ]
        if not candidates:
            return None
        priced = [(p, estimate_cost(req, p)) for p in candidates]
        return min(priced, key=lambda pair: pair[1])

    def _tiers_in_pref_order(self, desired: ModelTier, floor: ModelTier) -> list[ModelTier]:
        # Prefer the desired tier, then escalate up (preserves quality), then
        # down toward the floor as a last resort. Never below the floor.
        order = [desired]
        order += [ModelTier(t) for t in range(int(desired) + 1, int(ModelTier.STRONG) + 1)]
        order += [ModelTier(t) for t in range(int(desired) - 1, int(floor) - 1, -1)]
        return order

    def _select_available(
        self, req: InferenceRequest, desired: ModelTier, floor: ModelTier
    ) -> Optional[tuple[Provider, Decimal, ModelTier]]:
        for tier in self._tiers_in_pref_order(desired, floor):
            pick = self._cheapest_in_tier(req, tier)
            if pick is not None:
                return pick[0], pick[1], tier
        return None

    # --- the pipeline -------------------------------------------------------
    def serve(self, req: InferenceRequest) -> RouteDecision:
        # 1. Cache: an exact hit short-circuits everything at zero cost.
        if self._cache is not None and self._cache.get(req.cache_key) is not None:
            return RouteDecision(
                served=True, tier=None, provider="cache", estimated_cost=Decimal("0"),
                reason="exact cache hit within TTL", cache_hit=True,
            )

        # 2. Tier selection.
        desired, reason = select_tier(req)
        floor = req.required_quality

        # 3. Provider selection with availability failover.
        selected = self._select_available(req, desired, floor)
        if selected is None:
            return RouteDecision(
                served=False, tier=None, provider=None, estimated_cost=Decimal("0"),
                reason=reason + "; no healthy in-SLA provider at or above the quality floor",
            )
        provider, cost, tier = selected
        degraded = tier != desired

        # 4. Budget gate.
        verdict, breason = self._budget.check(req, cost)
        if verdict is BudgetVerdict.ALLOW:
            return RouteDecision(
                served=True, tier=tier, provider=provider.name, estimated_cost=cost,
                reason=f"{reason}; {breason}", degraded=degraded, budget_verdict="ALLOW",
            )
        if verdict is BudgetVerdict.BLOCK:
            return RouteDecision(
                served=False, tier=tier, provider=None, estimated_cost=cost,
                reason=f"{reason}; BLOCKED: {breason}", degraded=degraded, budget_verdict="BLOCK",
            )

        # 5. DOWNGRADE: walk down tiers toward the floor for a route within budget.
        for t in range(int(tier) - 1, int(floor) - 1, -1):
            cand = self._cheapest_in_tier(req, ModelTier(t))
            if cand is None:
                continue
            p2, c2 = cand
            v2, r2 = self._budget.check(req, c2)
            if v2 is BudgetVerdict.ALLOW:
                return RouteDecision(
                    served=True, tier=ModelTier(t), provider=p2.name, estimated_cost=c2,
                    reason=f"{reason}; over budget at {tier.name}, downgraded to {ModelTier(t).name}",
                    degraded=True, budget_verdict="DOWNGRADE",
                )
            if v2 is BudgetVerdict.BLOCK:
                return RouteDecision(
                    served=False, tier=ModelTier(t), provider=None, estimated_cost=c2,
                    reason=f"{reason}; BLOCKED: {r2}", degraded=True, budget_verdict="BLOCK",
                )

        # 6. No tier at or above the floor fits the budget -> block, don't serve below the bar.
        return RouteDecision(
            served=False, tier=tier, provider=None, estimated_cost=cost,
            reason=f"{reason}; BLOCKED: cannot meet budget without dropping below quality floor",
            degraded=degraded, budget_verdict="BLOCK",
        )
