from fastapi import APIRouter
from vantage.api.v1.alerts import router as alerts_router
from vantage.api.v1.analytics import router as analytics_router
from vantage.api.v1.cache import router as cache_router
from vantage.api.v1.ingest import router as ingest_router
from vantage.api.v1.projects import router as projects_router
from vantage.api.v1.query import router as query_router
from vantage.api.v1.registry import router as registry_router

from vantage.api.v1.policy import router as policy_router
from vantage.api.v1.api_keys import router as api_keys_router
from vantage.api.v1.audit import router as audit_router
from vantage.api.v1.replay import router as replay_router

api_v1_router = APIRouter()
api_v1_router.include_router(ingest_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(query_router)
api_v1_router.include_router(registry_router)
api_v1_router.include_router(cache_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(policy_router)
api_v1_router.include_router(api_keys_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(replay_router)
