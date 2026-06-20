# ADR-0005: Budget is a policy gate, not a hope

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering, Finance |
| **Tags** | governance, budget, multi-tenant, guardrails |

## Context

Inference spend fails in two directions: a single runaway request (a long context, a retry loop, a mis-estimated route) and a single tenant quietly consuming everyone's budget. If the only control is a billing alert, you discover both on the invoice — after the money is gone. For a multi-tenant platform, "spend whatever it takes and we'll watch the bill" is not a policy; it's an absence of one.

This is the inference analogue of an autonomy gate: the router can spend money, so something has to decide, *before the call*, how much it's allowed to spend on whom.

## Decision

Budget is enforced as a **policy gate before any provider call**:

- **Per-request ceiling** — a request whose cheapest in-tier route exceeds the ceiling is **downgraded** to a cheaper tier (if one exists at or above the quality floor). If no tier meets both budget and the quality floor, the request is **blocked**, not silently served below the bar.
- **Per-tenant budget** — a tenant whose remaining budget can't cover the request is **blocked**, protecting every other tenant's share.

The verdict (ALLOW / DOWNGRADE / BLOCK) and its reason are recorded for attribution.

## Alternatives considered

**Unbounded spend with billing alerts.** Rejected — detects overspend after it happens, and offers no per-tenant fairness.

**Hard-fail anything over budget.** Rejected as the only behaviour — downgrading to a cheaper tier that still meets the quality floor serves more requests than a blunt refusal.

**Buy budget by dropping below the quality floor.** Explicitly rejected — that trades the thing we're protecting (ADR-0001) for the thing we're capping. If both can't be met, blocking and surfacing it is the honest outcome.

## Consequences

**Buys us:** a runaway request or a greedy tenant is caught before the spend, not after; multi-tenant fairness is enforced, not hoped for.

**Costs us:** some legitimate expensive requests are refused — visibly, by design. A blocked request is a surfaced decision, not a silent failure.

**Risks:** ceilings set too tight refuse good traffic → mitigate by making ceilings per-request-class and reviewable, and by tracking budget-block rate on the scorecard so over-tight policy shows up immediately.

## How we operate it

Budget-block rate is a scorecard metric. A rising block rate is either an attack/runaway (act) or a too-tight policy (tune) — either way it's visible in the weekly review, not buried in billing.

---

**In one line, if I had to defend it to a board:** *A bad route or a greedy tenant shouldn't be something we discover on the invoice. Budget is checked before the call — over-budget requests get a cheaper model, and we block before we ever serve something below the quality bar to save money.*
