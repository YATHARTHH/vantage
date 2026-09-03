"""Enterprise Webhook Management REST Endpoints.

POST   /api/v1/webhooks      - Create Webhook Subscription (returns HMAC secret ONCE)
GET    /api/v1/webhooks      - List Webhook Subscriptions for project
DELETE /api/v1/webhooks/{id} - Soft revoke Webhook Subscription
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from vantage.auth.rbac import AuthContext, RequirePermission
from vantage.services.webhook_notifier import webhook_notifier, WebhookSubscription

router = APIRouter(prefix="/webhooks", tags=["Enterprise Webhooks"])


class CreateWebhookRequest(BaseModel):
    display_name: str = Field(..., min_length=3, max_length=100)
    endpoint_url: str = Field(..., description="HTTPS target URL for webhook push notifications")
    project_id: Optional[str] = Field(None, description="Optional project restriction scope")
    provider: str = Field("generic", description="generic | slack | teams | pagerduty")


class WebhookItemResponse(BaseModel):
    webhook_id: str
    display_name: str
    endpoint_url: str
    secret: str
    project_id: Optional[str]
    provider: str
    status: str
    created_at: str


@router.post("", response_model=WebhookItemResponse, summary="Create Enterprise Webhook Subscription")
@router.post("/", response_model=WebhookItemResponse, include_in_schema=False)
async def create_webhook(
    req: CreateWebhookRequest,
    auth: AuthContext = Depends(RequirePermission("api_key.manage")),
):
    """Creates a new webhook subscription. Validates URL against SSRF firewall and returns HMAC secret ONCE."""
    try:
        sub = webhook_notifier.register_subscription(
            display_name=req.display_name,
            endpoint_url=req.endpoint_url,
            project_id=req.project_id or auth.project_id,
            provider=req.provider,
            allow_dev_local=True,
        )
        return WebhookItemResponse(
            webhook_id=sub.webhook_id,
            display_name=sub.display_name,
            endpoint_url=sub.endpoint_url,
            secret=sub.secret,
            project_id=sub.project_id,
            provider=sub.provider,
            status=sub.status,
            created_at=sub.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=List[WebhookItemResponse], summary="List Enterprise Webhook Subscriptions")
@router.get("/", response_model=List[WebhookItemResponse], include_in_schema=False)
async def list_webhooks(
    project_id: Optional[str] = Query(None),
    auth: AuthContext = Depends(RequirePermission("api_key.manage")),
):
    """Lists active webhook subscriptions for project."""
    target_project = project_id or auth.project_id
    subs = webhook_notifier.list_subscriptions(project_id=target_project)
    return [
        WebhookItemResponse(
            webhook_id=s.webhook_id,
            display_name=s.display_name,
            endpoint_url=s.endpoint_url,
            secret=s.secret,
            project_id=s.project_id,
            provider=s.provider,
            status=s.status,
            created_at=s.created_at,
        )
        for s in subs
    ]


@router.delete("/{webhook_id}", summary="Soft Revoke Webhook Subscription")
async def revoke_webhook(
    webhook_id: str,
    auth: AuthContext = Depends(RequirePermission("api_key.manage")),
):
    """Soft revokes a webhook subscription."""
    success = webhook_notifier.revoke_subscription(webhook_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription '{webhook_id}' not found",
        )
    return {"status": "revoked", "webhook_id": webhook_id}
