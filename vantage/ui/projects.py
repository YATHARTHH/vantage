from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from vantage.api.dependencies import get_metadata_repository
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository

templates_dir = Path(__file__).parent.parent / "api" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(prefix="/projects", tags=["UI Projects"])


@router.get("", summary="Projects List UI")
async def projects_list_ui(
    request: Request,
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    projects = await repo.list_projects()
    return templates.TemplateResponse(
        "projects/list.html",
        {"request": request, "projects": [p.model_dump() for p in projects]},
    )
