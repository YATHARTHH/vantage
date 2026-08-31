from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from vantage.api.v1.router import api_v1_router
from vantage.ui.router import ui_router
from vantage.core.config import get_settings
from vantage.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("application_startup", name="Vantage")
    yield
    logger.info("application_shutdown", name="Vantage")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Unified AI & Engineering Observability Hub",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix=settings.api_prefix)
    app.include_router(ui_router)

    @app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    @app.get("/ready", status_code=status.HTTP_200_OK, tags=["Health"])
    async def readiness_check():
        return {
            "status": "ready",
            "olap_backend": settings.olap_backend,
            "database_url": settings.database_url.split("://")[0],
        }

    return app


app = create_app()
