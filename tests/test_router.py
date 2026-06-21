"""Unit tests for the router core — pure logic, no network or API keys.

These exercise cost accounting and cascade accept-vs-escalate behavior using
the FakeAdapter, which is exactly what makes CI runnable without secrets.
"""
from router.types import Call
from router.cost import CostAccountant
from router.cascade import CascadeRouter, Tier
from router.adapters.fake import FakeAdapter
from router.escalation import AlwaysEscalate

PRICING = {"small": {"in": 0.15, "out": 0.60}, "frontier": {"in": 3.0, "out": 15.0}}


class NeverEscalate:
    def should_escalate(self, prompt, answer, tier, calls):
        return False


def test_cost_accountant_prices_one_million_tokens():
    acc = CostAccountant(PRICING)
    assert acc.price(Call("small", "fake", 1_000_000, 0, 0.1)) == 0.15


def test_cost_total_sums_every_call_including_escalation():
    acc = CostAccountant(PRICING)
    calls = [Call("small", "fake", 1_000_000, 0, 0.1),
             Call("frontier", "fake", 1_000_000, 0, 0.1)]
    assert acc.total(calls) == 0.15 + 3.0


def test_router_stops_at_cheapest_tier_when_not_escalating():
    tiers = [Tier("small", FakeAdapter("fake-small")),
             Tier("frontier", FakeAdapter("fake-frontier"))]
    r = CascadeRouter(tiers, NeverEscalate(), CostAccountant(PRICING)).route("hi")
    assert r.final_tier == "small"
    assert r.escalated is False
    assert len(r.calls) == 1


def test_router_escalates_to_frontier_and_costs_more_than_zero():
    tiers = [Tier("small", FakeAdapter("fake-small")),
             Tier("frontier", FakeAdapter("fake-frontier"))]
    r = CascadeRouter(tiers, AlwaysEscalate(), CostAccountant(PRICING)).route("hi")
    assert r.final_tier == "frontier"
    assert r.escalated is True
    assert [c.tier for c in r.calls] == ["small", "frontier"]
    assert r.usd_cost > 0
