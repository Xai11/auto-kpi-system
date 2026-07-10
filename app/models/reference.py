from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.calculation import CalculationResult, MetricValue
    from app.models.rules import MotivationScheme


class Department(Base):
    __tablename__ = "department"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("department.id", ondelete="SET NULL"), nullable=True
    )

    parent: Mapped[Department | None] = relationship(
        "Department",
        back_populates="children",
        remote_side="Department.id",
        foreign_keys="[Department.parent_id]",
    )
    children: Mapped[list[Department]] = relationship(
        "Department", back_populates="parent", foreign_keys="[Department.parent_id]"
    )
    employees: Mapped[list[Employee]] = relationship(
        "Employee", back_populates="department"
    )
    schemes: Mapped[list[MotivationScheme]] = relationship(
        "MotivationScheme", back_populates="department"
    )


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    employees: Mapped[list[Employee]] = relationship("Employee", back_populates="role")
    schemes: Mapped[list[MotivationScheme]] = relationship(
        "MotivationScheme", back_populates="role"
    )


class Employee(Base):
    __tablename__ = "employee"
    __table_args__ = (
        UniqueConstraint("personnel_no", name="uq_employee_personnel_no"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    personnel_no: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("department.id"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("role.id"), nullable=False
    )
    hired_at: Mapped[date] = mapped_column(Date, nullable=False)
    fired_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    department: Mapped[Department] = relationship(
        "Department", back_populates="employees"
    )
    role: Mapped[Role] = relationship("Role", back_populates="employees")
    metric_values: Mapped[list[MetricValue]] = relationship(
        "MetricValue", back_populates="employee"
    )
    calculation_results: Mapped[list[CalculationResult]] = relationship(
        "CalculationResult", back_populates="employee"
    )
