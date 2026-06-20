"""Request model and model tiers."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum
from typing import Optional


class ModelTier(IntEnum):
    """Ordered tiers. Higher = stronger and more expensive."""

    CHEAP = 1
    MID = 2
    STRONG = 3


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    tenant_id: str
    cache_key: str
    difficulty: float                          # 0..1, estimated
    difficulty_confidence: float = 1.0         # 0..1, confidence in the estimate
    required_quality: ModelTier = ModelTier.CHEAP   # quality floor; router never goes below
    expected_input_tokens: int = 500
    expected_output_tokens: int = 300
    latency_budget_ms: int = 5000
    max_cost: Optional[Decimal] = None         # per-request ceiling override
