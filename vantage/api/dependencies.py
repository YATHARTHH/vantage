from functools import lru_cache
from pathlib import Path
from fastapi import Depends
from vantage.core.config import get_settings
from vantage.core.security import verify_api_key
from vantage.enrichment.cost_enricher import CostEnricher
from vantage.enrichment.pii_filter import PIIFilter
from vantage.enrichment.project_mapper import ProjectMapper
from vantage.services.ingestion_service import IngestionService
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository
from vantage.storage.sqlalchemy.session import get_session_factory

require_api_key = verify_api_key


@lru_cache
def get_telemetry_repository() -> DuckDBTelemetryRepository:
    settings = get_settings()
    return DuckDBTelemetryRepository(settings.duckdb_path)


@lru_cache
def get_metadata_repository() -> SQLiteMetadataRepository:
    session_factory = get_session_factory()
    return SQLiteMetadataRepository(session_factory)


@lru_cache
def get_cost_enricher() -> CostEnricher:
    settings = get_settings()
    return CostEnricher(settings.cost_model_path)


def get_project_mapper(
    metadata_repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
) -> ProjectMapper:
    return ProjectMapper(metadata_repo)


def get_pii_filter(
    metadata_repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
) -> PIIFilter:
    return PIIFilter(metadata_repo)


def get_ingestion_service(
    telemetry_repo: DuckDBTelemetryRepository = Depends(get_telemetry_repository),
    project_mapper: ProjectMapper = Depends(get_project_mapper),
    pii_filter: PIIFilter = Depends(get_pii_filter),
    cost_enricher: CostEnricher = Depends(get_cost_enricher),
) -> IngestionService:
    return IngestionService(telemetry_repo, project_mapper, pii_filter, cost_enricher)
