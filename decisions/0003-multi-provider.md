# ADR-0003: One interface over many providers

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering, Procurement |
| **Tags** | providers, resilience, lock-in, arbitrage |

## Context

Single-vendor inference is simpler to build and a strategic trap. One provider means one price, one outage surface, one roadmap you don't control, and a switching cost that grows every quarter. For a tier-0 service that every product depends on, that's three risks concentrated into one dependency.

## Decision

Abstract every model behind a single **provider interface** (cost, tier, health, latency, capabilities) and route across providers. A real Anthropic/OpenAI/self-hosted client and a test stub implement the same shape. The router selects providers by tier and cost; the provider's identity is a detail behind the interface.

## Alternatives considered

**Single vendor.** Rejected — concentrates price, availability, and lock-in risk into one dependency for a service everything relies on.

**A managed multi-provider gateway as the whole answer.** Partly adopted — the plumbing is worth buying (ADR-0008), but the *routing policy* stays ours, behind our interface, so it's portable across gateways.

## Consequences

**Buys us:** price arbitrage (route to the cheapest provider that meets the tier), resilience (failover across providers — ADR-0004), and freedom to change vendors without rewriting the platform.

**Costs us:** an integration and normalization surface — providers differ in APIs, token accounting, and capabilities, and that has to be abstracted cleanly.

**Risks:** the abstraction leaks (a capability only one provider has) → keep the interface to the common denominator the router needs (cost, tier, health, latency) and handle genuinely provider-specific features explicitly, not by special-casing the router.

## How we operate it

New providers are added behind the same interface and earn traffic only after passing the eval gate (ADR-0007) for the request classes they'll serve. Provider health and cost are first-class telemetry.

---

**In one line, if I had to defend it to a board:** *I won't make a service that everything depends on hostage to one vendor's price, uptime, and roadmap. One interface, many providers — so the router can always pick the cheapest healthy option and we can always walk away.*
