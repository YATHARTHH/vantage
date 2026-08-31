from datetime import datetime, timezone
from typing import Any
from vantage.connectors.base import AbstractConnector
from vantage.domain.events import (
    BuildData,
    DeployData,
    EventStatus,
    SourceTool,
    SpanIdentity,
    TelemetryEnvelope,
)


class GitHubWebhookConnector(AbstractConnector):
    """Parses GitHub Actions workflow_run webhooks into TelemetryEnvelope objects."""

    def parse(self, raw_payload: dict[str, Any]) -> list[TelemetryEnvelope]:
        action = raw_payload.get("action")
        if action not in ("completed", "requested", "in_progress"):
            return []

        workflow_run = raw_payload.get("workflow_run", {})
        if not workflow_run:
            return []

        run_id = str(workflow_run.get("id"))
        repo_name = raw_payload.get("repository", {}).get("full_name", "unknown")
        workflow_name = workflow_run.get("name", "workflow")
        branch = workflow_run.get("head_branch", "main")
        commit_sha = workflow_run.get("head_sha")
        event_trigger = workflow_run.get("event", "push")

        conclusion = workflow_run.get("conclusion")
        if conclusion == "success":
            status = EventStatus.SUCCESS
        elif conclusion in ("failure", "timed_out"):
            status = EventStatus.ERROR
        elif conclusion == "cancelled":
            status = EventStatus.CANCELLED
        else:
            status = EventStatus.RUNNING

        created_at_str = workflow_run.get("created_at")
        updated_at_str = workflow_run.get("updated_at")

        started_at = (
            datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime.now(timezone.utc)
        )
        ended_at = (
            datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            if updated_at_str
            else None
        )

        identity = SpanIdentity(
            trace_id=f"gh-{run_id}",
            span_id=f"gh-run-{run_id}",
            source_trace_id=run_id,
            source_span_id=run_id,
        )

        ext_event_id = f"github-{repo_name}-{run_id}"

        if "deploy" in workflow_name.lower():
            payload = DeployData(
                repo_name=repo_name,
                environment="production",
                version=commit_sha[:7] if commit_sha else None,
                commit_sha=commit_sha,
                pipeline_name=workflow_name,
            )
        else:
            payload = BuildData(
                repo_name=repo_name,
                branch=branch,
                commit_sha=commit_sha,
                pipeline_name=workflow_name,
                triggered_by=event_trigger,
            )

        envelope = TelemetryEnvelope(
            external_event_id=ext_event_id,
            project_id="__unmapped__",
            source_tool=SourceTool.GITHUB_ACTIONS,
            span=identity,
            started_at=started_at,
            ended_at=ended_at,
            status=status,
            payload=payload,
        )
        return [envelope]
