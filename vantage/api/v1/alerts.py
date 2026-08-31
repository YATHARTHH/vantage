from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from vantage.api.dependencies import get_metadata_repository, require_api_key
from vantage.domain.alerts import AlertRule, DetectorType
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class SaveAlertRuleRequest(BaseModel):
    project_id: str
    detector_type: DetectorType
    metric_name: str
    warn_z: float = 2.0
    crit_z: float = 3.0
    absolute_threshold: float | None = None
    rate_change_factor: float = 1.5
    error_rate_pct: float = 5.0
    enabled: bool = True


@router.get("", summary="List alert records")
async def list_alerts(
    project_id: str | None = None,
    unresolved_only: bool = False,
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    alerts = await repo.list_alerts(project_id=project_id, unresolved_only=unresolved_only)
    return [a.model_dump() for a in alerts]


@router.patch("/{alert_id}/resolve", summary="Resolve active alert incident")
async def resolve_alert(
    alert_id: str,
    _: str = Depends(require_api_key),
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    success = await repo.resolve_alert(alert_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found.",
        )
    return {"resolved": True, "alert_id": alert_id}


@router.get("/rules/{project_id}", summary="Get alert rules for project")
async def get_alert_rules(
    project_id: str,
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    rule = await repo.get_alert_rule(project_id)
    if not rule:
        return {"project_id": project_id, "rules": []}
    return {"project_id": project_id, "rules": [rule.model_dump()]}


@router.post("/rules", status_code=status.HTTP_201_CREATED, summary="Save or update alert rule")
async def save_alert_rule(
    req: SaveAlertRuleRequest,
    _: str = Depends(require_api_key),
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    rule = AlertRule(
        project_id=req.project_id,
        detector_type=req.detector_type,
        metric_name=req.metric_name,
        warn_z=req.warn_z,
        crit_z=req.crit_z,
        absolute_threshold=req.absolute_threshold,
        rate_change_factor=req.rate_change_factor,
        error_rate_pct=req.error_rate_pct,
        enabled=req.enabled,
    )
    saved = await repo.save_alert_rule(rule)
    return saved.model_dump()
