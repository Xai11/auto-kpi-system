"""Tests for RuleConfigService: metrics, templates, schemes, versioning."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.schemas.rule_config import EditableField, RuleConfig
from app.schemas.rules import (
    MetricCreate,
    SchemeCreate,
    TemplateCreate,
    VersionCreate,
)
from app.services.rules import RuleConfigService

VALID_CONFIG = {
    "components": [
        {
            "metric": "collected_amount",
            "plan": 1000000,
            "base_rate": 30000,
            "weight": 1.0,
            "scale": [
                {"from": 0.0, "to": 0.8, "coefficient": 0.0},
                {"from": 0.8, "to": 1.0, "coefficient": 0.5},
                {"from": 1.0, "to": 1.2, "coefficient": 1.0},
                {"from": 1.2, "to": 9.99, "coefficient": 1.3},
            ],
        }
    ],
    "modifiers": [],
    "limits": {"min": 0, "max": 100000},
}


# ---- RuleConfig schema validation (no DB needed) ----


def test_valid_config_parses() -> None:
    cfg = RuleConfig.model_validate(VALID_CONFIG)
    assert len(cfg.components) == 1
    assert cfg.limits.max is not None


def test_invalid_config_empty_components() -> None:
    with pytest.raises(ValidationError):
        RuleConfig.model_validate({"components": []})


def test_invalid_config_scale_gap() -> None:
    bad = dict(VALID_CONFIG)
    bad["components"] = [
        {
            "metric": "x",
            "plan": 100,
            "base_rate": 1000,
            "scale": [
                {"from": 0.0, "to": 0.5, "coefficient": 0.0},
                # gap: 0.5 → 0.8 missing
                {"from": 0.8, "to": 1.0, "coefficient": 1.0},
            ],
        }
    ]
    with pytest.raises(ValidationError):
        RuleConfig.model_validate(bad)


def test_invalid_config_min_gt_max() -> None:
    bad = dict(VALID_CONFIG)
    bad["limits"] = {"min": 100, "max": 50}
    with pytest.raises(ValidationError):
        RuleConfig.model_validate(bad)


def test_invalid_modifier_type() -> None:
    bad = dict(VALID_CONFIG)
    bad["modifiers"] = [{"type": "unknown", "code": "x", "amount": 1000}]
    with pytest.raises(ValidationError):
        RuleConfig.model_validate(bad)


# ---- service tests (require PostgreSQL) ----


@pytest.fixture
def svc(db_session: Session) -> RuleConfigService:
    return RuleConfigService(db_session)


def _make_scheme(svc: RuleConfigService) -> tuple[int, int]:
    """Helper: create metric + template + scheme, return (scheme_id, metric_id)."""
    m = svc.create_metric(MetricCreate(code="sales_vol", name="Объём продаж"))
    t = svc.create_template(TemplateCreate(name="Базовый шаблон", metric_ids=[m.id]))
    s = svc.create_scheme(SchemeCreate(name="Схема продаж", template_id=t.id))
    return s.id, m.id


def test_create_metric(svc: RuleConfigService) -> None:
    m = svc.create_metric(MetricCreate(code="rev", name="Выручка", unit="руб."))
    assert m.id is not None
    assert m.code == "rev"


def test_create_template(svc: RuleConfigService) -> None:
    m = svc.create_metric(MetricCreate(code="calls", name="Звонки"))
    t = svc.create_template(TemplateCreate(name="Шаблон КЦ", metric_ids=[m.id]))
    assert t.id is not None


def test_create_and_publish_version(svc: RuleConfigService) -> None:
    scheme_id, _ = _make_scheme(svc)

    v = svc.create_version(
        scheme_id,
        VersionCreate(
            effective_from=date(2024, 1, 1),
            config=RuleConfig.model_validate(VALID_CONFIG),
        ),
    )
    assert v.status.value == "draft"

    published = svc.publish_version(v.id, effective_from=date(2024, 1, 1))
    assert published.status.value == "published"


def test_cannot_publish_twice(svc: RuleConfigService) -> None:
    scheme_id, _ = _make_scheme(svc)
    v = svc.create_version(
        scheme_id,
        VersionCreate(
            effective_from=date(2024, 2, 1),
            config=RuleConfig.model_validate(VALID_CONFIG),
        ),
    )
    svc.publish_version(v.id, effective_from=date(2024, 2, 1))
    with pytest.raises(ValueError, match="Only draft"):
        svc.publish_version(v.id, effective_from=date(2024, 2, 1))


def test_update_params_within_bounds(svc: RuleConfigService) -> None:
    cfg = RuleConfig.model_validate(VALID_CONFIG)
    cfg.editable = [EditableField(path="components.0.plan", min=500000, max=2000000)]
    scheme_id, _ = _make_scheme(svc)
    v = svc.create_version(
        scheme_id,
        VersionCreate(
            effective_from=date(2024, 3, 1),
            config=cfg,
        ),
    )
    updated = svc.update_params(v.id, {"components.0.plan": 1500000})
    assert updated.config["components"][0]["plan"] == 1500000.0


def test_update_params_out_of_bounds(svc: RuleConfigService) -> None:
    cfg = RuleConfig.model_validate(VALID_CONFIG)
    cfg.editable = [EditableField(path="components.0.plan", min=500000, max=2000000)]
    scheme_id, _ = _make_scheme(svc)
    v = svc.create_version(
        scheme_id,
        VersionCreate(effective_from=date(2024, 4, 1), config=cfg),
    )
    with pytest.raises(ValueError, match="exceeds maximum"):
        svc.update_params(v.id, {"components.0.plan": 9999999})
