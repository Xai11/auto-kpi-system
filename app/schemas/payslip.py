from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class DecompositionStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    step_no: int
    description: str | None
    coefficient: Decimal | None
    subtotal: Decimal


class PayslipRead(BaseModel):
    employee_id: int
    period_id: int
    period_start: date
    period_end: date
    total_amount: Decimal
    calculated_at: datetime
    steps: list[DecompositionStepRead]
    config: dict[str, Any]
