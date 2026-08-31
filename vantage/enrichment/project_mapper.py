from datetime import datetime, timedelta, timezone
from vantage.core.logging import get_logger
from vantage.storage.base import AbstractMetadataRepository

logger = get_logger(__name__)


class ProjectMapper:
    """
    Resolves external telemetry source identifiers to Vantage project_ids.
    Uses a 60-second in-memory cache to avoid database queries per event.
    """

    def __init__(self, metadata_repo: AbstractMetadataRepository, cache_ttl_seconds: int = 60):
        self._repo = metadata_repo
        self._ttl = cache_ttl_seconds
        # Cache structure: (source_tool, source_identifier) -> (project_id, expires_at)
        self._cache: dict[tuple[str, str], tuple[str, datetime]] = {}

    async def resolve_project_id(self, source_tool: str, source_identifier: str) -> str:
        cache_key = (source_tool, source_identifier)
        now = datetime.now(timezone.utc)

        if cache_key in self._cache:
            project_id, expires_at = self._cache[cache_key]
            if now < expires_at:
                return project_id
            del self._cache[cache_key]

        mapping = await self._repo.get_source_mapping(source_tool, source_identifier)
        if mapping:
            expires_at = now + timedelta(seconds=self._ttl)
            self._cache[cache_key] = (mapping.project_id, expires_at)
            return mapping.project_id

        logger.warning("unmapped_source", source_tool=source_tool, source_identifier=source_identifier)
        return "__unmapped__"

    def invalidate_cache(self, source_tool: str | None = None, source_identifier: str | None = None) -> None:
        if source_tool and source_identifier:
            self._cache.pop((source_tool, source_identifier), None)
        else:
            self._cache.clear()
