# ADR-0004: Typed failure handling — degrade, don't halt

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering |
| **Tags** | reliability, failover, circuit-breaking, sla |

## Context

Providers fail in ordinary ways: outages, rate limits, timeouts, elevated latency. For a tier-0 router, "the provider had a bad day" must not become "the product had an outage." The naive behaviours — retry the same failing provider, or fail the request — convert a degradation into a customer-visible failure.

## Decision

Explicit, typed failover. Unhealthy or too-slow providers are skipped at selection time (a provider whose latency exceeds the request's budget is not a candidate). If the chosen tier has no healthy in-SLA provider, the router **degrades to another tier that still meets the quality floor** rather than failing — escalating up when that preserves quality. Persistently failing providers are circuit-broken out of the pool until healthy again.

The principle: **the request gets served at the required quality if any path exists; it fails only when no path meets the floor.**

## Alternatives considered

**Retry the same provider.** Rejected — amplifies load on a struggling provider and burns the latency budget.

**Fail the request on first provider error.** Rejected — turns a single provider's problem into a product outage.

**Silently degrade below the quality floor to stay up.** Rejected — availability is not worth breaching the quality bar; if no in-floor path exists, that's a real failure to surface, not paper over.

## Consequences

**Buys us:** a provider outage is a degradation, not an outage; the SLA holds through single-provider failures.

**Costs us:** a latency/cost budget consumed by failover, and a health/circuit-breaker model to maintain.

**Risks:** flapping health detection causes thrashing → mitigate with hysteresis on the circuit breaker (don't re-admit a provider on a single success).

## How we operate it

Failover rate and degraded-serve rate are on the scorecard (ADR-0001). A rising failover rate is an early signal of provider trouble, surfaced in the weekly review before it becomes an incident.

---

**In one line, if I had to defend it to a board:** *A provider's bad day should cost us a little latency, not an outage. The router degrades to another path that still meets the bar — and only fails when no path does, loudly, rather than quietly serving something worse.*
