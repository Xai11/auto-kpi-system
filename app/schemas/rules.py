from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import SchemeStatus
from app.schemas.rule_config import RuleConfig


class MetricBase(BaseModel):
    code: str
    name: str
    unit: str | None = None
    data_type: str = "numeric"


class MetricCreate(MetricBase):
    pass


class MetricRead(MetricBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TemplateBase(BaseModel):
    name: str
    description: str | None = None


class TemplateCreate(TemplateBase):
    metric_ids: list[int] = []


class TemplateRead(TemplateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SchemeBase(BaseModel):
    name: str
    template_id: int
    role_id: int | None = None
    department_id: int | None = None


class SchemeCreate(SchemeBase):
    pass


class SchemeRead(SchemeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class VersionCreate(BaseModel):
    effective_from: date
    config: RuleConfig


class VersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scheme_id: int
    effective_from: date
    status: SchemeStatus
    config: dict[str, Any]


class PublishRequest(BaseModel):
    effective_from: date


class ParamPatch(BaseModel):
    """Patch payload for head role: {path: value}."""

    patches: dict[str, Any]
