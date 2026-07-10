"""Calculation engine — deterministic, config-driven reward computation."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def resolve_threshold(scale: list[dict[str, Any]], performance: Decimal) -> Decimal:
    """Return the coefficient for a given performance ratio from a stepped scale."""
    p = float(performance)
    for step in scale:
        if step["from"] <= p < step["to"]:
            return Decimal(str(step["coefficient"]))
    return Decimal("0")


def calculate_reward(
    metrics: dict[str, Decimal],
    config: dict[str, Any],
) -> tuple[Decimal, list[dict[str, Any]]]:
    """
    Compute total reward and decomposition steps from metric values and config.

    Returns (total_amount rounded to 2 dp, list of step dicts).
    """
    steps: list[dict[str, Any]] = []
    total = Decimal("0")

    # 1. Components
    for i, comp in enumerate(config["components"]):
        value = Decimal(str(metrics.get(comp["metric"], 0)))
        plan = Decimal(str(comp["plan"]))
        performance = (value / plan) if plan else Decimal("0")
        coeff = resolve_threshold(comp["scale"], performance)
        weight = Decimal(str(comp.get("weight", 1)))
        base_rate = Decimal(str(comp["base_rate"]))
        amount = base_rate * coeff * weight
        total += amount
        steps.append(
            {
                "step_no": i + 1,
                "description": f"Компонент: {comp['metric']}",
                "metric": comp["metric"],
                "value": float(value),
                "plan": float(plan),
                "performance": round(float(performance), 4),
                "coefficient": float(coeff),
                "amount": float(amount.quantize(Decimal("0.01"))),
            }
        )

    # 2. Modifiers
    for j, mod in enumerate(config.get("modifiers", [])):
        amount = Decimal(str(mod["amount"]))
        total += amount
        steps.append(
            {
                "step_no": len(config["components"]) + j + 1,
                "description": f"Модификатор: {mod['code']}",
                "modifier": mod["code"],
                "type": mod["type"],
                "amount": float(amount),
            }
        )

    # 3. Limits
    limits = config.get("limits", {})
    if "min" in limits and limits["min"] is not None:
        total = max(total, Decimal(str(limits["min"])))
    if "max" in limits and limits["max"] is not None:
        total = min(total, Decimal(str(limits["max"])))

    return total.quantize(Decimal("0.01")), steps
