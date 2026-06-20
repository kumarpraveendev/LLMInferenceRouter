# src — reference implementation

The differentiated layer from the decision record, as real runnable code
([ADR-0008](../decisions/0008-build-vs-buy.md) is the argument for owning exactly
this much and buying the gateway). Pure standard library — no API keys, no network.

| File | What it is | Decision |
|------|------------|----------|
| [`request.py`](request.py) | Request model + ordered tiers | — |
| [`providers.py`](providers.py) | One interface over many providers; default pool | [ADR-0003](../decisions/0003-multi-provider.md) |
| [`cost.py`](cost.py) | Per-request cost estimate | [ADR-0001](../decisions/0001-cost-per-successful-request.md) |
| [`cache.py`](cache.py) | Exact-match TTL cache (never serves past TTL) | [ADR-0006](../decisions/0006-caching.md) |
| [`budget.py`](budget.py) | Budget gate: ALLOW / DOWNGRADE / BLOCK | [ADR-0005](../decisions/0005-budget-governance.md) |
| [`router.py`](router.py) | Cost-aware cascade + multi-provider failover | [ADR-0002](../decisions/0002-difficulty-routing.md), [ADR-0004](../decisions/0004-failover-policy.md) |

The single most load-bearing line is in `router.select_tier`: a low-confidence
difficulty estimate routes **up** a tier, never down — and a test fails if anyone
flips that. That's ADR-0002 enforced in code, not just argued in prose.

```bash
pip install -e ".[dev]"   # from the repo root
make test                 # unit tests
make eval                 # the golden-case eval gate
```

The orchestration around these components (provider connectivity, streaming, auth)
is the gateway layer this design buys rather than builds — see
[`docs/architecture.md`](../docs/architecture.md).
