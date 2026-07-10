from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.calculation import MetricValue, Period
from app.schemas.periods import (
    MetricValueCreate,
    MetricValueRead,
    PeriodCreate,
    PeriodRead,
)

router = APIRouter()


@router.get("/periods", response_model=list[PeriodRead])
def list_periods(db: Session = Depends(get_db)) -> list[PeriodRead]:
    rows = db.execute(select(Period)).scalars().all()
    return [PeriodRead.model_validate(p) for p in rows]


@router.post("/periods", response_model=PeriodRead, status_code=status.HTTP_201_CREATED)
def create_period(body: PeriodCreate, db: Session = Depends(get_db)) -> PeriodRead:
    period = Period(type=body.type, date_start=body.date_start, date_end=body.date_end)
    db.add(period)
    db.commit()
    db.refresh(period)
    return PeriodRead.model_validate(period)


@router.get("/metric-values", response_model=list[MetricValueRead])
def list_metric_values(
    period_id: int | None = None,
    employee_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[MetricValueRead]:
    stmt = select(MetricValue)
    if period_id is not None:
        stmt = stmt.where(MetricValue.period_id == period_id)
    if employee_id is not None:
        stmt = stmt.where(MetricValue.employee_id == employee_id)
    rows = db.execute(stmt).scalars().all()
    return [MetricValueRead.model_validate(v) for v in rows]


@router.post(
    "/metric-values",
    response_model=MetricValueRead,
    status_code=status.HTTP_201_CREATED,
)
def create_metric_value(
    body: MetricValueCreate, db: Session = Depends(get_db)
) -> MetricValueRead:
    # Prevent duplicate (employee, metric, period)
    existing = db.execute(
        select(MetricValue).where(
            MetricValue.employee_id == body.employee_id,
            MetricValue.metric_id == body.metric_id,
            MetricValue.period_id == body.period_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Metric value for this employee/metric/period already exists",
        )
    mv = MetricValue(
        employee_id=body.employee_id,
        metric_id=body.metric_id,
        period_id=body.period_id,
        value=body.value,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return MetricValueRead.model_validate(mv)
