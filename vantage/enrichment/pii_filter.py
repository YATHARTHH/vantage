from vantage.core.logging import get_logger
from vantage.domain.events import LLMCallData, TelemetryEnvelope, ToolCallData
from vantage.storage.base import AbstractMetadataRepository

logger = get_logger(__name__)


class PIIFilter:
    """
    Per-project PII filtering.
    Strips prompt_preview, completion_preview, tool_input, tool_output
    unless log_prompts is enabled for the target project.
    """

    def __init__(self, metadata_repo: AbstractMetadataRepository):
        self._repo = metadata_repo
        self._cache: dict[str, bool] = {}

    async def apply(self, envelope: TelemetryEnvelope) -> TelemetryEnvelope:
        if envelope.project_id == "__unmapped__":
            log_prompts = False
        else:
            log_prompts = await self._should_log_prompts(envelope.project_id)

        if log_prompts:
            return envelope

        payload = envelope.payload
        needs_update = False

        if isinstance(payload, LLMCallData):
            if payload.prompt_preview or payload.completion_preview:
                payload = payload.model_copy(
                    update={"prompt_preview": None, "completion_preview": None}
                )
                needs_update = True
        elif isinstance(payload, ToolCallData):
            if payload.tool_input or payload.tool_output:
                payload = payload.model_copy(
                    update={"tool_input": None, "tool_output": None}
                )
                needs_update = True

        if needs_update:
            logger.debug("pii_stripped", project_id=envelope.project_id)
            return envelope.model_copy(update={"payload": payload})

        return envelope

    async def _should_log_prompts(self, project_id: str) -> bool:
        if project_id not in self._cache:
            project = await self._repo.get_project(project_id)
            self._cache[project_id] = project.log_prompts if project else False
        return self._cache[project_id]

    def invalidate_cache(self, project_id: str | None = None) -> None:
        if project_id:
            self._cache.pop(project_id, None)
        else:
            self._cache.clear()
