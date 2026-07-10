from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.reference import Department, Employee, Role
from app.repositories.reference import (
    DepartmentRepository,
    EmployeeRepository,
    RoleRepository,
)
from app.schemas.reference import (
    DepartmentCreate,
    EmployeeCreate,
    RoleCreate,
)


class ReferenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._depts = DepartmentRepository(db)
        self._roles = RoleRepository(db)
        self._employees = EmployeeRepository(db)

    # ---- departments ----

    def list_departments(self) -> list[Department]:
        return self._depts.get_all()

    def get_department(self, dept_id: int) -> Department | None:
        return self._depts.get_by_id(dept_id)

    def create_department(self, data: DepartmentCreate) -> Department:
        dept = self._depts.create(
            name=data.name, code=data.code, parent_id=data.parent_id
        )
        self.db.commit()
        self.db.refresh(dept)
        return dept

    # ---- roles ----

    def list_roles(self) -> list[Role]:
        return self._roles.get_all()

    def get_role(self, role_id: int) -> Role | None:
        return self._roles.get_by_id(role_id)

    def create_role(self, data: RoleCreate) -> Role:
        role = self._roles.create(name=data.name)
        self.db.commit()
        self.db.refresh(role)
        return role

    # ---- employees ----

    def list_employees(self) -> list[Employee]:
        return self._employees.get_all()

    def get_employee(self, employee_id: int) -> Employee | None:
        return self._employees.get_by_id(employee_id)

    def get_active_employees(self, period_start: date) -> list[Employee]:
        return self._employees.get_active_on(period_start)

    def create_employee(self, data: EmployeeCreate) -> Employee:
        emp = self._employees.create(
            personnel_no=data.personnel_no,
            last_name=data.last_name,
            first_name=data.first_name,
            middle_name=data.middle_name,
            department_id=data.department_id,
            role_id=data.role_id,
            hired_at=data.hired_at,
            fired_at=data.fired_at,
        )
        self.db.commit()
        self.db.refresh(emp)
        return emp
