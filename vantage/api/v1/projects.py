from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from vantage.api.dependencies import get_metadata_repository, require_api_key
from vantage.domain.projects import Project, ProjectType, SourceToolMapping
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository

from vantage.auth.rbac import RequirePermission, AuthContext

router = APIRouter(prefix="/projects", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    id: str
    display_name: str
    project_type: ProjectType = ProjectType.AI_LLM
    owner_team: str
    owner_email: str
    description: str | None = None
    log_prompts: bool = False


class CreateSourceMappingRequest(BaseModel):
    source_tool: str
    source_identifier: str
    display_label: str | None = None


@router.get("", summary="List all registered projects")
async def list_projects(
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
    auth: AuthContext = Depends(RequirePermission("projects.read")),
):
    projects = await repo.list_projects()
    return [p.model_dump() for p in projects]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new project")
async def create_project(
    req: CreateProjectRequest,
    _: str = Depends(require_api_key),
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    existing = await repo.get_project(req.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with ID '{req.id}' already exists.",
        )

    project = Project(
        id=req.id,
        display_name=req.display_name,
        project_type=req.project_type,
        owner_team=req.owner_team,
        owner_email=req.owner_email,
        description=req.description,
        log_prompts=req.log_prompts,
    )
    saved = await repo.save_project(project)
    return saved.model_dump()


@router.get("/{project_id}", summary="Get project by ID")
async def get_project(
    project_id: str,
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return project.model_dump()


@router.post(
    "/{project_id}/mappings",
    status_code=status.HTTP_201_CREATED,
    summary="Add source mapping to project",
)
async def add_source_mapping(
    project_id: str,
    req: CreateSourceMappingRequest,
    _: str = Depends(require_api_key),
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
):
    project = await repo.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    mapping = SourceToolMapping(
        project_id=project_id,
        source_tool=req.source_tool,
        source_identifier=req.source_identifier,
        display_label=req.display_label,
    )
    saved = await repo.save_source_mapping(mapping)
    return saved.model_dump()
