"""
Node 2 -- Aggregate & Statechart Extraction

Clusters events into aggregates, extracts implicit state machines,
performs gap analysis.

Validation layers:
  L1 (schema): field presence, ID formats, enum values
  L2 (referential): aggregate codes match registry; transition.event
                     resolves to Node 1 catalogue; gap ID prefixes match aggregate
  L3 (semantic): no dead-end states without justification;
                  gap severity distribution sensible
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from ..primitives import (
    AggCode,
    CodeRef,
    EdeBaseModel,
    EventID,
    GapID,
    PipelineEnvelope,
    Severity,
    StateType,
    TransitionAnnotation,
)


class StateEntry(EdeBaseModel):
    name: str = Field(min_length=1)
    type: StateType
    representation: str = Field(min_length=1)
    location: CodeRef
    evidence: str = Field(min_length=10)


class Transition(EdeBaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    event: EventID
    guard: str | None
    side_effects: list[str]
    annotation: TransitionAnnotation | None
    evidence: str = Field(min_length=10)
    code_location: CodeRef


class Gap(EdeBaseModel):
    id: GapID
    severity: Severity
    description: str = Field(min_length=1)
    code_location: CodeRef


class Aggregate(EdeBaseModel):
    code: AggCode
    name: str = Field(min_length=1)
    root_entity: str = Field(min_length=1)
    key_files: list[CodeRef] = Field(min_length=1)
    states: list[StateEntry] = Field(min_length=1)
    transitions: list[Transition]
    gaps: list[Gap]
    trivial_lifecycle: bool = False


class CrossAggTransition(EdeBaseModel):
    from_event: EventID
    from_aggregate: AggCode
    to_event: EventID
    to_aggregate: AggCode
    mechanism: str = Field(min_length=1)


class ImpossibleCombination(EdeBaseModel):
    combination: str = Field(min_length=1)
    risk: str = Field(min_length=1)
    source: str = Field(min_length=1)


class MigrationCandidate(EdeBaseModel):
    rank: int = Field(ge=1)
    aggregate: AggCode
    rationale: str = Field(min_length=1)


class GapSummary(EdeBaseModel):
    """L1 promotion: total must equal sum of components."""

    critical: int = Field(ge=0)
    high: int = Field(ge=0)
    med: int = Field(ge=0)
    low: int = Field(ge=0)
    total: int = Field(ge=0)

    @model_validator(mode="after")
    def check_total(self) -> Self:
        expected = self.critical + self.high + self.med + self.low
        if self.total != expected:
            raise ValueError(f"total ({self.total}) != sum of components ({expected})")
        return self


class Node2Output(PipelineEnvelope):
    node: Literal[2]
    aggregates: list[Aggregate] = Field(min_length=1)
    cross_agg_transitions: list[CrossAggTransition]
    impossible_combinations: list[ImpossibleCombination]
    migration_priority: list[MigrationCandidate]
    gap_summary: GapSummary
