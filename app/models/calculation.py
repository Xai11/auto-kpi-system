from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PeriodType

if TYPE_CHECKING:
    from app.models.reference import Employee
    from app.models.rules import Metric, SchemeVersion


class Period(Base):
    __tablename__ = "period"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[PeriodType] = mapped_column(
        Enum(PeriodType, native_enum=False, length=20), nullable=False
    )
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[date] = mapped_column(Date, nullable=False)

    metric_values: Mapped[list[MetricValue]] = relationship(
        "MetricValue", back_populates="period"
    )
    calculation_results: Mapped[list[CalculationResult]] = relationship(
        "CalculationResult", back_populates="period"
    )


class MetricValue(Base):
    __tablename__ = "metric_value"
    __table_args__ = (
        Index("ix_metric_value_employee_period", "employee_id", "period_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employee.id"), nullable=False
    )
    metric_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("metric.id"), nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("period.id"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    employee: Mapped[Employee] = relationship(
        "Employee", back_populates="metric_values"
    )
    metric: Mapped[Metric] = relationship("Metric")
    period: Mapped[Period] = relationship("Period", back_populates="metric_values")


class CalculationResult(Base):
    __tablename__ = "calculation_result"
    __table_args__ = (
        Index("ix_calculation_result_employee_period", "employee_id", "period_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employee.id"), nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("period.id"), nullable=False
    )
    scheme_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("scheme_version.id"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    employee: Mapped[Employee] = relationship(
        "Employee", back_populates="calculation_results"
    )
    period: Mapped[Period] = relationship(
        "Period", back_populates="calculation_results"
    )
    scheme_version: Mapped[SchemeVersion] = relationship("SchemeVersion")
    steps: Mapped[list[DecompositionStep]] = relationship(
        "DecompositionStep", back_populates="result", cascade="all, delete-orphan"
    )


class DecompositionStep(Base):
    __tablename__ = "decomposition_step"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("calculation_result.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_no: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    coefficient: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    result: Mapped[CalculationResult] = relationship(
        "CalculationResult", back_populates="steps"
    )
