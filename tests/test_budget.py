from decimal import Decimal

from src.budget import BudgetPolicy, BudgetVerdict
from src.request import InferenceRequest, ModelTier


def req(max_cost=None, tenant="t"):
    return InferenceRequest("r", tenant, "k", difficulty=0.1, max_cost=max_cost,
                            required_quality=ModelTier.CHEAP)


def test_within_ceiling_allows():
    pol = BudgetPolicy(per_request_ceiling=Decimal("0.01"))
    assert pol.check(req(), Decimal("0.005"))[0] is BudgetVerdict.ALLOW


def test_over_ceiling_downgrades():
    pol = BudgetPolicy(per_request_ceiling=Decimal("0.01"))
    assert pol.check(req(), Decimal("0.05"))[0] is BudgetVerdict.DOWNGRADE


def test_tenant_exhausted_blocks():
    pol = BudgetPolicy(per_request_ceiling=Decimal("1"), tenant_remaining={"t": Decimal("0.001")})
    assert pol.check(req(), Decimal("0.005"))[0] is BudgetVerdict.BLOCK


def test_per_request_override_ceiling():
    pol = BudgetPolicy(per_request_ceiling=Decimal("0.01"))
    assert pol.ceiling_for(req(max_cost=Decimal("0.50"))) == Decimal("0.50")
