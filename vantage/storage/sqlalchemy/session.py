from pathlib import Path
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from vantage.core.config import get_settings
from vantage.storage.sqlalchemy.models import Base


def get_engine(database_url: str | None = None) -> AsyncEngine:
    url = database_url or get_settings().database_url
    if url.startswith("sqlite"):
        # Extract file path if local sqlite database
        path_str = url.split(":///")[-1] if ":///" in url else ""
        if path_str and not path_str.startswith(":memory:"):
            db_file = Path(path_str)
            db_file.parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(url, echo=False, future=True)


def get_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    eng = engine or get_engine()
    return async_sessionmaker(eng, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine | None = None) -> None:
    eng = engine or get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
