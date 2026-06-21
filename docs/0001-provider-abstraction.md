# ADR-0001 — Provider abstraction

**Status:** Accepted
**Context date:** see git history

## Context

The router calls multiple LLM providers (OpenAI, Anthropic, Gemini, and a local vLLM endpoint). Each has a different SDK, request/response shape, token-counting method, error model, and pricing. If provider-specific details leak into the routing, cost-accounting, or escalation logic, every one of those modules has to change whenever we add or swap a provider — and testing the cascade in isolation becomes impossible.

## Decision

Put every provider behind a single `ProviderAdapter` interface that returns a normalized result:

```python
class ProviderAdapter(Protocol):
    def complete(self, prompt: str, **opts) -> Completion: ...
    # Completion carries: text, input_tokens, output_tokens, latency_s, raw
```

The adapter is the *only* place that knows about a provider's SDK, token counting, and quirks. Pricing lives in config (`config/router.yaml`), not in code. Adding a provider means writing one adapter file and one config block — nothing in the router core changes.

## Alternatives considered

- **Call SDKs directly in the router** — fastest to write, but couples routing to providers and makes the cascade untestable without live API calls. Rejected.
- **Adopt a heavy multi-provider framework (e.g. LiteLLM)** — solves abstraction but pulls in a large dependency and its own opinions; for a reference design meant to be *read*, a thin explicit interface is clearer. Rejected here, reasonable in production.

## Consequences

- (+) New providers are isolated, one-file changes; the cascade is unit-testable with fake adapters.
- (+) Cost accounting has a single normalized token source.
- (−) A thin abstraction can hide provider-specific features (e.g. logprobs, prompt caching). Where the escalation signal needs them (see ADR-0002), the interface is extended explicitly rather than bypassed.
