"""
Fragment Schemas -- Sub-Agent Output Types

Sub-agents produce fragments. Fragments are smaller, easier to validate,
and don't carry the full pipeline envelope. The assembler merges fragments
into the final Node output.

Key difference from final schemas:
- No EventIDs, GapIDs, ObstacleIDs -- the assembler assigns these
- Predecessor/successor links use event NAMES, not IDs
- No pipeline envelope -- fragments are intermediate, not stored long-term
  (though they CAN be stored for debugging/audit)
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from .primitives import (
    AggCode,
    CodeRef,
    EdeBaseModel,
    HotSpot,
    ResolutionType,
    Severity,
    StateType,
    TransitionAnnotation,
)


# -- Node 1 Fragment ----------------------------------------------------------
# One per scan area. Sub-agent reads code, extracts events, links by name.

class EventFragment(EdeBaseModel):
    """Event without assigned ID. Uses event name for linking."""

    name: Annotated[str, StringConstraints(pattern=r"^[A-Z][a-zA-Z0-9]+$")]
    trigger: str = Field(min_length=1)
    location: CodeRef
    predecessor_names: list[str]
    successor_names: list[str]
    state_change: str = Field(min_length=1)
    evidence: str = Field(min_length=10)
    hot_spots: list[HotSpot]


class Node1Fragment(EdeBaseModel):
    area_code: AggCode
    area_name: str = Field(min_length=1)
    files_scanned: list[str] = Field(min_length=1)
    files_skipped: list[str]
    events: list[EventFragment]


# -- Node 2 Fragment ----------------------------------------------------------
# One per aggregate. Sub-agent discovers states and maps transitions.
# Gap IDs are provisional (just sequential numbers) -- assembler prefixes them.

class StateFragment(EdeBaseModel):
    name: str = Field(min_length=1)
    type: StateType
    representation: str = Field(min_length=1)
    location: CodeRef
    evidence: str = Field(min_length=10)


class TransitionFragment(EdeBaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    event_name: str = Field(min_length=1)  # event NAME, not ID
    guard: str | None
    side_effects: list[str]
    annotation: TransitionAnnotation | None
    evidence: str = Field(min_length=10)
    code_location: CodeRef


class GapFragment(EdeBaseModel):
    """Sequential number only. Assembler prefixes with AggCode."""

    seq: int = Field(ge=1)
    severity: Severity
    description: str = Field(min_length=1)
    code_location: CodeRef


class Node2Fragment(EdeBaseModel):
    agg_code: AggCode
    agg_name: str = Field(min_length=1)
    root_entity: str = Field(min_length=1)
    key_files: list[CodeRef] = Field(min_length=1)
    states: list[StateFragment] = Field(min_length=1)
    transitions: list[TransitionFragment]
    gaps: list[GapFragment]
    trivial_lifecycle: bool


# -- Node 3 Fragment ----------------------------------------------------------
# One per aggregate. Forward obstacle analysis results.

class ObstacleFragment(EdeBaseModel):
    """Sequential number. Assembler assigns global O-N{seq}."""

    seq: int = Field(ge=1)
    violates_goals: list[str] = Field(min_length=1)
    evidence: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Severity
    resolution_type: ResolutionType


class Node3Fragment(EdeBaseModel):
    agg_code: AggCode
    agg_name: str = Field(min_length=1)
    new_obstacles: list[ObstacleFragment]
