"""The budget policy gate (ADR-0005).

Enforced before any provider call. Over-budget routes are downgraded to a
cheaper tier; if budget can't be met without dropping below the quality floor,
the request is blocked rather than silently served below the bar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional

from src.request import InferenceRequest


class BudgetVerdict(Enum):
    ALLOW = "ALLOW"
    DOWNGRADE = "DOWNGRADE"   # too expensive for this tier; try a cheaper one
    BLOCK = "BLOCK"           # tenant budget exhausted, or no in-floor route fits


@dataclass
class BudgetPolicy:
    per_request_ceiling: Decimal
    # tenant_id -> remaining budget. Absent tenant = no per-tenant limit.
    tenant_remaining: dict[str, Decimal] = field(default_factory=dict)

    def ceiling_for(self, req: InferenceRequest) -> Decimal:
        return req.max_cost if req.max_cost is not None else self.per_request_ceiling

    def check(self, req: InferenceRequest, estimated_cost: Decimal) -> tuple[BudgetVerdict, str]:
        remaining = self.tenant_remaining.get(req.tenant_id)
        if remaining is not None and estimated_cost > remaining:
            return BudgetVerdict.BLOCK, f"tenant budget exhausted (remaining {remaining})"
        ceiling = self.ceiling_for(req)
        if estimated_cost <= ceiling:
            return BudgetVerdict.ALLOW, "within per-request ceiling"
        return BudgetVerdict.DOWNGRADE, f"estimated {estimated_cost} over ceiling {ceiling}"
