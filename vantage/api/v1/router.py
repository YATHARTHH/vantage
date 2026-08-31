from fastapi import APIRouter
from vantage.api.v1.ingest import router as ingest_router

api_v1_router = APIRouter()
api_v1_router.include_router(ingest_router)
