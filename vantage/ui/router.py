from fastapi import APIRouter
from vantage.ui.experiments import router as experiments_ui_router
from vantage.ui.projects import router as projects_ui_router

ui_router = APIRouter(prefix="/ui")
ui_router.include_router(projects_ui_router)
ui_router.include_router(experiments_ui_router)
