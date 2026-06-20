# ADR-0008: Buy the gateway, build the economics

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06 |
| **Owner** | Praveen Kumar (Head of Engineering, this design) |
| **Deciders** | Engineering, Finance |
| **Tags** | build-vs-buy, strategy, lock-in |

## Context

There are capable LLM gateways and routers off the shelf now. The portfolio reflex is to build the whole thing to prove capability; the opposite reflex — buy an opinionated router and be done — quietly outsources the exact layer that produces the savings. The leadership call is to draw the line where the differentiation actually is.

## Decision

**Buy the gateway/SDK plumbing** — provider connectivity, auth, retries-at-the-wire, token accounting, streaming. **Build the cost-routing policy, the budget gate, and the eval harness** — the cascade, the conservative-up default, the budget verdicts, the quality invariants. These encode *this* platform's economics and risk appetite; they are the layer that carries the ~70% and the quality floor, so they're ours. And they're kept **portable** — they sit above the gateway, so the gateway can change without rewriting the policy.

## Alternatives considered

**Build the entire gateway.** Rejected — reinventing provider connectivity and token accounting that vendors do well, while the differentiated policy work waits.

**Buy an opinionated end-to-end router.** Rejected as the default — convenient, but it owns the routing policy, the budget logic, and the eval boundary, which is precisely the layer that is our advantage and our risk. Fine for a generic use case; not when the economics are the product.

## Consequences

**Buys us:** faster to production, effort concentrated on the layer that differentiates, and the freedom to swap gateways.

**Costs us:** an integration boundary, and a boundary that moves — gateways absorb more routing every quarter, so the line needs revisiting.

**Risks:** the bought gateway's routing features tempt us to lean on them and lose portability → keep the policy layer above the gateway and gateway-agnostic by rule.

## How we operate it

The build/buy boundary is revisited quarterly. The policy, budget, and eval layers stay portable, so the gateway underneath remains a decision we can re-make.

---

**In one line, if I had to defend it to a board:** *I'd buy the plumbing and build the economics. The cascade and the budget gate are where the 70% lives — that's the layer I own. Building the gateway too would just prove I can write a retry loop.*
