from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SchemeStatus

if TYPE_CHECKING:
    from app.models.reference import Department, Role


class Metric(Base):
    __tablename__ = "metric"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="numeric"
    )

    template_metrics: Mapped[list[TemplateMetric]] = relationship(
        "TemplateMetric", back_populates="metric"
    )


class Template(Base):
    __tablename__ = "template"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    template_metrics: Mapped[list[TemplateMetric]] = relationship(
        "TemplateMetric", back_populates="template"
    )
    schemes: Mapped[list[MotivationScheme]] = relationship(
        "MotivationScheme", back_populates="template"
    )


class TemplateMetric(Base):
    __tablename__ = "template_metric"

    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("template.id", ondelete="CASCADE"), primary_key=True
    )
    metric_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("metric.id", ondelete="CASCADE"), primary_key=True
    )

    template: Mapped[Template] = relationship(
        "Template", back_populates="template_metrics"
    )
    metric: Mapped[Metric] = relationship("Metric", back_populates="template_metrics")


class MotivationScheme(Base):
    __tablename__ = "motivation_scheme"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("template.id"), nullable=False
    )
    role_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("role.id"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("department.id"), nullable=True
    )

    template: Mapped[Template] = relationship("Template", back_populates="schemes")
    role: Mapped[Role | None] = relationship("Role", back_populates="schemes")
    department: Mapped[Department | None] = relationship(
        "Department", back_populates="schemes"
    )
    versions: Mapped[list[SchemeVersion]] = relationship(
        "SchemeVersion", back_populates="scheme"
    )


class SchemeVersion(Base):
    __tablename__ = "scheme_version"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scheme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("motivation_scheme.id"), nullable=False
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SchemeStatus] = mapped_column(
        Enum(SchemeStatus, native_enum=False, length=20),
        nullable=False,
        default=SchemeStatus.draft,
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("app_user.id"), nullable=True
    )

    scheme: Mapped[MotivationScheme] = relationship(
        "MotivationScheme", back_populates="versions"
    )
