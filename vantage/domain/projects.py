from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    AI_LLM = "ai_llm"
    SOFTWARE = "software"
    POC_EXPERIMENT = "poc_experiment"
    MIXED = "mixed"


class SourceToolMapping(BaseModel):
    """
    Maps one external source identifier → Vantage project_id.
    """
    id: int | None = None
    project_id: str
    source_tool: str
    source_identifier: str
    display_label: str | None = None
    created_at: datetime | None = None


class Project(BaseModel):
    """The central entity that all telemetry is attached to."""
    id: str
    display_name: str
    project_type: ProjectType
    owner_team: str
    owner_email: str
    description: str | None = None

    log_prompts: bool = False
    active: bool = True

    source_mappings: list[SourceToolMapping] = Field(default_factory=list)
    created_at: datetime | None = None
