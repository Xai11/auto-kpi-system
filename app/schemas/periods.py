from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import PeriodType


class PeriodCreate(BaseModel):
    type: PeriodType
    date_start: date
    date_end: date

    @model_validator(mode="after")
    def check_dates(self) -> PeriodCreate:
        if self.date_start > self.date_end:
            raise ValueError("date_start must be <= date_end")
        return self


class PeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: PeriodType
    date_start: date
    date_end: date


class MetricValueCreate(BaseModel):
    employee_id: int
    metric_id: int
    period_id: int
    value: Decimal


class MetricValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: int
    metric_id: int
    period_id: int
    value: Decimal
