from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.rules import (
    MetricCreate,
    MetricRead,
    ParamPatch,
    PublishRequest,
    SchemeCreate,
    SchemeRead,
    TemplateCreate,
    TemplateRead,
    VersionCreate,
    VersionRead,
)
from app.services.rules import RuleConfigService

router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> RuleConfigService:
    return RuleConfigService(db)


# ---- metrics ----


@router.get("/metrics", response_model=list[MetricRead])
def list_metrics(svc: RuleConfigService = Depends(_svc)) -> list[MetricRead]:
    return [MetricRead.model_validate(m) for m in svc.list_metrics()]


@router.post("/metrics", response_model=MetricRead, status_code=status.HTTP_201_CREATED)
def create_metric(
    body: MetricCreate, svc: RuleConfigService = Depends(_svc)
) -> MetricRead:
    return MetricRead.model_validate(svc.create_metric(body))


# ---- templates ----


@router.get("/templates", response_model=list[TemplateRead])
def list_templates(svc: RuleConfigService = Depends(_svc)) -> list[TemplateRead]:
    return [TemplateRead.model_validate(t) for t in svc.list_templates()]


@router.post(
    "/templates", response_model=TemplateRead, status_code=status.HTTP_201_CREATED
)
def create_template(
    body: TemplateCreate, svc: RuleConfigService = Depends(_svc)
) -> TemplateRead:
    return TemplateRead.model_validate(svc.create_template(body))


# ---- schemes ----


@router.get("/schemes", response_model=list[SchemeRead])
def list_schemes(svc: RuleConfigService = Depends(_svc)) -> list[SchemeRead]:
    return [SchemeRead.model_validate(s) for s in svc.list_schemes()]


@router.post("/schemes", response_model=SchemeRead, status_code=status.HTTP_201_CREATED)
def create_scheme(
    body: SchemeCreate, svc: RuleConfigService = Depends(_svc)
) -> SchemeRead:
    return SchemeRead.model_validate(svc.create_scheme(body))


# ---- versions ----


@router.post(
    "/schemes/{scheme_id}/versions",
    response_model=VersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    scheme_id: int,
    body: VersionCreate,
    svc: RuleConfigService = Depends(_svc),
) -> VersionRead:
    v = svc.create_version(scheme_id, body)
    return VersionRead.model_validate(v)


@router.post("/versions/{version_id}/publish", response_model=VersionRead)
def publish_version(
    version_id: int,
    body: PublishRequest,
    svc: RuleConfigService = Depends(_svc),
) -> VersionRead:
    try:
        v = svc.publish_version(version_id, body.effective_from)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VersionRead.model_validate(v)


@router.patch("/versions/{version_id}/params", response_model=VersionRead)
def update_params(
    version_id: int,
    body: ParamPatch,
    svc: RuleConfigService = Depends(_svc),
) -> VersionRead:
    try:
        v = svc.update_params(version_id, body.patches)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return VersionRead.model_validate(v)
