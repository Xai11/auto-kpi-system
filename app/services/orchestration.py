"""Orchestration: run_calculation / recalculate for a period."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.calculation import CalculationResult, DecompositionStep, MetricValue
from app.models.reference import Employee
from app.models.rules import MotivationScheme, SchemeVersion
from app.repositories.reference import EmployeeRepository
from app.repositories.rules import VersionRepository
from app.services.calculation import calculate_reward


class OrchestrationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._employees = EmployeeRepository(db)
        self._versions = VersionRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_calculation(self, period_id: int) -> dict[str, Any]:
        """Calculate rewards for all active employees in the given period."""
        period = self._get_period(period_id)
        employees = self._employees.get_active_on(period.date_start)
        saved = 0
        for employee in employees:
            version = self._get_effective_version(employee, period)
            if version is None:
                continue
            metrics = self._get_metric_values(employee.id, period_id)
            total, steps = calculate_reward(metrics, version.config)
            self._save_result(employee.id, period_id, version.id, total, steps)
            saved += 1
        self.db.commit()
        return {"period_id": period_id, "calculated": saved}

    def recalculate(self, period_id: int) -> dict[str, Any]:
        """Delete existing results for the period and recalculate."""
        existing = (
            self.db.execute(
                select(CalculationResult).where(
                    CalculationResult.period_id == period_id
                )
            )
            .scalars()
            .all()
        )
        for r in existing:
            self.db.delete(r)
        self.db.flush()
        return self.run_calculation(period_id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_period(self, period_id: int) -> Any:
        from app.models.calculation import Period

        p = self.db.get(Period, period_id)
        if p is None:
            raise ValueError(f"Period {period_id} not found")
        return p

    def _get_effective_version(
        self, employee: Employee, period: Any
    ) -> SchemeVersion | None:
        """
        Find the published SchemeVersion for the employee's scheme
        with max(effective_from) <= period.date_start.
        """
        # Resolve scheme via motivation_scheme: match department OR role
        stmt = (
            select(MotivationScheme)
            .where(
                (MotivationScheme.department_id == employee.department_id)
                | (MotivationScheme.role_id == employee.role_id)
            )
            .limit(1)
        )
        scheme = self.db.execute(stmt).scalar_one_or_none()
        if scheme is None:
            return None

        return self._versions.get_effective_version(scheme.id, period.date_start)

    def _get_metric_values(
        self, employee_id: int, period_id: int
    ) -> dict[str, Decimal]:
        stmt = select(MetricValue).where(
            MetricValue.employee_id == employee_id,
            MetricValue.period_id == period_id,
        )
        rows = self.db.execute(stmt).scalars().all()
        # Join to Metric to get code
        result: dict[str, Decimal] = {}
        for mv in rows:
            from app.models.rules import Metric

            metric = self.db.get(Metric, mv.metric_id)
            if metric is not None:
                result[metric.code] = mv.value
        return result

    def _save_result(
        self,
        employee_id: int,
        period_id: int,
        version_id: int,
        total: Decimal,
        steps: list[dict[str, Any]],
    ) -> None:
        result = CalculationResult(
            employee_id=employee_id,
            period_id=period_id,
            scheme_version_id=version_id,
            total_amount=total,
            calculated_at=datetime.utcnow(),
        )
        self.db.add(result)
        self.db.flush()

        for i, step in enumerate(steps):
            ds = DecompositionStep(
                result_id=result.id,
                step_no=step.get("step_no", i + 1),
                description=step.get("description"),
                coefficient=(
                    Decimal(str(step["coefficient"])) if "coefficient" in step else None
                ),
                subtotal=Decimal(str(step["amount"])),
            )
            self.db.add(ds)
