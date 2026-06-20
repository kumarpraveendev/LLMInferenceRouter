"""Deterministic quality invariants for routing decisions (ADR-0007).

Hard pass/fail checks on the things a cost change must never silently break.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.budget import BudgetPolicy
from src.providers import Provider
from src.request import InferenceRequest
from src.router import RouteDecision


@dataclass(frozen=True)
class InvariantResult:
    name: str
    passed: bool
    detail: str


def served_meets_quality_floor(req, decision, providers, policy) -> InvariantResult:
    ok = True
    detail = "ok"
    if decision.served and decision.tier is not None and not decision.cache_hit:
        ok = decision.tier >= req.required_quality
        if not ok:
            detail = f"served at {decision.tier.name}, below floor {req.required_quality.name}"
    return InvariantResult("served_meets_quality_floor", ok, detail)


def served_within_ceiling(req, decision, providers, policy) -> InvariantResult:
    ok = True
    detail = "ok"
    if decision.served and not decision.cache_hit:
        ceiling = policy.ceiling_for(req)
        ok = decision.estimated_cost <= ceiling
        if not ok:
            detail = f"served cost {decision.estimated_cost} over ceiling {ceiling}"
    return InvariantResult("served_within_ceiling", ok, detail)


def blocked_is_not_served(req, decision, providers, policy) -> InvariantResult:
    ok = not (decision.budget_verdict == "BLOCK" and decision.served)
    return InvariantResult(
        "blocked_is_not_served", ok,
        "ok" if ok else "a BLOCK verdict was served anyway",
    )


def served_provider_is_healthy(req, decision, providers, policy) -> InvariantResult:
    ok = True
    detail = "ok"
    if decision.served and not decision.cache_hit and decision.provider is not None:
        match = next((p for p in providers if p.name == decision.provider), None)
        ok = match is not None and match.healthy
        if not ok:
            detail = f"served by unhealthy/unknown provider {decision.provider}"
    return InvariantResult("served_provider_is_healthy", ok, detail)


ALL_INVARIANTS = (
    served_meets_quality_floor,
    served_within_ceiling,
    blocked_is_not_served,
    served_provider_is_healthy,
)


def check_decision(
    req: InferenceRequest,
    decision: RouteDecision,
    providers: Sequence[Provider],
    policy: BudgetPolicy,
) -> list[InvariantResult]:
    return [inv(req, decision, providers, policy) for inv in ALL_INVARIANTS]


def passed(req, decision, providers, policy) -> bool:
    return all(r.passed for r in check_decision(req, decision, providers, policy))
