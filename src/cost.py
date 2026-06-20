"""Per-request cost estimation."""
from __future__ import annotations

from decimal import Decimal

from src.providers import Provider
from src.request import InferenceRequest

_CENT = Decimal("0.000001")


def estimate_cost(req: InferenceRequest, provider: Provider) -> Decimal:
    cin = Decimal(req.expected_input_tokens) / 1000 * provider.cost_per_1k_input
    cout = Decimal(req.expected_output_tokens) / 1000 * provider.cost_per_1k_output
    return (cin + cout).quantize(_CENT)
