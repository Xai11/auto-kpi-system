from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class DepartmentBase(BaseModel):
    name: str
    code: str
    parent_id: int | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RoleBase(BaseModel):
    name: str


class RoleCreate(RoleBase):
    pass


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EmployeeBase(BaseModel):
    personnel_no: str
    last_name: str
    first_name: str
    middle_name: str | None = None
    department_id: int
    role_id: int
    hired_at: date
    fired_at: date | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
