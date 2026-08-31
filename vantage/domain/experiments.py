from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field


class ExperimentStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ARCHIVED = "archived"


class ExperimentOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"
    PIVOTED = "pivoted"


class ModelConfiguration(BaseModel):
    model_name: str
    model_provider: str
    temperature: float | None = None
    max_tokens: int | None = None
    system_prompt_hash: str | None = None
    other_params: dict[str, str] = Field(default_factory=dict)


class ExperimentResult(BaseModel):
    outcome: ExperimentOutcome
    summary: str
    metrics: dict[str, float] = Field(default_factory=dict)
    learnings: str
    recommendations: str | None = None
    known_limitations: str | None = None


class Artefact(BaseModel):
    label: str
    url: str
    artefact_type: str


class Experiment(BaseModel):
    id: str
    title: str
    slug: str
    project_id: str | None = None
    status: ExperimentStatus = ExperimentStatus.PLANNED

    hypothesis: str
    objective: str
    owner_name: str
    owner_team: str
    owner_email: str
    start_date: date
    expected_end: date

    dataset_description: str | None = None
    baseline_description: str | None = None
    model_configurations: list[ModelConfiguration] = Field(default_factory=list)

    actual_end: date | None = None
    result: ExperimentResult | None = None
    artefacts: list[Artefact] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)

    created_at: datetime | None = None
    updated_at: datetime | None = None
