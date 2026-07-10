"""PayslipService — fetch calculation result with decomposition."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculation import CalculationResult
from app.schemas.payslip import DecompositionStepRead, PayslipRead


class PayslipService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_payslip(self, employee_id: int, period_id: int) -> PayslipRead | None:
        stmt = (
            select(CalculationResult)
            .where(
                CalculationResult.employee_id == employee_id,
                CalculationResult.period_id == period_id,
            )
            .order_by(CalculationResult.calculated_at.desc())
            .limit(1)
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        if result is None:
            return None

        from app.models.calculation import Period

        period = self.db.get(Period, period_id)
        if period is None:
            return None

        steps = [DecompositionStepRead.model_validate(s) for s in result.steps]
        return PayslipRead(
            employee_id=employee_id,
            period_id=period_id,
            period_start=period.date_start,
            period_end=period.date_end,
            total_amount=result.total_amount,
            calculated_at=result.calculated_at,
            steps=steps,
            config=result.scheme_version.config,
        )
