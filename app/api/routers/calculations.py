from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.orchestration import OrchestrationService

router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> OrchestrationService:
    return OrchestrationService(db)


@router.post("/calculations/{period_id}/run")
def run_calculation(
    period_id: int, svc: OrchestrationService = Depends(_svc)
) -> dict[str, Any]:
    try:
        return svc.run_calculation(period_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/calculations/{period_id}/recalc")
def recalculate(
    period_id: int, svc: OrchestrationService = Depends(_svc)
) -> dict[str, Any]:
    try:
        return svc.recalculate(period_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
