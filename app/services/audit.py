from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(self, action: str, user_id: int | None = None) -> None:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.flush()

    def list_logs(self, limit: int = 200) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())
