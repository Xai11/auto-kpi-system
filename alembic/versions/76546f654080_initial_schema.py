"""initial_schema

Revision ID: 76546f654080
Revises:
Create Date: 2026-07-09

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "76546f654080"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("login", sa.String(length=100), nullable=False),
        sa.Column("access_role", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login"),
    )
    op.create_table(
        "department",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["department.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "metric",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("data_type", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "period",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "role",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "template",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "employee",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("personnel_no", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=False),
        sa.Column("middle_name", sa.String(length=255), nullable=True),
        sa.Column("department_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("hired_at", sa.Date(), nullable=False),
        sa.Column("fired_at", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["department.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("personnel_no", name="uq_employee_personnel_no"),
    )
    op.create_table(
        "motivation_scheme",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=True),
        sa.Column("department_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["department.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["template.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "template_metric",
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("metric_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["metric_id"], ["metric.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["template.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("template_id", "metric_id"),
    )
    op.create_table(
        "scheme_version",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scheme_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["scheme_id"], ["motivation_scheme.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "metric_value",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("metric_id", sa.BigInteger(), nullable=False),
        sa.Column("period_id", sa.BigInteger(), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["metric_id"], ["metric.id"]),
        sa.ForeignKeyConstraint(["period_id"], ["period.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_metric_value_employee_period",
        "metric_value",
        ["employee_id", "period_id"],
    )
    op.create_table(
        "calculation_result",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("period_id", sa.BigInteger(), nullable=False),
        sa.Column("scheme_version_id", sa.BigInteger(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("calculated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
        sa.ForeignKeyConstraint(["period_id"], ["period.id"]),
        sa.ForeignKeyConstraint(["scheme_version_id"], ["scheme_version.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calculation_result_employee_period",
        "calculation_result",
        ["employee_id", "period_id"],
    )
    op.create_table(
        "decomposition_step",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("result_id", sa.BigInteger(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("coefficient", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"], ["calculation_result.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("decomposition_step")
    op.drop_index(
        "ix_calculation_result_employee_period", table_name="calculation_result"
    )
    op.drop_table("calculation_result")
    op.drop_index("ix_metric_value_employee_period", table_name="metric_value")
    op.drop_table("metric_value")
    op.drop_table("scheme_version")
    op.drop_table("template_metric")
    op.drop_table("motivation_scheme")
    op.drop_table("employee")
    op.drop_table("template")
    op.drop_table("metric")
    op.drop_table("period")
    op.drop_table("role")
    op.drop_table("department")
    op.drop_table("app_user")
