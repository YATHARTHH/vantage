from datetime import date
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from vantage.api.dependencies import get_metadata_repository, require_api_key
from vantage.domain.experiments import (
    Experiment,
    ExperimentOutcome,
    ExperimentResult,
    ExperimentStatus,
)
from vantage.services.registry_service import RegistryService
from vantage.storage.sqlalchemy.metadata_repository import SQLiteMetadataRepository

router = APIRouter(prefix="/experiments", tags=["Experiment Registry"])


def get_registry_service(
    repo: SQLiteMetadataRepository = Depends(get_metadata_repository),
) -> RegistryService:
    return RegistryService(repo)


class CreateExperimentRequest(BaseModel):
    id: str
    title: str
    slug: str
    project_id: str | None = None
    hypothesis: str
    objective: str
    owner_name: str
    owner_team: str
    owner_email: str
    start_date: date
    expected_end: date
    dataset_description: str | None = None
    baseline_description: str | None = None


class RecordResultRequest(BaseModel):
    outcome: ExperimentOutcome
    summary: str
    metrics: dict[str, float] = {}
    learnings: str
    recommendations: str | None = None


@router.get("", summary="List all experiments")
async def list_experiments(
    project_id: str | None = None,
    status: str | None = None,
    registry_svc: RegistryService = Depends(get_registry_service),
):
    experiments = await registry_svc.list_experiments(project_id=project_id, status=status)
    return [e.model_dump() for e in experiments]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create new experiment")
async def create_experiment(
    req: CreateExperimentRequest,
    _: str = Depends(require_api_key),
    registry_svc: RegistryService = Depends(get_registry_service),
):
    existing = await registry_svc.get_experiment(req.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Experiment '{req.id}' already exists.",
        )

    experiment = Experiment(
        id=req.id,
        title=req.title,
        slug=req.slug,
        project_id=req.project_id,
        hypothesis=req.hypothesis,
        objective=req.objective,
        owner_name=req.owner_name,
        owner_team=req.owner_team,
        owner_email=req.owner_email,
        start_date=req.start_date,
        expected_end=req.expected_end,
        dataset_description=req.dataset_description,
        baseline_description=req.baseline_description,
        status=ExperimentStatus.PLANNED,
    )
    saved = await registry_svc.save_experiment(experiment)
    return saved.model_dump()


@router.get("/{experiment_id}", summary="Get experiment by ID")
async def get_experiment(
    experiment_id: str,
    registry_svc: RegistryService = Depends(get_registry_service),
):
    exp = await registry_svc.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found.",
        )
    return exp.model_dump()


@router.post("/{experiment_id}/result", summary="Record experiment result")
async def record_experiment_result(
    experiment_id: str,
    req: RecordResultRequest,
    _: str = Depends(require_api_key),
    registry_svc: RegistryService = Depends(get_registry_service),
):
    result = ExperimentResult(
        outcome=req.outcome,
        summary=req.summary,
        metrics=req.metrics,
        learnings=req.learnings,
        recommendations=req.recommendations,
    )
    updated = await registry_svc.record_result(experiment_id, result)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment '{experiment_id}' not found.",
        )
    return updated.model_dump()
