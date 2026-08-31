from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from vantage.api.dependencies import get_ingestion_service, require_api_key
from vantage.connectors.custom_run import CustomRunConnector
from vantage.connectors.github import GitHubWebhookConnector
from vantage.connectors.jenkins import JenkinsWebhookConnector
from vantage.connectors.otel_batch import OTLPBatchConnector
from vantage.core.config import get_settings
from vantage.core.security import verify_github_signature
from vantage.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "/otel-batch",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive OTLP/HTTP JSON export from OpenTelemetry Collector",
)
async def ingest_otel_batch(
    request: Request,
    _: str = Depends(require_api_key),
    ingestion_svc: IngestionService = Depends(get_ingestion_service),
):
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Expected Content-Type: application/json, got: {content_type}",
        )

    raw_payload = await request.json()
    connector = OTLPBatchConnector()
    envelopes = connector.parse(raw_payload)

    res = await ingestion_svc.ingest_batch(envelopes)
    return {"accepted": True, **res}


@router.post(
    "/github-webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive GitHub Actions workflow_run webhook",
)
async def ingest_github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    ingestion_svc: IngestionService = Depends(get_ingestion_service),
):
    settings = get_settings()
    body_bytes = await request.body()

    if settings.github_webhook_secret and x_hub_signature_256:
        if not verify_github_signature(body_bytes, settings.github_webhook_secret, x_hub_signature_256):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook signature",
            )

    raw_payload = await request.json()
    connector = GitHubWebhookConnector()
    envelopes = connector.parse(raw_payload)

    res = await ingestion_svc.ingest_batch(envelopes)
    return {"accepted": True, **res}


@router.post(
    "/jenkins-webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive Jenkins build notification webhook",
)
async def ingest_jenkins_webhook(
    request: Request,
    _: str = Depends(require_api_key),
    ingestion_svc: IngestionService = Depends(get_ingestion_service),
):
    raw_payload = await request.json()
    connector = JenkinsWebhookConnector()
    envelopes = connector.parse(raw_payload)

    res = await ingestion_svc.ingest_batch(envelopes)
    return {"accepted": True, **res}


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive custom agent run payload",
)
async def ingest_custom_run(
    raw_payload: dict[str, Any],
    _: str = Depends(require_api_key),
    ingestion_svc: IngestionService = Depends(get_ingestion_service),
):
    connector = CustomRunConnector()
    envelopes = connector.parse(raw_payload)

    res = await ingestion_svc.ingest_batch(envelopes)
    return {"accepted": True, **res}
