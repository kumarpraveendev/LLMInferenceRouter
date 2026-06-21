# ADR-0003 — Fallback & circuit-breaking

**Status:** Accepted
**Context date:** see git history

## Context

Provider APIs fail: timeouts, rate limits (429), 5xx errors, and occasional total outages. A router that calls multiple providers is exposed to all of their failure modes at once. Without a deliberate strategy, a single provider's bad five minutes takes the whole router down — the opposite of what a routing layer is supposed to buy you.

## Decision

Two layers of protection, both config-driven:

1. **Per-request fallback.** On a retryable error (timeout, 429, 5xx), retry with exponential backoff up to a small limit; if the tier still fails, fall through to the next configured tier (including a designated deterministic fallback model) rather than failing the request.
2. **Per-provider circuit breaker.** Track each provider's recent error rate; when it crosses a threshold, *open* the breaker and stop routing to that provider for a cooldown window, routing around it instead. Probe periodically to *close* it again.

The guiding principle: **degrade quality before failing the request.** A user getting a slightly weaker answer beats a user getting an error.

## Alternatives considered

- **Fail fast, no fallback** — simplest, but turns any provider blip into user-facing errors. Unacceptable for a layer whose job is resilience.
- **Infinite retries** — risks pile-up, cost blowout, and latency spikes during an outage. Rejected in favor of bounded retries + breaker.

## Consequences

- (+) A single provider outage degrades gracefully instead of failing requests.
- (+) The breaker prevents hammering a struggling provider and spreading the failure.
- (−) Fallback can shift cost and latency in unexpected ways during incidents — so fallback events, breaker state, and the resulting tier distribution are emitted to telemetry and watched as SLOs (see README, "Running this in production").
- (−) Retries add latency on the unhappy path; bounds are tuned per provider in config.
