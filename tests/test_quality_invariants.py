from decimal import Decimal

from src.budget import BudgetPolicy
from src.providers import DEFAULT_PROVIDERS
from src.request import InferenceRequest, ModelTier
from src.router import RouteDecision
from evals.quality_invariants import passed

POLICY = BudgetPolicy(per_request_ceiling=Decimal("0.0030"))


def req(required=ModelTier.CHEAP):
    return InferenceRequest("r", "t", "k", difficulty=0.1, required_quality=required)


def test_clean_decision_passes():
    d = RouteDecision(True, ModelTier.CHEAP, "cheap-fast", Decimal("0.0005"), "ok")
    assert passed(req(), d, DEFAULT_PROVIDERS, POLICY)


def test_below_floor_is_caught():
    d = RouteDecision(True, ModelTier.CHEAP, "cheap-fast", Decimal("0.0005"), "x")
    assert not passed(req(required=ModelTier.STRONG), d, DEFAULT_PROVIDERS, POLICY)


def test_over_ceiling_is_caught():
    d = RouteDecision(True, ModelTier.STRONG, "strong-a", Decimal("0.05"), "x")
    assert not passed(req(), d, DEFAULT_PROVIDERS, POLICY)


def test_block_served_is_caught():
    d = RouteDecision(True, ModelTier.CHEAP, "cheap-fast", Decimal("0.0005"), "x",
                      budget_verdict="BLOCK")
    assert not passed(req(), d, DEFAULT_PROVIDERS, POLICY)


def test_unhealthy_provider_is_caught():
    d = RouteDecision(True, ModelTier.CHEAP, "ghost-provider", Decimal("0.0005"), "x")
    assert not passed(req(), d, DEFAULT_PROVIDERS, POLICY)


def test_cache_hit_is_exempt_from_floor_and_ceiling():
    d = RouteDecision(True, None, "cache", Decimal("0"), "hit", cache_hit=True)
    assert passed(req(required=ModelTier.STRONG), d, DEFAULT_PROVIDERS, POLICY)
