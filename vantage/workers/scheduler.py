from apscheduler.schedulers.asyncio import AsyncIOScheduler
from vantage.core.config import get_settings
from vantage.core.logging import get_logger

logger = get_logger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler()
    logger.info(
        "scheduler_created",
        anomaly_interval=settings.anomaly_interval_minutes,
        rollup_interval=settings.rollup_interval_minutes,
    )
    return scheduler
