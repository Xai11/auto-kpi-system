from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AccessRole


class AppUserCreate(BaseModel):
    login: str
    access_role: AccessRole


class AppUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    login: str
    access_role: AccessRole


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    created_at: datetime
