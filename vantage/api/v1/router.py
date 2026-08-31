from fastapi import APIRouter
from vantage.api.v1.alerts import router as alerts_router
from vantage.api.v1.ingest import router as ingest_router
from vantage.api.v1.projects import router as projects_router
from vantage.api.v1.query import router as query_router

api_v1_router = APIRouter()
api_v1_router.include_router(ingest_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(query_router)
