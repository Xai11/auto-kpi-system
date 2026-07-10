from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import CurrentUser, require_role
from app.models.admin import AppUser, AuditLog
from app.models.enums import AccessRole
from app.schemas.admin import AppUserCreate, AppUserRead, AuditLogRead
from app.services.audit import AuditService

router = APIRouter(prefix="/admin")

_only_admin = require_role(AccessRole.admin)


@router.get("/users", response_model=list[AppUserRead])
def list_users(
    _: CurrentUser = Depends(_only_admin),
    db: Session = Depends(get_db),
) -> list[AppUserRead]:
    users = list(db.execute(select(AppUser)).scalars().all())
    return [AppUserRead.model_validate(u) for u in users]


@router.post("/users", response_model=AppUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    body: AppUserCreate,
    _: CurrentUser = Depends(_only_admin),
    db: Session = Depends(get_db),
) -> AppUserRead:
    user = AppUser(login=body.login, access_role=body.access_role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return AppUserRead.model_validate(user)


@router.get("/audit", response_model=list[AuditLogRead])
def list_audit(
    limit: int = 200,
    _: CurrentUser = Depends(_only_admin),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    svc = AuditService(db)
    logs = svc.list_logs(limit=limit)
    return [AuditLogRead.model_validate(lg) for lg in logs]


@router.get("/audit/{log_id}", response_model=AuditLogRead)
def get_audit_entry(
    log_id: int,
    _: CurrentUser = Depends(_only_admin),
    db: Session = Depends(get_db),
) -> AuditLogRead:
    entry = db.get(AuditLog, log_id)
    if entry is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return AuditLogRead.model_validate(entry)
