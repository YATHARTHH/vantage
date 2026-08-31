from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from vantage.api.dependencies import get_metadata_repository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository

templates_dir = Path(__file__).parent.parent / "api" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(prefix="/experiments", tags=["UI Experiments"])


@router.get("", summary="Experiments List UI")
async def experiments_list_ui(
    request: Request,
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    experiments = await repo.list_experiments()
    return templates.TemplateResponse(
        "experiments/list.html",
        {"request": request, "experiments": [e.model_dump() for e in experiments]},
    )
