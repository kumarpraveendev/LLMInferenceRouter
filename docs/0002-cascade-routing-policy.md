# ADR-0002 — Cascade routing & the escalation signal

**Status:** Accepted
**Context date:** see git history

## Context

The router tries a cheap model first and escalates to a stronger one only when the cheap answer isn't good enough. The whole value of the system rests on one question: **how do we decide "good enough" at runtime?** Two hard constraints shape the answer:

1. **It must be answer-independent.** At inference time we don't have the gold answer, so the signal cannot use it. (Using it would also make the benchmark meaningless.)
2. **It must be cheaper than just calling the frontier model**, or the cascade saves nothing.

## Decision

Make the escalation signal a **pluggable policy** with a configurable threshold, and ship one default. The candidate signals:

| Signal | How it works | Cost | Notes |
|---|---|---|---|
| **Self-consistency** | Sample the small model *k* times; escalate if answers disagree | `k×` small-model cost | No extra model; works anywhere |
| **Judge model** | A small model scores the candidate answer's adequacy; escalate below threshold | +1 judge call | Powerful; **judge cost must be counted** |
| **Logprob confidence** | Escalate when token-level confidence is low | ~free | Not all providers expose logprobs |

**Default: `<self-consistency>`** for portability (no dependence on provider logprobs or a separate judge), with the judge-model policy available for tasks where a learned adequacy signal beats agreement.

The escalation policy is the single point that decides accept-vs-escalate; tiers, thresholds, and the active signal are config, not code.

## The honesty rule

If the active signal makes an extra model call (judge, or *k* self-consistency samples), **those calls are added to the request's cost accounting.** The benchmark and the per-request cost both include escalation overhead. Reporting cascade savings while hiding the judge cost is the exact dishonesty this project exists to avoid.

## Alternatives considered

- **Fixed routing by prompt length / heuristic** — cheap but blunt; misroutes hard-but-short prompts. Rejected as the primary signal (kept as an optional starting-tier hint).
- **Always escalate on any uncertainty** — collapses toward frontier-only cost. Rejected.

## Consequences

- (+) Swapping signals is a config change; each is independently testable.
- (+) Cost accounting stays honest because overhead is attributed at the policy boundary.
- (−) Every signal has a false-"good-enough" rate; the threshold is a tunable quality/cost dial, not a free lunch — documented in the README's limitations.
