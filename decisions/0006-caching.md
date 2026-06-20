# ADR-0006: Cache exact now, semantic later — with the risk owned

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Tags** | caching, cost, quality, risk |

## Context

Caching is the cheapest cost lever there is: a cache hit costs nothing and returns instantly. The temptation is to reach straight for *semantic* caching — match similar-enough requests and reuse the answer — because it hits far more often. The temptation is also where the trap is: a semantic cache that returns a close-but-wrong answer isn't a saving, it's a silent quality and trust failure, and it's exactly the kind of failure that doesn't show up in a cost dashboard.

## Decision

Ship **exact-match caching with a TTL** first — keyed on a normalized request, correct by construction, never serving an entry past its TTL. Defer **semantic caching** until its false-hit risk is gated behind the eval harness (ADR-0007): a semantic cache may only serve a hit for a request class where evals show the similarity threshold doesn't degrade quality.

## Alternatives considered

**Semantic caching on day one.** Rejected — introduces a correctness risk (wrong-but-close answers) before there's an eval gate to bound it. The biggest hit-rate gain, behind the biggest unmeasured risk.

**No caching.** Rejected — leaves the safest, largest cost lever on the table.

## Consequences

**Buys us:** the cheap, safe wins immediately — repeated and idempotent requests stop costing anything, with zero correctness risk.

**Costs us:** exact-match hit rates are lower than semantic; we accept a smaller, safe win now over a larger, unproven one.

**Risks:** stale cache content (the world changed but the TTL hasn't) → mitigate with conservative TTLs per request class and explicit invalidation hooks; a cache entry past TTL is never served.

## How we operate it

Cache hit rate is on the scorecard. Semantic caching is a future ADR, not a flag someone flips — it ships only with the eval evidence that its threshold holds quality.

---

**In one line, if I had to defend it to a board:** *Caching is free money, but a semantic cache that returns a nearly-right answer is the opposite — a quality failure you can't see in the cost numbers. So I take the safe exact-match wins now and let semantic earn its way in through evals.*
