from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.payslip import PayslipRead
from app.services.payslip import PayslipService

router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> PayslipService:
    return PayslipService(db)


@router.get("/payslips/{employee_id}", response_model=PayslipRead)
def get_payslip(
    employee_id: int,
    period_id: int,
    svc: PayslipService = Depends(_svc),
) -> PayslipRead:
    payslip = svc.get_payslip(employee_id, period_id)
    if payslip is None:
        raise HTTPException(
            status_code=404,
            detail="Payslip not found for this employee and period",
        )
    return payslip
