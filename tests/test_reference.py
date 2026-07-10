"""Tests for ReferenceService and /departments /roles /employees endpoints."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.schemas.reference import DepartmentCreate, EmployeeCreate, RoleCreate
from app.services.reference import ReferenceService

client = TestClient(app)


# ---- unit tests (no DB) ----


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


# ---- service tests (require PostgreSQL) ----


@pytest.fixture
def svc(db_session: Session) -> ReferenceService:
    return ReferenceService(db_session)


def test_create_and_list_department(svc: ReferenceService) -> None:
    dept = svc.create_department(DepartmentCreate(name="Тест", code="TST"))
    assert dept.id is not None
    assert dept.code == "TST"

    all_depts = svc.list_departments()
    assert any(d.id == dept.id for d in all_depts)


def test_department_hierarchy(svc: ReferenceService) -> None:
    parent = svc.create_department(DepartmentCreate(name="Родитель", code="PAR"))
    child = svc.create_department(
        DepartmentCreate(name="Дочернее", code="CHD", parent_id=parent.id)
    )
    assert child.parent_id == parent.id


def test_create_and_list_role(svc: ReferenceService) -> None:
    role = svc.create_role(RoleCreate(name="Менеджер"))
    assert role.id is not None
    roles = svc.list_roles()
    assert any(r.id == role.id for r in roles)


def test_create_and_list_employee(svc: ReferenceService) -> None:
    dept = svc.create_department(DepartmentCreate(name="Отдел", code="DEP1"))
    role = svc.create_role(RoleCreate(name="Сотрудник"))

    emp = svc.create_employee(
        EmployeeCreate(
            personnel_no="P100",
            last_name="Тестов",
            first_name="Тест",
            department_id=dept.id,
            role_id=role.id,
            hired_at=date(2023, 1, 1),
        )
    )
    assert emp.id is not None
    assert emp.personnel_no == "P100"

    found = svc.get_employee(emp.id)
    assert found is not None
    assert found.last_name == "Тестов"


def test_get_active_employees(svc: ReferenceService) -> None:
    dept = svc.create_department(DepartmentCreate(name="Актив", code="ACT"))
    role = svc.create_role(RoleCreate(name="Активный"))

    active = svc.create_employee(
        EmployeeCreate(
            personnel_no="A001",
            last_name="Активный",
            first_name="Сотрудник",
            department_id=dept.id,
            role_id=role.id,
            hired_at=date(2022, 1, 1),
        )
    )
    fired = svc.create_employee(
        EmployeeCreate(
            personnel_no="A002",
            last_name="Уволенный",
            first_name="Сотрудник",
            department_id=dept.id,
            role_id=role.id,
            hired_at=date(2022, 1, 1),
            fired_at=date(2023, 6, 30),
        )
    )

    period_start = date(2024, 1, 1)
    actives = svc.get_active_employees(period_start)
    active_ids = {e.id for e in actives}
    assert active.id in active_ids
    assert fired.id not in active_ids


# ---- endpoint tests (require PostgreSQL via TestClient override) ----


def test_endpoints_return_list(db_session: Session) -> None:
    """Smoke test: endpoints return 200 and a list."""
    # Override DB dependency
    from app.core.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session

    c = TestClient(app)
    assert c.get("/departments").status_code == 200
    assert c.get("/roles").status_code == 200
    assert c.get("/employees").status_code == 200

    app.dependency_overrides.clear()
