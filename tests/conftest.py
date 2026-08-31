import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from vantage.api.app import app
from vantage.api.dependencies import get_metadata_repository, get_telemetry_repository
from vantage.storage.duckdb.telemetry_repository import DuckDBTelemetryRepository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository
from vantage.storage.sqlalchemy.session import get_engine, get_session_factory, init_db


@pytest.fixture
async def async_client(tmp_path: Path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_metadata.db'}"
    engine = get_engine(db_url)
    session_factory = get_session_factory(engine)
    await init_db(engine)
    meta_repo = SQLiteMetadataRepository(session_factory)

    duck_repo = DuckDBTelemetryRepository(tmp_path / "test_telemetry.duckdb")

    app.dependency_overrides[get_metadata_repository] = lambda: meta_repo
    app.dependency_overrides[get_telemetry_repository] = lambda: duck_repo

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()
    await duck_repo.close()
