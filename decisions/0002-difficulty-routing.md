# ADR-0002: Route by request difficulty, and default *up* when unsure

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering |
| **Tags** | routing, cost, cascade |

## Context

The single largest lever on inference cost is the most ignored one: most requests are easy, and a frontier model is wasted on them. A fixed "use model X for everything" policy either overpays on the easy majority or underperforms on the hard minority. The win is matching model strength to request difficulty — the cascade that, in production, is what got me ~70% against a managed baseline.

But a cascade has a sharp edge: misrouting *down*. Send a hard request to a cheap model and you don't save money — you get a weak answer that retries on a stronger model (you paid for both) or escalates (you paid far more). The error that's expensive is the one where you were too optimistic about how easy the request was.

## Decision

Route by an estimated request difficulty across tiers (cheap / mid / strong), and make the cascade **conservative**: when the difficulty estimate is low-confidence, route *up* a tier, not down. A required-quality floor per request class is always respected — the router can go above the floor, never below it.

The principle: **a cheap-model miss costs more than the stronger model would have, so uncertainty resolves upward.**

## Alternatives considered

**Fixed single model.** Rejected — leaves the biggest lever untouched.

**Route down when unsure (optimise for cost).** Rejected — optimises the metric that fails expensively; uncertainty should never buy a cheaper route.

**Train one fine-tuned model to cover all difficulties.** Rejected for v1 — premature, with real retraining/drift ops burden before we know the traffic shape. The cascade first; fine-tuning is a later, data-informed decision.

## Consequences

**Buys us:** spend concentrates on the minority of requests that need it — the core economics of the platform.

**Costs us:** a difficulty signal and a router to build, evaluate, and maintain. A misroute hurts quality or cost, so the router is a first-class component with its own evals (ADR-0007), not a hidden `if`.

**Risks:** the difficulty estimator drifts or is systematically wrong → mitigate with the conservative default (errors bias toward over-spending a little, never under-serving) and continuous eval against the scorecard.

## How we operate it

Routing thresholds are tuned against the balanced scorecard (ADR-0001), never against cost alone. A change that raises cheap-tier share but drops quality pass-rate is a regression.

---

**In one line, if I had to defend it to a board:** *Most requests are easy and don't need an expensive model — but when I'm not sure how hard a request is, I spend up, not down. A cheap wrong answer is the costliest answer there is.*
