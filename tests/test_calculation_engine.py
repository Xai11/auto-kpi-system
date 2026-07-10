"""Unit tests for the calculation engine (no DB required)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.calculation import calculate_reward, resolve_threshold

SCALE = [
    {"from": 0.0, "to": 0.8, "coefficient": 0.0},
    {"from": 0.8, "to": 1.0, "coefficient": 0.5},
    {"from": 1.0, "to": 1.2, "coefficient": 1.0},
    {"from": 1.2, "to": 9.99, "coefficient": 1.3},
]

BASE_CONFIG: dict = {
    "components": [
        {
            "metric": "sales",
            "plan": 1_000_000,
            "base_rate": 30_000,
            "weight": 1.0,
            "scale": SCALE,
        }
    ],
    "modifiers": [],
    "limits": {"min": 0, "max": 100_000},
}


# ---- resolve_threshold ----


def test_below_threshold_returns_zero() -> None:
    assert resolve_threshold(SCALE, Decimal("0.5")) == Decimal("0")


def test_lower_boundary_hits_correct_step() -> None:
    assert resolve_threshold(SCALE, Decimal("0.8")) == Decimal("0.5")


def test_exact_plan_hits_coeff_1() -> None:
    assert resolve_threshold(SCALE, Decimal("1.0")) == Decimal("1.0")


def test_overperformance_hits_higher_coeff() -> None:
    assert resolve_threshold(SCALE, Decimal("1.25")) == Decimal("1.3")


def test_exactly_at_upper_boundary_moves_to_next() -> None:
    # 0.8 is the start of the second step, not the end of the first
    assert resolve_threshold(SCALE, Decimal("0.8")) == Decimal("0.5")


# ---- calculate_reward ----


def _metrics(value: int | float) -> dict[str, Decimal]:
    return {"sales": Decimal(str(value))}


def test_below_threshold_component_is_zero() -> None:
    total, steps = calculate_reward(_metrics(500_000), BASE_CONFIG)
    assert total == Decimal("0.00")
    assert steps[0]["coefficient"] == 0.0


def test_at_plan_component_equals_base_rate() -> None:
    total, steps = calculate_reward(_metrics(1_000_000), BASE_CONFIG)
    assert total == Decimal("30000.00")
    assert steps[0]["coefficient"] == 1.0


def test_overperformance_raises_amount() -> None:
    total, _ = calculate_reward(_metrics(1_300_000), BASE_CONFIG)
    assert total == Decimal("39000.00")  # 30000 * 1.3


def test_partial_performance() -> None:
    # 900_000 / 1_000_000 = 0.9 → coeff 0.5 → 30000 * 0.5 = 15000
    total, steps = calculate_reward(_metrics(900_000), BASE_CONFIG)
    assert total == Decimal("15000.00")
    assert steps[0]["coefficient"] == 0.5


def test_modifiers_bonus_and_penalty_sum() -> None:
    cfg = dict(BASE_CONFIG)
    cfg["modifiers"] = [
        {"type": "bonus", "code": "no_complaints", "amount": 5000},
        {"type": "penalty", "code": "sla_breach", "amount": -3000},
    ]
    total, steps = calculate_reward(_metrics(1_000_000), cfg)
    # 30000 + 5000 - 3000 = 32000
    assert total == Decimal("32000.00")
    assert len(steps) == 3


def test_limit_max_caps_total() -> None:
    cfg = dict(BASE_CONFIG)
    cfg["limits"] = {"min": 0, "max": 10_000}
    total, _ = calculate_reward(_metrics(1_000_000), cfg)
    assert total == Decimal("10000.00")


def test_limit_min_floor() -> None:
    cfg = dict(BASE_CONFIG)
    cfg["limits"] = {"min": 5000, "max": 100_000}
    total, _ = calculate_reward(_metrics(0), cfg)
    assert total == Decimal("5000.00")


def test_no_limits_key() -> None:
    cfg = {
        "components": [BASE_CONFIG["components"][0]],
        "modifiers": [],
    }
    total, _ = calculate_reward(_metrics(1_000_000), cfg)
    assert total == Decimal("30000.00")


def test_determinism() -> None:
    r1 = calculate_reward(_metrics(850_000), BASE_CONFIG)
    r2 = calculate_reward(_metrics(850_000), BASE_CONFIG)
    assert r1[0] == r2[0]
    assert r1[1] == r2[1]


def test_weight_scales_amount() -> None:
    cfg = dict(BASE_CONFIG)
    cfg["components"] = [
        {
            "metric": "sales",
            "plan": 1_000_000,
            "base_rate": 30_000,
            "weight": 0.5,
            "scale": SCALE,
        }
    ]
    total, _ = calculate_reward(_metrics(1_000_000), cfg)
    assert total == Decimal("15000.00")


def test_zero_plan_yields_zero_performance() -> None:
    cfg = dict(BASE_CONFIG)
    cfg["components"] = [
        {
            "metric": "sales",
            "plan": 0,
            "base_rate": 30_000,
            "weight": 1.0,
            "scale": SCALE,
        }
    ]
    total, _ = calculate_reward(_metrics(100_000), cfg)
    assert total == Decimal("0.00")


@pytest.mark.parametrize(
    "value, expected_coeff",
    [
        (0, 0.0),
        (799_999, 0.0),
        (800_000, 0.5),
        (999_999, 0.5),
        (1_000_000, 1.0),
        (1_199_999, 1.0),
        (1_200_000, 1.3),
    ],
)
def test_scale_boundaries(value: int, expected_coeff: float) -> None:
    _, steps = calculate_reward(_metrics(value), BASE_CONFIG)
    assert steps[0]["coefficient"] == expected_coeff
