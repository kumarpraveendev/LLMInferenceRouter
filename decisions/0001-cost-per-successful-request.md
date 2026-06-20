# ADR-0001: Optimize cost per successful, in-SLA request — never cost per token

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering, Finance, Product |
| **Tags** | metrics, unit-economics, quality, sla |

## Context

The first chart an inference-cost project produces is cost per token, or cost per call, and it's almost always going down — because someone pointed traffic at a cheaper model. It makes a clean slide. It's also the wrong number to lead with.

Cost per token measures the price of an *answer*, not the price of a *resolution*. A cheap model that returns a weak answer triggers a retry on a stronger model, an escalation to a human, or a customer who comes back — and now you've paid twice to save once. Optimise the token price and you train the whole system to produce cheap answers that fail expensively somewhere you're not looking.

This is a Goodhart problem: the moment cost per token becomes the target, it stops measuring efficiency and starts measuring corner-cutting.

## Decision

The north-star metric is **cost per successful, in-SLA request**: the blended cost of serving a request that met its quality bar *and* its latency budget. Cost is reported on a balanced scorecard — efficiency (cost per request, cache hit rate, cheap-tier share) alongside quality (eval pass rate, share of requests meeting their required tier) and latency (p95/p99) — with a hard guardrail: **cost per request is never reported without quality pass-rate and p95 beside it.**

A route that lowers cost while dropping quality below the bar or breaching latency is a **regression**, even when the cost dashboard is green.

## Alternatives considered

**Cost per token / per call.** Rejected — cheapest to instrument, most expensive to live with. Rewards cheap failures.

**Quality-only (always use the strongest model).** Rejected — safe and ruinous; it deletes the entire reason the router exists.

**A single blended cost-quality score.** Rejected — collapsing the axes hides the tradeoff a leader needs to see. The value is watching cost and quality move against each other and deciding.

## Consequences

**Buys us:** Finance, Product, and Engineering read the same scorecard; "we cut cost" and "quality dropped" can't both be true in different rooms. Every routing decision has a clear test.

**Costs us:** no single clean savings number — reporting is three axes with guardrails. And it requires quality and latency instrumentation *before* the cost optimisation, which is the work most projects skip.

**Risks:** quality measurement is itself imperfect → mitigate by pairing offline eval pass-rate with online acceptance/retry signals, which need no eval run and are hard to game.

## How we operate it

The weekly review reads all three axes together; a cheaper week with worse quality or latency is a failing week. Quality pass-rate and p95 are required companions to any cost number in any deck.

---

**In one line, if I had to defend it to a board:** *Cost per token measures the price of an answer. I'd rather measure the price of a request that actually worked — because the cheap answer that fails is the most expensive thing in the system.*
