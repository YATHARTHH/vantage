from vantage.core.logging import get_logger
from vantage.domain.events import TelemetryEnvelope
from vantage.enrichment.cost_enricher import CostEnricher
from vantage.enrichment.pii_filter import PIIFilter
from vantage.enrichment.project_mapper import ProjectMapper
from vantage.storage.base import AbstractTelemetryRepository

logger = get_logger(__name__)


class IngestionService:
    """
    Orchestrates the full enrichment and ingestion pipeline:
      1. ProjectMapper   (resolve source_tool + identifier -> project_id)
      2. PIIFilter       (strip prompts per project.log_prompts)
      3. CostEnricher    (tokens x model_prices.json -> cost_usd)
      4. Dedup check     (RETURNING * -> skip if stored=False)
    """

    def __init__(
        self,
        event_repo: AbstractTelemetryRepository,
        project_mapper: ProjectMapper,
        pii_filter: PIIFilter,
        cost_enricher: CostEnricher,
    ):
        self._repo = event_repo
        self._mapper = project_mapper
        self._pii = pii_filter
        self._cost = cost_enricher

    async def ingest(self, envelope: TelemetryEnvelope) -> str | None:
        source_id = (
            envelope.project_id
            if envelope.project_id and envelope.project_id != "__unmapped__"
            else (
                envelope.span.source_trace_id
                or envelope.span.trace_id
                or envelope.external_event_id
                or "unknown"
            )
        )
        resolved_project_id = await self._mapper.resolve_project_id(
            envelope.source_tool.value, source_id
        )

        if resolved_project_id:
            envelope = envelope.model_copy(update={"project_id": resolved_project_id})

        envelope = await self._pii.apply(envelope)
        envelope = await self._cost.apply(envelope)

        stored = await self._repo.insert(envelope)
        if not stored:
            logger.debug("event_deduplicated", external_event_id=envelope.external_event_id)
            return None

        return str(envelope.event_id)

    async def ingest_batch(self, envelopes: list[TelemetryEnvelope]) -> dict:
        stored = 0
        deduped = 0
        for env in envelopes:
            res = await self.ingest(env)
            if res:
                stored += 1
            else:
                deduped += 1

        logger.info("batch_ingestion_summary", stored=stored, deduplicated=deduped)
        return {"stored": stored, "deduplicated": deduped}
