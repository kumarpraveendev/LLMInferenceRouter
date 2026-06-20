# Sample Cost & Quality Report — inference-router

> **Illustrative sample with synthetic data.** It shows the output of the telemetry
> and scorecard described in [ADR-0001](../decisions/0001-cost-per-successful-request.md):
> a period rollup that reports cost *with* quality and latency beside it, plus the
> reconstructable trail for a single request. Every figure is fabricated for
> demonstration; the savings pattern reflects production experience, not this design.

This artifact answers the two questions Finance and an engineering panel actually ask:
1. *Did we cut cost without cutting quality?* (Part A)
2. *For this request, why did it cost what it cost?* (Part B)

If a router can't answer both, "we saved money" is a claim, not a fact.

---

## Part A — Period scorecard

**Period:** 2026-06-08 → 2026-06-14 (synthetic) · **Requests:** 4.21M

### The headline, reported honestly

| Axis | Metric | Value | Guardrail |
|------|--------|-------|-----------|
| Efficiency | Cost per successful request | **€0.00041** | — |
| Efficiency | vs. single-flagship baseline | **−71%** | — |
| Efficiency | Cache hit rate | 23.8% | — |
| Efficiency | Cheap-tier share of served requests | 68.2% | — |
| Quality | Eval pass rate | 98.9% | ✅ above 98% floor |
| Quality | Requests meeting required tier | 100.0% | ✅ |
| Latency | p95 end-to-end | 1.42s | ✅ under 2.0s SLA |
| Latency | p99 end-to-end | 3.10s | ✅ |
| Reliability | Success rate | 99.97% | ✅ |
| Reliability | Failover rate | 0.6% | ✅ |
| Reliability | Budget-block rate | 0.11% | ✅ |

> **Guardrail note:** cost per request fell 4% week-over-week (a cheap-tier threshold
> was widened). Eval pass rate held at 98.9% and p95 held at 1.42s, so the change is
> a genuine saving. **Had eval pass-rate dropped, this would read FAIL regardless of
> the cost win** — that is the whole point of [ADR-0001](../decisions/0001-cost-per-successful-request.md).

### Where the spend went (tier distribution)

| Tier | Share of served | Share of cost |
|------|-----------------|---------------|
| Cheap | 68.2% | 19% |
| Mid | 24.1% | 33% |
| Strong | 7.7% | 48% |

The shape that produces the savings: most requests are easy and cheap; the spend
concentrates on the hard minority ([ADR-0002](../decisions/0002-difficulty-routing.md)).

### Governance events

- Budget downgrades (over-ceiling → cheaper tier): 14,802 — served, at lower cost.
- Budget blocks (no in-floor route within budget): 4,610 — refused, by design, not served below the bar.
- Failover events (provider unhealthy/slow): 25,118 — degraded, zero customer-visible outages.
- Routing changes shipped this period: 3. **Eval-gate blocks: 1** (a threshold change regressed quality pass-rate; never reached production — [ADR-0007](../decisions/0007-quality-gate.md)).

---

## Part B — Single request trace

**Request ID:** `REQ-2026-0612-0098441` (synthetic) · **Tenant:** `acme` · **Timestamp:** 2026-06-12 14:22:07 CET

| Step | Event | Detail |
|------|-------|--------|
| 1 | Cache check ([ADR-0006](../decisions/0006-caching.md)) | miss |
| 2 | Difficulty estimate | 0.81, confidence 0.62 |
| 3 | Tier selection ([ADR-0002](../decisions/0002-difficulty-routing.md)) | base STRONG; low confidence already at top tier; floor MID → **STRONG** |
| 4 | Provider selection ([ADR-0003](../decisions/0003-multi-provider.md)) | cheapest healthy in-SLA in STRONG: `strong-b` (est. €0.00485) |
| 5 | Budget gate ([ADR-0005](../decisions/0005-budget-governance.md)) | per-request ceiling €0.01 → **ALLOW** |
| 6 | Served | `strong-b`, latency 1.31s, within p95 SLA |

**Attribution row written to telemetry:**
`tenant=acme tier=STRONG provider=strong-b cost=0.00485 cache=miss verdict=ALLOW reason="difficulty 0.81; floor MID; within ceiling" latency_ms=1310`

That row is what makes the −71% in Part A a number Finance can trust rather than a
slide — every euro is attributable to a tenant, a tier, and a routing reason.

---

## How to read this report

- **Part A** is the board/Finance view: did cost fall *with quality and latency holding*?
- **Part B** is the per-request forensic view: pick any request, see why it routed where it did and what it cost.

Together they turn "we cut inference spend" into evidence — and they make a cost
regression that hides a quality regression impossible to ship unnoticed.

---

*Sample artifact for a reference design by Praveen Kumar. Synthetic data throughout; the −71% reflects a production pattern, not this reference implementation.*
