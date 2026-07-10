from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.reference import (
    DepartmentCreate,
    DepartmentRead,
    EmployeeCreate,
    EmployeeRead,
    RoleCreate,
    RoleRead,
)
from app.services.reference import ReferenceService

router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> ReferenceService:
    return ReferenceService(db)


# ---- departments ----


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(svc: ReferenceService = Depends(_svc)) -> list[DepartmentRead]:
    return [DepartmentRead.model_validate(d) for d in svc.list_departments()]


@router.post(
    "/departments",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_department(
    body: DepartmentCreate,
    svc: ReferenceService = Depends(_svc),
) -> DepartmentRead:
    return DepartmentRead.model_validate(svc.create_department(body))


# ---- roles ----


@router.get("/roles", response_model=list[RoleRead])
def list_roles(svc: ReferenceService = Depends(_svc)) -> list[RoleRead]:
    return [RoleRead.model_validate(r) for r in svc.list_roles()]


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    body: RoleCreate,
    svc: ReferenceService = Depends(_svc),
) -> RoleRead:
    return RoleRead.model_validate(svc.create_role(body))


# ---- employees ----


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(svc: ReferenceService = Depends(_svc)) -> list[EmployeeRead]:
    return [EmployeeRead.model_validate(e) for e in svc.list_employees()]


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    svc: ReferenceService = Depends(_svc),
) -> EmployeeRead:
    emp = svc.get_employee(employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeRead.model_validate(emp)


@router.post(
    "/employees",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    body: EmployeeCreate,
    svc: ReferenceService = Depends(_svc),
) -> EmployeeRead:
    return EmployeeRead.model_validate(svc.create_employee(body))
