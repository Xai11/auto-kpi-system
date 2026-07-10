"""Pydantic schema for scheme_version.config (JSONB contract)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ScaleStep(BaseModel):
    from_: Decimal = Field(alias="from")
    to: Decimal
    coefficient: Decimal

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def check_range(self) -> ScaleStep:
        if self.from_ >= self.to:
            raise ValueError("scale step: 'from' must be less than 'to'")
        return self


class Component(BaseModel):
    metric: str
    plan: Decimal = Field(gt=0)
    base_rate: Decimal = Field(ge=0)
    weight: Decimal = Field(default=Decimal("1.0"), gt=0)
    scale: list[ScaleStep] = Field(min_length=1)

    @model_validator(mode="after")
    def check_scale_contiguous(self) -> Component:
        steps = sorted(self.scale, key=lambda s: s.from_)
        for i in range(1, len(steps)):
            if steps[i].from_ != steps[i - 1].to:
                raise ValueError(
                    f"scale steps are not contiguous at index {i}: "
                    f"{steps[i - 1].to} != {steps[i].from_}"
                )
        return self


class Modifier(BaseModel):
    type: str  # "bonus" | "penalty"
    code: str
    amount: Decimal

    @model_validator(mode="after")
    def check_type(self) -> Modifier:
        if self.type not in ("bonus", "penalty"):
            raise ValueError("modifier type must be 'bonus' or 'penalty'")
        return self


class Limits(BaseModel):
    min: Decimal | None = None
    max: Decimal | None = None

    @model_validator(mode="after")
    def check_min_max(self) -> Limits:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("limits.min must be <= limits.max")
        return self


class EditableField(BaseModel):
    """Boundary for a single editable parameter (for head role)."""

    path: str
    min: Decimal | None = None
    max: Decimal | None = None


class RuleConfig(BaseModel):
    """Full config stored in scheme_version.config."""

    components: list[Component] = Field(min_length=1)
    modifiers: list[Modifier] = Field(default_factory=list)
    limits: Limits = Field(default_factory=Limits)
    editable: list[EditableField] = Field(default_factory=list)
