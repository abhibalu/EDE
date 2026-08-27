"""
Primitives — The atomic types that every node builds on.

Design decisions (carried from V2):
1. IDs are strings validated by pattern, not branded types.
   Reason: they serialize to JSON and LLMs produce them as strings.
2. CodeRef is a structured object, not a "file:line" string.
   Reason: LLMs are inconsistent with delimiter formats.
3. The Registry is a first-class artifact, not implicit.
   Reason: every ID prefix derives from it. No hardcoded project knowledge.
4. Severity and Priority are closed enums.
   Reason: these drive the semantic constraint "CRITICAL -> MUST".
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel


# -- Base Model ---------------------------------------------------------------

class EdeBaseModel(BaseModel):
    """Base for all EDE models. camelCase JSON aliases for V2 compatibility."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


# -- ID Patterns -------------------------------------------------------------
# Structural validation (Layer 1). Referential integrity is Layer 2.

AggCode = Annotated[
    str, StringConstraints(pattern=r"^[A-Z]{2,4}$")
]

EventID = Annotated[
    str, StringConstraints(pattern=r"^E-[A-Z]{2,4}-\d{1,3}$")
]

GapID = Annotated[
    str, StringConstraints(pattern=r"^[A-Z]{2,4}-G\d{1,3}$")
]

GoalID = Annotated[
    str, StringConstraints(pattern=r"^G\d{1,2}(\.\d{1,2})?$")
]

ObstacleID = Annotated[
    str, StringConstraints(pattern=r"^O-([A-Z]{2,4}|XA)-\d{1,3}$|^O-N\d{1,3}$")
]

ReqID = Annotated[
    str, StringConstraints(pattern=r"^R-([A-Z]{2,4}|XA)-\d{1,3}$")
]


# -- Code References ----------------------------------------------------------
# Never stores content. Only pointers. "Never store code" contract.

class CodeRef(EdeBaseModel):
    file: str = Field(min_length=1)
    anchor: str = Field(min_length=1)


# -- Enums --------------------------------------------------------------------

class Severity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"


class Priority(StrEnum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    COULD = "COULD"


class StateType(StrEnum):
    ATOMIC = "atomic"
    COMPOUND = "compound"
    PARALLEL = "parallel"
    FINAL = "final"


class TransitionAnnotation(StrEnum):
    DISCOVERED = "DISCOVERED"
    PROPOSED = "PROPOSED"


class ResolutionType(StrEnum):
    NEW_REQUIREMENT = "New requirement"
    GOAL_WEAKENING = "Goal weakening"
    OPERATIONAL_WORKAROUND = "Operational workaround"


class GoalDecomposition(StrEnum):
    AND = "AND"
    OR = "OR"


class ArchitectureType(StrEnum):
    MONOREPO = "monorepo"
    FRONTEND_ONLY = "frontend-only"
    BACKEND_ONLY = "backend-only"
    FULLSTACK = "fullstack"


# -- Registry -----------------------------------------------------------------
# Established at Node 0, immutable thereafter. Backbone for all ID validation.

class AreaDef(EdeBaseModel):
    code: AggCode
    name: str = Field(min_length=1)
    directories: list[str] = Field(min_length=1)


class Registry(EdeBaseModel):
    project: str = Field(min_length=1)
    version: Literal["0.1.0"]
    areas: list[AreaDef] = Field(min_length=1)


# -- Pipeline Metadata --------------------------------------------------------
# Every node output carries this envelope.

class PipelineEnvelope(EdeBaseModel):
    pipeline_version: Literal["0.1.0"]
    node: int = Field(ge=0, le=4)
    generated_at: datetime
    registry: Registry


# -- Hot Spot -----------------------------------------------------------------

class HotSpot(EdeBaseModel):
    description: str = Field(min_length=1)
    location: CodeRef


# -- Finding ------------------------------------------------------------------
# Shared by constraints.py and assemblers.py (no duplication).

class FindingLevel(StrEnum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


class Finding(EdeBaseModel):
    level: FindingLevel
    node: int
    where: str
    message: str
    rule: str | None = None
