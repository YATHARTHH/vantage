from datetime import datetime, timezone
from typing import Any
from vantage.connectors.base import AbstractConnector
from vantage.domain.events import (
    BuildData,
    EventStatus,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
)


class JenkinsWebhookConnector(AbstractConnector):
    """Parses Jenkins build notification webhooks into TelemetryEnvelope objects."""

    def parse(self, raw_payload: dict[str, Any]) -> list[TelemetryEnvelope]:
        job_name = raw_payload.get("name", "jenkins-job")
        build = raw_payload.get("build", {})
        build_number = build.get("number", 1)
        phase = build.get("phase")

        if phase not in ("COMPLETED", "FINISHED"):
            return []

        status_str = build.get("status", "SUCCESS")
        status = EventStatus.SUCCESS if status_str == "SUCCESS" else EventStatus.ERROR

        duration_ms = build.get("duration")
        started_at = datetime.now(timezone.utc)
        ended_at = started_at

        run_id = f"{job_name}-{build_number}"
        identity = SpanIdentity(
            trace_id=f"jenkins-{run_id}",
            span_id=f"jenkins-build-{build_number}",
            source_trace_id=run_id,
            source_span_id=str(build_number),
        )

        ext_event_id = f"jenkins-{job_name}-{build_number}"

        payload = BuildData(
            repo_name=job_name,
            branch="main",
            pipeline_name=job_name,
        )

        envelope = TelemetryEnvelope(
            external_event_id=ext_event_id,
            project_id="__unmapped__",
            source_tool=SourceTool.JENKINS,
            span=identity,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=float(duration_ms) if duration_ms else None,
            status=status,
            payload=payload,
        )
        return [envelope]
