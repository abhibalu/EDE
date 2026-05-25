"""
Node 4 -- Spec Assembly

Compiles all prior node outputs into a single artifact.
No new analysis -- only compilation and cross-referencing.

The Node4Output is the STORED format (JSON). Human-readable markdown
is a rendering concern handled separately.

Validation layers:
  L1 (schema): structural validity
  L2 (referential): file index req IDs resolve; all prior IDs preserved
  L3 (semantic): metrics match actual counts; every requirement appears
                  in file index and roadmap
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, StringConstraints
from typing import Annotated

from ..primitives import EdeBaseModel, PipelineEnvelope, ReqID


class FileCategory(StrEnum):
    BACKEND_ROUTER = "backend-router"
    BACKEND_SERVICE = "backend-service"
    BACKEND_AGENT = "backend-agent"
    FRONTEND_HOOK = "frontend-hook"
    FRONTEND_COMPONENT = "frontend-component"
    FRONTEND_STATE = "frontend-state"
    CONFIG = "config"
    SCHEMA = "schema"
    SHARED = "shared"
    OTHER = "other"


class FileIndexEntry(EdeBaseModel):
    file: str = Field(min_length=1)
    category: FileCategory
    requirements: list[ReqID] = Field(min_length=1)


class ChangelogEntry(EdeBaseModel):
    date: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    change: str = Field(min_length=1)


class Node4Metrics(EdeBaseModel):
    total_goals: int
    total_aggregates: int
    total_events: int
    total_gaps: int
    confirmed_obstacles: int
    new_obstacles: int
    total_requirements: int
    must: int
    should: int
    could: int
    phases: int
    files_indexed: int


class SourceRefs(EdeBaseModel):
    node0: str = Field(min_length=1)
    node1: str = Field(min_length=1)
    node2: str = Field(min_length=1)
    node3: str = Field(min_length=1)


class Node4Output(PipelineEnvelope):
    node: Literal[4]
    system_purpose: str = Field(min_length=1)
    file_index: list[FileIndexEntry]
    changelog: list[ChangelogEntry] = Field(min_length=1)
    metrics: Node4Metrics
    sources: SourceRefs
