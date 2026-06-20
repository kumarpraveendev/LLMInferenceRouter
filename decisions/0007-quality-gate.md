# ADR-0007: A routing change ships only through an eval gate

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering |
| **Tags** | evaluation, quality, ci-cd, safety |

## Context

Every cost optimisation in this platform is also a quality risk: moving a request class to a cheaper model, raising a similarity threshold, widening a tier boundary — each can save money *and* quietly lower quality. And a quality regression caused by a cost change is the hardest kind to catch, because the cost dashboard is showing exactly the green you wanted.

The discipline that keeps cost optimisation honest is the same one that keeps any production agent honest: evaluation. The cheap model doesn't get trusted with a request class because it's cheaper — it gets trusted because it *proved* it meets the bar.

## Decision

Any change to routing policy, thresholds, model assignments, or cache behaviour passes an **offline eval gate** before it's allowed. **Deterministic quality invariants** (a served request meets its required tier; a served route is within budget; a blocked request is never served; a chosen provider is healthy) are hard pass/fail. A **golden set** of request classes catches regressions in routing outcomes. The gate runs in CI on every push.

## Alternatives considered

**Tune-and-watch in production.** Rejected — surfaces quality regressions on real traffic, after customers feel them.

**Cost dashboards as the safety net.** Rejected — a cost dashboard cannot see a quality regression; that's the whole danger.

**LLM-as-judge for the gate.** Used above the line for nuanced quality grading; rejected for the hard invariants — "the judge thought it was fine" is not the assurance I want on whether we served below the quality floor.

## Consequences

**Buys us:** a cost change can't lower quality through the front door — the regression is caught at merge, not in production.

**Costs us:** an eval harness and golden set to build and maintain — which is why a named owner holds it as a standing responsibility.

**Risks:** golden set staleness → fed continuously from production samples and incidents, so coverage tracks real traffic.

## How we operate it

The eval gate is wired into CI; a failing invariant or a golden regression blocks the merge. The golden set grows from production request classes and any incident where a route underperformed.

---

**In one line, if I had to defend it to a board:** *Every cost saving here is a potential quality cut, and the cost dashboard is blind to it. So a cheaper route doesn't ship because it's cheaper — it ships because it passed an eval that proves quality held.*
