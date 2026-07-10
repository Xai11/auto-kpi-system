"""RuleConfigService — metric catalogue, templates, schemes, versioning."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import SchemeStatus
from app.models.rules import Metric, MotivationScheme, SchemeVersion, Template
from app.repositories.rules import (
    MetricRepository,
    SchemeRepository,
    TemplateRepository,
    VersionRepository,
)
from app.schemas.rule_config import EditableField, RuleConfig
from app.schemas.rules import (
    MetricCreate,
    SchemeCreate,
    TemplateCreate,
    VersionCreate,
)


class _DecimalEncoder(json.JSONEncoder):
    """Converts Decimal to float so JSONB stores numbers, not quoted strings."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


class RuleConfigService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._metrics = MetricRepository(db)
        self._templates = TemplateRepository(db)
        self._schemes = SchemeRepository(db)
        self._versions = VersionRepository(db)

    # ---- metrics ----

    def list_metrics(self) -> list[Metric]:
        return self._metrics.get_all()

    def create_metric(self, data: MetricCreate) -> Metric:
        m = self._metrics.create(
            code=data.code, name=data.name, unit=data.unit, data_type=data.data_type
        )
        self.db.commit()
        self.db.refresh(m)
        return m

    # ---- templates ----

    def list_templates(self) -> list[Template]:
        return self._templates.get_all()

    def create_template(self, data: TemplateCreate) -> Template:
        t = self._templates.create(
            name=data.name,
            description=data.description,
            metric_ids=data.metric_ids,
        )
        self.db.commit()
        self.db.refresh(t)
        return t

    # ---- schemes ----

    def list_schemes(self) -> list[MotivationScheme]:
        return self._schemes.get_all()

    def create_scheme(self, data: SchemeCreate) -> MotivationScheme:
        s = self._schemes.create(
            name=data.name,
            template_id=data.template_id,
            role_id=data.role_id,
            department_id=data.department_id,
        )
        self.db.commit()
        self.db.refresh(s)
        return s

    # ---- versions ----

    def create_version(self, scheme_id: int, data: VersionCreate) -> SchemeVersion:
        """Create a draft version; validates config via Pydantic before saving."""
        # Validate config (raises ValidationError on bad input)
        validated = RuleConfig.model_validate(data.config.model_dump(by_alias=True))
        # _DecimalEncoder converts Decimal→float; json.loads gives native numbers
        # so JSONB stores numbers (not strings) and the engine can compare them.
        config_dict = json.loads(
            json.dumps(validated.model_dump(by_alias=True), cls=_DecimalEncoder)
        )

        v = self._versions.create_draft(
            scheme_id=scheme_id,
            config=config_dict,
            effective_from=data.effective_from,
        )
        self.db.commit()
        self.db.refresh(v)
        return v

    def publish_version(self, version_id: int, effective_from: date) -> SchemeVersion:
        v = self._versions.get_by_id(version_id)
        if v is None:
            raise ValueError(f"Version {version_id} not found")
        if v.status != SchemeStatus.draft:
            raise ValueError(
                f"Only draft versions can be published (current: {v.status})"
            )
        v.status = SchemeStatus.published
        v.effective_from = effective_from
        self.db.commit()
        self.db.refresh(v)
        return v

    def update_params(self, version_id: int, patches: dict[str, Any]) -> SchemeVersion:
        """Apply patches to a draft version, enforcing editable boundaries."""
        v = self._versions.get_by_id(version_id)
        if v is None:
            raise ValueError(f"Version {version_id} not found")
        if v.status == SchemeStatus.published:
            raise ValueError("Cannot modify a published version")

        config = RuleConfig.model_validate(v.config)
        editable_map: dict[str, EditableField] = {e.path: e for e in config.editable}

        for path, value in patches.items():
            if path not in editable_map:
                raise ValueError(f"Path '{path}' is not in editable list")
            boundary = editable_map[path]
            dec_val = Decimal(str(value))
            if boundary.min is not None and dec_val < boundary.min:
                raise ValueError(
                    f"Value {dec_val} for '{path}' is below minimum {boundary.min}"
                )
            if boundary.max is not None and dec_val > boundary.max:
                raise ValueError(
                    f"Value {dec_val} for '{path}' exceeds maximum {boundary.max}"
                )
            _apply_patch(v.config, path, dec_val)

        # Re-validate after patching
        RuleConfig.model_validate(v.config)

        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(v, "config")
        self.db.commit()
        self.db.refresh(v)
        return v


def _apply_patch(config: dict[str, Any], path: str, value: Decimal) -> None:
    """Apply a simple dot-notation patch to the config dict in-place."""
    keys = path.split(".")
    node: Any = config
    for key in keys[:-1]:
        if isinstance(node, list):
            node = node[int(key)]
        else:
            node = node[key]
    last = keys[-1]
    if isinstance(node, list):
        node[int(last)] = float(value)
    else:
        node[last] = float(value)
