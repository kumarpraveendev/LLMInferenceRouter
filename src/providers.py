"""Provider abstraction and a default multi-provider pool.

Every model lives behind this one shape (ADR-0003). A real Anthropic/OpenAI/
self-hosted client and the stubs below are interchangeable to the router.
Costs are per 1,000 tokens, in arbitrary currency units; values are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.request import ModelTier


@dataclass(frozen=True)
class Provider:
    name: str
    tier: ModelTier
    cost_per_1k_input: Decimal
    cost_per_1k_output: Decimal
    p50_latency_ms: int
    healthy: bool = True


# Multiple providers per tier so failover and price arbitrage are real.
DEFAULT_PROVIDERS: list[Provider] = [
    Provider("cheap-fast",  ModelTier.CHEAP,  Decimal("0.00025"), Decimal("0.00125"), 400),
    Provider("cheap-alt",   ModelTier.CHEAP,  Decimal("0.00020"), Decimal("0.00100"), 600),
    Provider("mid-a",       ModelTier.MID,    Decimal("0.00100"), Decimal("0.00500"), 800),
    Provider("mid-b",       ModelTier.MID,    Decimal("0.00090"), Decimal("0.00450"), 1500),
    Provider("strong-a",    ModelTier.STRONG, Decimal("0.00300"), Decimal("0.01500"), 1200),
    Provider("strong-b",    ModelTier.STRONG, Decimal("0.00250"), Decimal("0.01200"), 3000),
]
