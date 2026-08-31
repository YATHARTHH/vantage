import httpx
from vantage.core.logging import get_logger
from vantage.domain.alerts import AlertRecord

logger = get_logger(__name__)


class NotificationService:
    """Sends outbound Slack alerts when an anomaly is detected."""

    def __init__(self, webhook_url: str | None = None):
        self._webhook_url = webhook_url

    async def send(self, alert: AlertRecord) -> bool:
        if not self._webhook_url:
            logger.info("slack_notification_skipped_no_url", alert_id=str(alert.alert_id))
            return False

        payload = {
            "text": f"🚨 *[{alert.severity.value.upper()}] Vantage Anomaly Detected*",
            "attachments": [
                {
                    "color": "#ef4444" if alert.severity == "critical" else "#f59e0b",
                    "fields": [
                        {"title": "Project", "value": alert.project_id, "short": True},
                        {"title": "Detector", "value": alert.detector_type.value, "short": True},
                        {"title": "Metric", "value": alert.metric_name, "short": True},
                        {"title": "Current Value", "value": f"{alert.current_value:.4f}", "short": True},
                        {"title": "Message", "value": alert.message, "short": False},
                    ],
                    "footer": "Vantage Intelligence Engine",
                    "ts": int(alert.fired_at.timestamp()),
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self._webhook_url, json=payload)
                if res.status_code == 200:
                    logger.info("slack_notification_sent", alert_id=str(alert.alert_id))
                    return True
                logger.warning("slack_notification_failed", status_code=res.status_code)
                return False
        except Exception as exc:
            logger.error("slack_notification_error", error=str(exc))
            return False
