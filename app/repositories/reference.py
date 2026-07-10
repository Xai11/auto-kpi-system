from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Department, Employee, Role


class DepartmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Department]:
        return list(self.db.execute(select(Department)).scalars().all())

    def get_by_id(self, dept_id: int) -> Department | None:
        return self.db.get(Department, dept_id)

    def create(self, name: str, code: str, parent_id: int | None = None) -> Department:
        dept = Department(name=name, code=code, parent_id=parent_id)
        self.db.add(dept)
        self.db.flush()
        return dept


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Role]:
        return list(self.db.execute(select(Role)).scalars().all())

    def get_by_id(self, role_id: int) -> Role | None:
        return self.db.get(Role, role_id)

    def create(self, name: str) -> Role:
        role = Role(name=name)
        self.db.add(role)
        self.db.flush()
        return role


class EmployeeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Employee]:
        return list(self.db.execute(select(Employee)).scalars().all())

    def get_by_id(self, employee_id: int) -> Employee | None:
        return self.db.get(Employee, employee_id)

    def get_active_on(self, period_start: date) -> list[Employee]:
        stmt = select(Employee).where(
            Employee.hired_at <= period_start,
            (Employee.fired_at.is_(None)) | (Employee.fired_at > period_start),
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        personnel_no: str,
        last_name: str,
        first_name: str,
        department_id: int,
        role_id: int,
        hired_at: date,
        middle_name: str | None = None,
        fired_at: date | None = None,
    ) -> Employee:
        emp = Employee(
            personnel_no=personnel_no,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            department_id=department_id,
            role_id=role_id,
            hired_at=hired_at,
            fired_at=fired_at,
        )
        self.db.add(emp)
        self.db.flush()
        return emp
