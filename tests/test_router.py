from decimal import Decimal

from src.budget import BudgetPolicy
from src.cache import ResponseCache
from src.providers import DEFAULT_PROVIDERS, Provider
from src.request import InferenceRequest, ModelTier
from src.router import Router, select_tier


def req(**kw):
    base = dict(request_id="r", tenant_id="t", cache_key="k",
                difficulty=0.1, difficulty_confidence=0.99, required_quality=ModelTier.CHEAP)
    base.update(kw)
    return InferenceRequest(**base)


def router(**kw):
    kw.setdefault("budget", BudgetPolicy(per_request_ceiling=Decimal("0.0030")))
    return Router(DEFAULT_PROVIDERS, **kw)


def test_easy_request_routes_cheap():
    d = router().serve(req(difficulty=0.1, difficulty_confidence=0.99))
    assert d.served and d.tier is ModelTier.CHEAP


def test_low_confidence_escalates_up():
    tier, _ = select_tier(req(difficulty=0.1, difficulty_confidence=0.5))
    assert tier is ModelTier.MID


def test_quality_floor_is_respected():
    tier, _ = select_tier(req(difficulty=0.1, difficulty_confidence=0.99,
                              required_quality=ModelTier.STRONG))
    assert tier is ModelTier.STRONG


def test_hard_request_uses_strong_when_budget_allows():
    d = router(budget=BudgetPolicy(per_request_ceiling=Decimal("0.01"))).serve(
        req(difficulty=0.9))
    assert d.served and d.tier is ModelTier.STRONG


def test_over_budget_downgrades():
    d = router().serve(req(difficulty=0.9))
    assert d.served and d.tier is ModelTier.MID and d.budget_verdict == "DOWNGRADE"


def test_cannot_meet_budget_without_breaching_floor_blocks():
    d = router().serve(req(difficulty=0.9, required_quality=ModelTier.STRONG))
    assert not d.served and d.budget_verdict == "BLOCK"


def test_tenant_budget_exhausted_blocks():
    pol = BudgetPolicy(per_request_ceiling=Decimal("0.0030"),
                       tenant_remaining={"t": Decimal("0.0001")})
    d = Router(DEFAULT_PROVIDERS, budget=pol).serve(req(difficulty=0.1))
    assert not d.served and d.budget_verdict == "BLOCK"


def test_cache_hit_serves_at_zero_cost():
    cache = ResponseCache()
    cache.put("k", "cached")
    d = router(cache=cache).serve(req(difficulty=0.9, required_quality=ModelTier.STRONG))
    assert d.served and d.cache_hit and d.estimated_cost == Decimal("0")


def test_unhealthy_tier_fails_over():
    pool = [
        Provider("cheap-fast", ModelTier.CHEAP, Decimal("0.00025"), Decimal("0.00125"), 400, healthy=False),
        Provider("cheap-alt", ModelTier.CHEAP, Decimal("0.00020"), Decimal("0.00100"), 600, healthy=False),
        Provider("mid-a", ModelTier.MID, Decimal("0.00100"), Decimal("0.00500"), 800),
    ]
    d = Router(pool, budget=BudgetPolicy(per_request_ceiling=Decimal("0.01"))).serve(
        req(difficulty=0.1))
    assert d.served and d.tier is ModelTier.MID and d.degraded


def test_latency_budget_filters_slow_providers():
    # difficulty high -> wants STRONG, but only the fast cheap provider meets a 500ms budget
    d = router(budget=BudgetPolicy(per_request_ceiling=Decimal("0.01"))).serve(
        req(difficulty=0.9, latency_budget_ms=500))
    assert d.served and d.tier is ModelTier.CHEAP and d.degraded


def test_no_provider_at_floor_blocks():
    pool = [Provider("cheap-fast", ModelTier.CHEAP, Decimal("0.00025"), Decimal("0.00125"), 400, healthy=False)]
    d = Router(pool, budget=BudgetPolicy(per_request_ceiling=Decimal("0.01"))).serve(
        req(difficulty=0.1))
    assert not d.served
