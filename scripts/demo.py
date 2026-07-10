#!/usr/bin/env python
"""
Демонстрационный кейс: сквозной расчёт KPI для отдела продаж.

Сценарий
────────
Компания «Ромашка», отдел продаж, 3 менеджера.
Схема мотивации: компонент «Объём сборов» + бонус «нет жалоб».

Шкала выплат (ступенчатая):
  < 80% плана    → коэффициент 0.0
  80–100% плана  → коэффициент 0.5
  100–120% плана → коэффициент 1.0
  ≥ 120% плана   → коэффициент 1.3

Базовая ставка: 30 000 руб.   Бонус «нет жалоб»: +5 000 руб.
Лимиты: 0 – 100 000 руб.

Ожидаемые результаты за январь 2024:
  Иванов  — факт 800 000 (80%)   → 30000×0.5 + 5000 = 20 000 руб.
  Петрова — факт 1 050 000 (105%) → 30000×1.0 + 5000 = 35 000 руб.
  Сидоров — факт 1 300 000 (130%) → 30000×1.3 + 5000 = 44 000 руб.

Запуск: python scripts/demo.py
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env before app imports
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.models.calculation import MetricValue, Period  # noqa: E402
from app.models.enums import PeriodType  # noqa: E402
from app.models.reference import Department, Employee, Role  # noqa: E402
from app.schemas.rule_config import RuleConfig  # noqa: E402
from app.schemas.rules import (  # noqa: E402
    MetricCreate,
    SchemeCreate,
    TemplateCreate,
    VersionCreate,
)
from app.services.orchestration import OrchestrationService  # noqa: E402
from app.services.payslip import PayslipService  # noqa: E402
from app.services.rules import RuleConfigService  # noqa: E402

SEP = "─" * 62
PLAN = 1_000_000


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def main() -> None:
    Base.metadata.create_all(engine)
    # Wrap the entire demo in an outer transaction that is always rolled back.
    # Service-level commit() calls release SAVEPOINTs without touching the outer tx,
    # so demo data never persists and the script is safe to run multiple times.
    connection = engine.connect()
    trans = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        _run(db)
    finally:
        db.close()
        trans.rollback()
        connection.close()


def _run(db: Session) -> None:
    rules = RuleConfigService(db)
    orch = OrchestrationService(db)
    payslip_svc = PayslipService(db)

    # ── 1. Справочники ──────────────────────────────────────────
    section("1. Справочники — подразделения, роли, сотрудники")

    dept = Department(name="Отдел продаж", code="DEMO_SALES")
    role = Role(name="Менеджер продаж")
    db.add_all([dept, role])
    db.flush()
    print(f"  Подразделение : {dept.name!r}  id={dept.id}")
    print(f"  Роль          : {role.name!r}   id={role.id}")

    emp_data = [
        ("Иванов", "Иван", "DE001"),
        ("Петрова", "Мария", "DE002"),
        ("Сидоров", "Алексей", "DE003"),
    ]
    emps: list[Employee] = []
    for last, first, pno in emp_data:
        e = Employee(
            personnel_no=pno,
            last_name=last,
            first_name=first,
            department_id=dept.id,
            role_id=role.id,
            hired_at=date(2022, 1, 1),
        )
        db.add(e)
        emps.append(e)
    db.flush()
    print()
    for e in emps:
        print(
            f"  Сотрудник: {e.last_name} {e.first_name}"
            f"  (табн. {e.personnel_no})  id={e.id}"
        )

    # ── 2. Метрика, шаблон, схема ───────────────────────────────
    section("2. Каталог метрик, шаблон и схема мотивации")

    metric = rules.create_metric(
        MetricCreate(code="DEMO_sales_vol", name="Объём сборов", unit="руб.")
    )
    template = rules.create_template(
        TemplateCreate(name="Менеджер продаж — базовый", metric_ids=[metric.id])
    )
    scheme = rules.create_scheme(
        SchemeCreate(
            name="Мотивация отдел продаж",
            template_id=template.id,
            department_id=dept.id,
        )
    )
    print(f"  Метрика : {metric.code!r}  id={metric.id}")
    print(f"  Шаблон  : {template.name!r}  id={template.id}")
    print(f"  Схема   : {scheme.name!r}  id={scheme.id}")

    # ── 3. Версия правил ────────────────────────────────────────
    section("3. Версия правил (draft → published)")

    config_raw = {
        "components": [
            {
                "metric": "DEMO_sales_vol",
                "plan": PLAN,
                "base_rate": 30_000,
                "weight": 1.0,
                "scale": [
                    {"from": 0.0, "to": 0.8, "coefficient": 0.0},
                    {"from": 0.8, "to": 1.0, "coefficient": 0.5},
                    {"from": 1.0, "to": 1.2, "coefficient": 1.0},
                    {"from": 1.2, "to": 9.99, "coefficient": 1.3},
                ],
            }
        ],
        "modifiers": [{"type": "bonus", "code": "no_complaints", "amount": 5_000}],
        "limits": {"min": 0, "max": 100_000},
    }

    version = rules.create_version(
        scheme.id,
        VersionCreate(
            effective_from=date(2024, 1, 1),
            config=RuleConfig.model_validate(config_raw),
        ),
    )
    published = rules.publish_version(version.id, effective_from=date(2024, 1, 1))
    print(f"  Версия id={published.id}  статус={published.status.value!r}")
    print(f"  Вступает в силу: {published.effective_from}")
    print("  Шкала:")
    for step in published.config["components"][0]["scale"]:
        f, t, c = float(step["from"]), float(step["to"]), float(step["coefficient"])
        print(f"    {f:.0%} – {t:.0%}  →  коэффициент {c}")

    # ── 4. Период и фактические значения ────────────────────────
    section("4. Период январь 2024 — фактические показатели")

    period = Period(
        type=PeriodType.month,
        date_start=date(2024, 1, 1),
        date_end=date(2024, 1, 31),
    )
    db.add(period)
    db.flush()

    actuals: dict[int, Decimal] = {
        emps[0].id: Decimal("800000"),  # 80%
        emps[1].id: Decimal("1050000"),  # 105%
        emps[2].id: Decimal("1300000"),  # 130%
    }
    for emp_id, val in actuals.items():
        db.add(
            MetricValue(
                employee_id=emp_id,
                metric_id=metric.id,
                period_id=period.id,
                value=val,
            )
        )
    db.flush()

    for e, val in zip(emps, actuals.values()):
        pct = float(val) / PLAN * 100
        print(f"  {e.last_name:10} факт={val:>12,} руб.  ({pct:.0f}% плана)")

    # ── 5. Расчёт ───────────────────────────────────────────────
    section("5. Запуск расчёта за период")

    result = orch.run_calculation(period.id)
    print(f"  Рассчитано сотрудников: {result['calculated']}")

    # ── 6. Расчётные листы ──────────────────────────────────────
    section("6. Расчётные листы (декомпозиция)")

    all_correct = True
    expected = [Decimal("20000.00"), Decimal("35000.00"), Decimal("44000.00")]
    for e, exp in zip(emps, expected):
        ps = payslip_svc.get_payslip(e.id, period.id)
        assert ps is not None, f"Расчётный лист для {e.last_name} не найден"
        print(f"\n  ── {e.last_name} {e.first_name} ──")
        for step in ps.steps:
            coeff = f" ×{step.coefficient}" if step.coefficient is not None else ""
            print(
                f"    [{step.step_no}] {step.description}{coeff}"
                f"  → {step.subtotal:>10,.2f} руб."
            )
        status = "✓" if ps.total_amount == exp else f"✗ (ожидалось {exp})"
        print(f"  ИТОГО: {ps.total_amount:>12,.2f} руб.  {status}")
        if ps.total_amount != exp:
            all_correct = False

    # ── Итог ────────────────────────────────────────────────────
    section("Итог")
    if all_correct:
        print("  Все расчёты верны — система работает корректно.")
    else:
        print("  ОШИБКА: расхождение с ожидаемыми значениями!")
        sys.exit(1)

    # Outer transaction rollback happens in main() — no separate call needed here


if __name__ == "__main__":
    main()
