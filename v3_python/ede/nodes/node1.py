"""
Node 1 -- Domain Event Extraction

Every event is a factual claim about code. The `evidence` field is
the ReAct grounding mechanism: it records the observation that justifies
the event's existence.

Validation layers:
  L1 (schema): field presence, ID format, CodeRef structure
  L2 (referential): predecessor/successor IDs resolve within catalogue;
                     area code prefix matches registry
  L3 (semantic): event names PascalCase; no self-referential links;
                  evidence field non-empty (ReAct contract)
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from ..primitives import (
    CodeRef,
    EdeBaseModel,
    EventID,
    HotSpot,
    PipelineEnvelope,
)


class DomainEvent(EdeBaseModel):
    id: EventID
    name: Annotated[str, StringConstraints(min_length=1, pattern=r"^[A-Z][a-zA-Z0-9]+$")]
    trigger: str = Field(min_length=1)
    location: CodeRef
    predecessors: list[EventID]
    successors: list[EventID]
    state_change: str = Field(min_length=1)
    hot_spots: list[HotSpot]
    evidence: str = Field(min_length=10)


class ScanArea(EdeBaseModel):
    name: str = Field(min_length=1)
    area_code: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2,4}$")]
    directories: list[str] = Field(min_length=1)
    files_scanned: list[str]
    files_skipped: list[str]


class TruncationInfo(EdeBaseModel):
    estimated_total: int
    areas_affected: list[str]


class Node1Metadata(EdeBaseModel):
    total_files_scanned: int = Field(ge=0)
    scan_areas: list[ScanArea] = Field(min_length=1)


class Node1Output(PipelineEnvelope):
    node: Literal[1]
    metadata: Node1Metadata
    events: list[DomainEvent]
    hot_spot_summary: list[HotSpot]
    truncation: TruncationInfo | None
