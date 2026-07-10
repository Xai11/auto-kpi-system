from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SchemeStatus
from app.models.rules import (
    Metric,
    MotivationScheme,
    SchemeVersion,
    Template,
    TemplateMetric,
)


class MetricRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Metric]:
        return list(self.db.execute(select(Metric)).scalars().all())

    def get_by_id(self, metric_id: int) -> Metric | None:
        return self.db.get(Metric, metric_id)

    def create(self, code: str, name: str, unit: str | None, data_type: str) -> Metric:
        m = Metric(code=code, name=name, unit=unit, data_type=data_type)
        self.db.add(m)
        self.db.flush()
        return m


class TemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[Template]:
        return list(self.db.execute(select(Template)).scalars().all())

    def get_by_id(self, template_id: int) -> Template | None:
        return self.db.get(Template, template_id)

    def create(
        self, name: str, description: str | None, metric_ids: list[int]
    ) -> Template:
        t = Template(name=name, description=description)
        self.db.add(t)
        self.db.flush()
        for mid in metric_ids:
            self.db.add(TemplateMetric(template_id=t.id, metric_id=mid))
        self.db.flush()
        return t


class SchemeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> list[MotivationScheme]:
        return list(self.db.execute(select(MotivationScheme)).scalars().all())

    def get_by_id(self, scheme_id: int) -> MotivationScheme | None:
        return self.db.get(MotivationScheme, scheme_id)

    def create(
        self,
        name: str,
        template_id: int,
        role_id: int | None,
        department_id: int | None,
    ) -> MotivationScheme:
        s = MotivationScheme(
            name=name,
            template_id=template_id,
            role_id=role_id,
            department_id=department_id,
        )
        self.db.add(s)
        self.db.flush()
        return s


class VersionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, version_id: int) -> SchemeVersion | None:
        return self.db.get(SchemeVersion, version_id)

    def get_published_for_scheme(self, scheme_id: int) -> list[SchemeVersion]:
        stmt = select(SchemeVersion).where(
            SchemeVersion.scheme_id == scheme_id,
            SchemeVersion.status == SchemeStatus.published,
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_effective_version(
        self, scheme_id: int, on_date: date
    ) -> SchemeVersion | None:
        """Latest published version with effective_from <= on_date."""
        stmt = (
            select(SchemeVersion)
            .where(
                SchemeVersion.scheme_id == scheme_id,
                SchemeVersion.status == SchemeStatus.published,
                SchemeVersion.effective_from <= on_date,
            )
            .order_by(SchemeVersion.effective_from.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create_draft(
        self, scheme_id: int, config: dict[str, Any], effective_from: date
    ) -> SchemeVersion:
        v = SchemeVersion(
            scheme_id=scheme_id,
            config=config,
            effective_from=effective_from,
            status=SchemeStatus.draft,
        )
        self.db.add(v)
        self.db.flush()
        return v
