# inference-router: A Decision Record

<!-- Replace <your-username> with your GitHub username so the badge renders -->
[![ci](https://github.com/kumarpraveendev/inference-router/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-username>/inference-router/actions/workflows/ci.yml)

> A reference design for a multi-provider, cost-aware LLM inference router — written as the set of decisions a Head of Engineering owns when the goal is "cut inference spend without quietly cutting quality," not a tour of the routing code.

An inference router is where the unit economics of an AI product are won or lost. The cheap way to look good is to route everything to the cheapest model and post the savings. The honest way is harder: spend less *per successful request that met its SLA*, and be able to prove quality didn't slip while the cost line fell.

This repo is a record of the decisions that distinguish those two — and the differentiated layer (the routing policy, the budget gate, the eval harness) is built as real, runnable code underneath. If you only read this README, you should understand how I'd run an inference platform, not just how it routes.

---

## A note on the numbers

This is a reference design. The platform figures below (cost per request, cache hit rate, tier split, savings) are **design targets**, not production results.

The judgment behind them is real: I built a cascaded multi-provider inference pipeline that cut cost roughly **70% against a managed baseline (Bedrock)** and became the org-wide reference pattern, and a multi-tenant LLM/ML inference platform that delivered a **~90% translation-cost reduction**. Where I draw on that, I say so. The numbers in the sample cost report are illustrative; the pattern that produces them is not.

---

## The problem, framed as a leader sees it

Three decisions made badly up front sink most inference-cost projects:

1. **They optimize cost per token.** The cheapest model per token is not the cheapest *outcome* — a weak answer triggers a retry, an escalation, or a downstream human, and you paid twice to save once.
2. **They route by a fixed rule.** "Use model X for everything" leaves the biggest lever — matching model strength to request difficulty — untouched.
3. **They treat cost and quality as one knob.** Cost falls, quality erodes silently, and nobody notices until an eval dashboard (if one exists) catches it months later.

This design treats all three as deliberate decisions. The north-star metric is **cost per successful, in-SLA request**, and every routing choice is judged against quality and latency guardrails, not cost alone.

---

## The decisions

The spine. Each links to a full ADR in [`/decisions`](./decisions); each is a tradeoff I can defend out loud.

### 1. Optimize cost per *successful, in-SLA* request — never cost per token
**Decided:** north-star metric is blended cost per request that met its quality and latency SLA. **Rejected:** lowest cost per token. **Why:** cost-per-token rewards cheap answers that fail downstream and cost more. **Consequence:** a cheaper route that drops quality or blows latency is a regression, not a win. → [ADR-0001](./decisions/0001-cost-per-successful-request.md)

### 2. Route by request difficulty, and default *up* when unsure
**Decided:** a cascade — cheap model for the easy majority, escalate to stronger models on hard/uncertain requests; when the difficulty estimate is low-confidence, route up a tier. **Rejected:** a fixed model, or routing down when unsure. **Why:** a cheap-model miss is the expensive kind — it retries or escalates. This is the lever that produced the ~70%. **Consequence:** spend concentrates on the minority of requests that need it. → [ADR-0002](./decisions/0002-difficulty-routing.md)

### 3. One interface over many providers
**Decided:** abstract every model behind a single provider interface; route across providers. **Rejected:** single-vendor. **Why:** multi-provider buys price arbitrage, resilience, and freedom from lock-in. **Consequence:** an integration/normalization surface to maintain — worth it for the three things it buys. → [ADR-0003](./decisions/0003-multi-provider.md)

### 4. Typed failure handling: degrade, don't halt
**Decided:** explicit failover — unhealthy or too-slow providers are skipped, a dead tier degrades to another, circuit-breaking isolates bad providers. **Rejected:** retry-the-same-thing or fail the request. **Why:** a provider's bad day should be a degradation, not an outage. **Consequence:** a latency/cost budget for failover, and a health model to maintain. → [ADR-0004](./decisions/0004-failover-policy.md)

### 5. Budget is a policy gate, not a hope
**Decided:** per-request and per-tenant budget ceilings enforced before a call is made — over-budget routes downgrade to a cheaper tier; if budget can't be met without dropping below the quality floor, the request is **blocked**, not silently served cheap. **Rejected:** unbounded spend with after-the-fact billing alerts. **Why:** a runaway loop or a bad route shouldn't be discoverable only on the invoice, and you never buy budget by breaching the quality bar. **Consequence:** some legitimate expensive requests are refused — by design, visibly. → [ADR-0005](./decisions/0005-budget-governance.md)

### 6. Cache exact now, semantic later — with the risk owned
**Decided:** an exact-match response cache with TTL as the first cost lever; semantic caching deferred until its false-hit risk is gated. **Rejected:** semantic caching on day one. **Why:** a semantic cache that returns a *close-but-wrong* answer is a quality and trust failure, not a saving. **Consequence:** exact-match captures the cheap, safe wins immediately; semantic is a later decision made with evals. → [ADR-0006](./decisions/0006-caching.md)

### 7. A routing change ships only through an eval gate
**Decided:** any change to the routing policy, thresholds, or model assignments must pass an offline eval before it's allowed — the cheap model has to *prove* it meets the quality bar for a request class before it's trusted with it. **Rejected:** tune-and-watch in production. **Why:** quality regressions from a cost change are exactly the ones that hide. **Consequence:** an eval harness and golden set to maintain — the safety system for cost optimization. → [ADR-0007](./decisions/0007-quality-gate.md)

### 8. Buy the gateway, build the economics
**Decided:** buy the commoditized gateway/SDK plumbing; build the cost-routing policy, the budget gate, and the eval layer — the parts that carry the savings and the risk — and keep them portable. **Rejected:** building the whole gateway, or buying an opinionated router that owns the policy. **Why:** the differentiated layer is the policy, not the plumbing. **Consequence:** revisit the boundary as gateways absorb more routing. → [ADR-0008](./decisions/0008-build-vs-buy.md)

---

## How I'd staff and operate it

- **Team shape:** small — 3–5 engineers. One owns the eval harness and golden set as a standing responsibility, because the eval gate is what keeps cost optimization honest.
- **The router is a tier-0 service:** every product depends on it. It gets an on-call rotation, a latency SLA, and a runbook for provider outages and budget-block storms.
- **The weekly review reads the scorecard, not the savings:** cost per request never appears without quality pass-rate and p95 latency beside it. A cheaper week with worse quality is a failing week.
- **Cost attribution is a feature:** per-request, per-tenant, per-model telemetry is what turns "we saved money" into a number Finance trusts.

---

## What I'd measure

| Axis | Metric | Why it's on the board pack |
|------|--------|----------------------------|
| Efficiency | Cost per successful request · cache hit rate · cheap-tier share | The unit economics, and the levers behind them |
| Quality | Eval pass rate · share of requests meeting required tier | The half that silent cost-cutting destroys |
| Latency | p95 / p99 end-to-end | The SLA the router has to route within |
| Reliability | Success rate · failover rate · budget-block rate | Whether "degrade, don't halt" actually holds |

**Guardrail rule:** cost per request is never reported without quality pass-rate and p95 beside it.

---

## Architecture (the evidence, briefly)

A request flows: **cache → tier selection (by difficulty) → budget gate → provider selection with failover → telemetry.** Full walkthrough, with a diagram, in [`/docs/architecture.md`](./docs/architecture.md) — linked, not led with.

## Running the reference slice

The differentiated layer is real, runnable code — pure standard library, no API keys.

```bash
pip install -e ".[dev]"
make test   # unit tests
make eval   # the golden-case eval gate (exits non-zero on regression)
```

The same eval gate runs in CI on every push, which makes "a routing change ships only through the eval gate" ([ADR-0007](./decisions/0007-quality-gate.md)) true in this repo rather than asserted.

## Repository map

```
.
├── README.md                     ← you are here (the decisions)
├── decisions/                    ← ADRs, one per decision above (0001–0008)
├── artifacts/
│   └── sample-cost-report.md     ← the cost & quality deliverable
├── docs/
│   └── architecture.md           ← the wiring, as evidence
├── src/                          ← reference implementation (runs, no API keys)
│   ├── request.py                ← request model + tiers
│   ├── providers.py              ← provider abstraction + default pool
│   ├── cost.py                   ← cost estimation
│   ├── cache.py                  ← exact-match TTL cache
│   ├── budget.py                 ← the budget policy gate
│   └── router.py                 ← cost-aware cascade + failover
├── evals/                        ← the eval gate from ADR-0007
│   ├── quality_invariants.py     ← deterministic must-hold checks
│   ├── golden_cases.json         ← seed golden set
│   └── golden_runner.py          ← runs the gate; exit 1 on regression
├── tests/                        ← pytest
└── .github/workflows/ci.yml      ← tests + eval gate on every push
```

---

*Reference design and write-up by Praveen Kumar. The judgment is drawn from production experience building multi-provider inference platforms (~70% cost reduction vs a managed baseline; ~90% translation-cost reduction); the platform figures here are design targets, not shipped results.*
