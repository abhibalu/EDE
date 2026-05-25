"""
Node 3 -- Goal Tree & Obstacle Register

Reverse-engineers KAOS goals from statecharts, maps gaps to obstacles,
discovers new obstacles via forward analysis, produces requirements delta.

Validation layers:
  L1 (schema): field presence, ID formats, enum values, tree structure
  L2 (referential): obstacle.gapSource resolves to Node 2 gap;
                     obstacle.violatesGoal resolves in tree;
                     requirement.resolves resolves to obstacle;
                     phase.requirements all resolve
  L3 (semantic): CRITICAL gaps -> MUST requirements;
                  goal tree root is G0; metrics consistency
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from ..primitives import (
    EdeBaseModel,
    GapID,
    GoalDecomposition,
    GoalID,
    ObstacleID,
    PipelineEnvelope,
    Priority,
    ReqID,
    ResolutionType,
    Severity,
)


class GoalNode(EdeBaseModel):
    id: GoalID
    description: str = Field(min_length=1)
    decomposition: GoalDecomposition | None
    agent: str | None
    children: list[GoalNode] = []
    obstacle_refs: list[ObstacleID] = []


GoalNode.model_rebuild()


class ConfirmedObstacle(EdeBaseModel):
    id: ObstacleID
    violates_goals: list[GoalID] = Field(min_length=1)
    gap_source: GapID
    description: str = Field(min_length=1)
    severity: Severity


class NewObstacle(EdeBaseModel):
    """L1 promotion: ID must use O-N prefix."""

    id: ObstacleID
    violates_goals: list[GoalID] = Field(min_length=1)
    evidence: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Severity
    resolution_type: ResolutionType

    @model_validator(mode="after")
    def check_new_prefix(self) -> Self:
        if not self.id.startswith("O-N"):
            raise ValueError(f"New obstacle ID must use O-N prefix, got: {self.id}")
        return self


class Requirement(EdeBaseModel):
    id: ReqID
    priority: Priority
    description: str = Field(min_length=1)
    resolves: list[ObstacleID] = Field(min_length=1)


class Phase(EdeBaseModel):
    number: int = Field(ge=1)
    name: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    requirements: list[ReqID] = Field(min_length=1)
    gaps_closed: list[str]  # GapID or ObstacleID — union validated by pattern
    risk_reduced: str = Field(min_length=1)


class Node3Metrics(EdeBaseModel):
    """L1 promotion: total_requirements must equal must + should + could."""

    total_goals: int = Field(ge=1)
    leaf_goals: int = Field(ge=1)
    confirmed_obstacles: int = Field(ge=0)
    new_obstacles: int = Field(ge=0)
    total_requirements: int = Field(ge=0)
    must: int = Field(ge=0)
    should: int = Field(ge=0)
    could: int = Field(ge=0)

    @model_validator(mode="after")
    def check_totals(self) -> Self:
        if self.total_requirements != self.must + self.should + self.could:
            raise ValueError(
                f"totalRequirements ({self.total_requirements}) "
                f"!= must + should + could ({self.must + self.should + self.could})"
            )
        return self


class Node3Output(PipelineEnvelope):
    node: Literal[3]
    goal_tree: GoalNode
    confirmed_obstacles: list[ConfirmedObstacle]
    new_obstacles: list[NewObstacle]
    requirements: list[Requirement]
    roadmap: list[Phase] = Field(min_length=1)
    metrics: Node3Metrics
