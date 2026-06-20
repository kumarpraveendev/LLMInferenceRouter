"""Golden-case runner. Doubles as the CI eval gate (exit 1 on any failure).

Each "route" case runs a request through the real router and asserts the
expected outcome *and* that every quality invariant holds. Each "invariant"
case feeds a hand-built decision to the invariant checker. The seed set here is
representative; in production it grows from real request classes and incidents.

Run: ``python -m evals.golden_runner``
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.budget import BudgetPolicy
from src.cache import ResponseCache
from src.providers import DEFAULT_PROVIDERS
from src.request import InferenceRequest, ModelTier
from src.router import RouteDecision, Router
from evals.quality_invariants import check_decision

CASES_PATH = Path(__file__).with_name("golden_cases.json")


@dataclass(frozen=True)
class Result:
    name: str
    passed: bool
    detail: str


def _build_request(r: dict[str, Any]) -> InferenceRequest:
    return InferenceRequest(
        request_id=r.get("request_id", "req"),
        tenant_id=r.get("tenant_id", "tenant-a"),
        cache_key=r.get("cache_key", "key-1"),
        difficulty=r["difficulty"],
        difficulty_confidence=r.get("difficulty_confidence", 1.0),
        required_quality=ModelTier[r.get("required_quality", "CHEAP")],
        latency_budget_ms=r.get("latency_budget_ms", 5000),
        max_cost=Decimal(r["max_cost"]) if "max_cost" in r else None,
    )


def _build_policy(cfg: dict[str, Any], req: InferenceRequest) -> BudgetPolicy:
    tenant_remaining = {}
    if cfg.get("tenant_budget") is not None:
        tenant_remaining[req.tenant_id] = Decimal(cfg["tenant_budget"])
    return BudgetPolicy(
        per_request_ceiling=Decimal(cfg.get("per_request_ceiling", "0.0030")),
        tenant_remaining=tenant_remaining,
    )


def _run_route(case: dict[str, Any]) -> Result:
    cfg = case.get("config", {})
    req = _build_request(case["request"])
    policy = _build_policy(cfg, req)
    cache = ResponseCache()
    if cfg.get("seed_cache"):
        cache.put(req.cache_key, "cached-response")
    router = Router(DEFAULT_PROVIDERS, budget=policy, cache=cache)

    decision = router.serve(req)
    exp = case["expect"]
    problems = []

    if decision.served != exp["served"]:
        problems.append(f"served: want {exp['served']}, got {decision.served}")
    if "tier" in exp:
        got = decision.tier.name if decision.tier else None
        if got != exp["tier"]:
            problems.append(f"tier: want {exp['tier']}, got {got}")
    if "cache_hit" in exp and decision.cache_hit != exp["cache_hit"]:
        problems.append(f"cache_hit: want {exp['cache_hit']}, got {decision.cache_hit}")
    if "degraded" in exp and decision.degraded != exp["degraded"]:
        problems.append(f"degraded: want {exp['degraded']}, got {decision.degraded}")
    if "cost_max" in exp and decision.served and not decision.cache_hit:
        if decision.estimated_cost > Decimal(exp["cost_max"]):
            problems.append(f"cost {decision.estimated_cost} over expected max {exp['cost_max']}")

    # Every produced decision must also satisfy the invariants.
    for r in check_decision(req, decision, DEFAULT_PROVIDERS, policy):
        if not r.passed:
            problems.append(f"invariant {r.name}: {r.detail}")

    return Result(case["name"], not problems, "; ".join(problems))


def _run_invariant(case: dict[str, Any]) -> Result:
    req = _build_request(case["request"])
    policy = _build_policy(case.get("config", {}), req)
    d = case["decision"]
    decision = RouteDecision(
        served=d["served"],
        tier=ModelTier[d["tier"]] if d.get("tier") else None,
        provider=d.get("provider"),
        estimated_cost=Decimal(d.get("estimated_cost", "0")),
        reason="(golden invariant case)",
        cache_hit=d.get("cache_hit", False),
        degraded=d.get("degraded", False),
        budget_verdict=d.get("budget_verdict", "ALLOW"),
    )
    got_pass = all(r.passed for r in check_decision(req, decision, DEFAULT_PROVIDERS, policy))
    want_pass = case["expect_pass"]
    return Result(case["name"], got_pass == want_pass, f"want pass={want_pass}, got pass={got_pass}")


_DISPATCH = {"route": _run_route, "invariant": _run_invariant}


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def run_all(cases: list[dict[str, Any]]) -> list[Result]:
    return [_DISPATCH[c["kind"]](c) for c in cases]


def main() -> int:
    results = run_all(load_cases())
    failures = [r for r in results if not r.passed]
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"[{mark}] {r.name}" + ("" if r.passed else f"  ({r.detail})"))
    print(f"\n{len(results) - len(failures)}/{len(results)} passed.")
    if failures:
        print("EVAL GATE: BLOCKED — regression(s) detected.")
        return 1
    print("EVAL GATE: PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
