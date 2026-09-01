from vantage.core.logging import get_logger
from vantage.domain.events import TelemetryEnvelope, SecurityMetadata
from vantage.enrichment.cost_enricher import CostEnricher
from vantage.enrichment.pii_filter import PIIFilter
from vantage.enrichment.project_mapper import ProjectMapper
from vantage.security.jailbreak_detector import JailbreakDetector
from vantage.services.security_alert_service import SecurityAlertService
from vantage.storage.base import AbstractTelemetryRepository

logger = get_logger(__name__)


class IngestionService:
    """
    Orchestrates the full enrichment, security scan, and ingestion pipeline:
      1. ProjectMapper       (resolve source_tool + identifier -> project_id)
      2. JailbreakDetector   (Security Scan BEFORE PII Filter to inspect raw prompt content)
      3. PIIFilter           (strip prompts per project.log_prompts policy)
      4. CostEnricher        (tokens x model_prices.json -> cost_usd)
      5. Storage             (DuckDB insert with deduplication)
      6. SecurityAlertService(Deduplicated alert generation for HIGH/CRITICAL threat risks)
    """

    def __init__(
        self,
        event_repo: AbstractTelemetryRepository,
        project_mapper: ProjectMapper,
        pii_filter: PIIFilter,
        cost_enricher: CostEnricher,
        jailbreak_detector: JailbreakDetector | None = None,
        security_alert_service: SecurityAlertService | None = None,
    ):
        self._repo = event_repo
        self._mapper = project_mapper
        self._pii = pii_filter
        self._cost = cost_enricher
        self._detector = jailbreak_detector or JailbreakDetector()
        self._security_alerts = security_alert_service

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

        # Step 2: Security Scan BEFORE PII Filtering
        try:
            scan_result = self._detector.scan_envelope(envelope)
            envelope = envelope.model_copy(
                update={
                    "security": SecurityMetadata(
                        scanned=True,
                        is_threat=scan_result.is_threat,
                        risk_level=scan_result.risk_level.value,
                        threat_types=[t.value for t in scan_result.threat_types],
                        threat_score=scan_result.threat_score,
                        matched_rules=scan_result.matched_rules,
                        evidence=scan_result.evidence,
                        scanner_version=scan_result.scanner_version,
                    )
                }
            )
        except Exception as e:
            logger.error(f"Error during security scan execution: {e}")

        # Step 3: PII Filter (strips prompt per logging policy)
        envelope = await self._pii.apply(envelope)

        # Step 4: Cost Enrichment
        envelope = await self._cost.apply(envelope)

        # Step 5: Storage
        stored = await self._repo.insert(envelope)
        if not stored:
            logger.debug("event_deduplicated", external_event_id=envelope.external_event_id)
            return None

        # Step 6: Security Alert Service
        if self._security_alerts and envelope.security and envelope.security.is_threat:
            try:
                await self._security_alerts.process_security_envelope(envelope)
            except Exception as e:
                logger.error(f"Error processing security alert for envelope {envelope.event_id}: {e}")

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
