"""Seed test data: departments, roles, employees."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.reference import Department, Employee, Role


def seed_reference(db: Session) -> None:
    if db.query(Department).count() > 0:
        return

    # Departments (two levels)
    head_office = Department(name="Головной офис", code="HQ")
    db.add(head_office)
    db.flush()

    sales = Department(name="Отдел продаж", code="SALES", parent_id=head_office.id)
    ops = Department(name="Операционный отдел", code="OPS", parent_id=head_office.id)
    db.add_all([sales, ops])
    db.flush()

    # Roles
    role_manager = Role(name="Менеджер по продажам")
    role_operator = Role(name="Оператор")
    role_head = Role(name="Руководитель")
    db.add_all([role_manager, role_operator, role_head])
    db.flush()

    # Employees
    employees = [
        Employee(
            personnel_no="EMP001",
            last_name="Иванов",
            first_name="Иван",
            middle_name="Иванович",
            department_id=sales.id,
            role_id=role_manager.id,
            hired_at=date(2022, 1, 10),
        ),
        Employee(
            personnel_no="EMP002",
            last_name="Петрова",
            first_name="Мария",
            department_id=sales.id,
            role_id=role_manager.id,
            hired_at=date(2023, 3, 1),
        ),
        Employee(
            personnel_no="EMP003",
            last_name="Сидоров",
            first_name="Алексей",
            department_id=ops.id,
            role_id=role_operator.id,
            hired_at=date(2021, 6, 15),
        ),
        Employee(
            personnel_no="EMP004",
            last_name="Козлова",
            first_name="Елена",
            department_id=sales.id,
            role_id=role_head.id,
            hired_at=date(2020, 9, 1),
        ),
    ]
    db.add_all(employees)
    db.commit()
