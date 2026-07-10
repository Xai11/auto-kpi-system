from fastapi import FastAPI
import uvicorn

from app.api.routers.admin import router as admin_router
from app.api.routers.calculations import router as calculations_router
from app.api.routers.payslips import router as payslips_router
from app.api.routers.periods import router as periods_router
from app.api.routers.reference import router as reference_router
from app.api.routers.rules import router as rules_router

app = FastAPI(title="KPI System")

app.include_router(reference_router)
app.include_router(rules_router)
app.include_router(periods_router)
app.include_router(calculations_router)
app.include_router(payslips_router)
app.include_router(admin_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == '__main__':
    uvicorn.run(app)
