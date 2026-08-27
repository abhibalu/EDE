"""
Node 0 -- Codebase Reconnaissance

Pure structural scan. No domain analysis.
Seeds the Registry that all subsequent nodes inherit.

Validation layers:
  L1 (schema): field presence, types, enums
  L2 (referential): area codes unique; dispatch plan areas match registry
  L3 (semantic): keyFiles count within bounds; schema entities non-empty if persistence declared
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ..primitives import (
    AreaDef,
    ArchitectureType,
    EdeBaseModel,
    PipelineEnvelope,
)


class Identity(EdeBaseModel):
    repo: str = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    frameworks: list[str]
    package_managers: list[str]


class Architecture(EdeBaseModel):
    type: ArchitectureType
    frontend_dir: str | None
    backend_dir: str | None
    shared_dir: str | None


class Persistence(EdeBaseModel):
    database: str
    orm: str
    schema_location: str | None
    storage: str | None


class ExternalService(EdeBaseModel):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    config_location: str = Field(min_length=1)


class SchemaEntity(EdeBaseModel):
    table: str = Field(min_length=1)
    key_columns: list[str] = Field(min_length=1)
    relationships: list[str]


class KeyFile(EdeBaseModel):
    path: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class Node0Output(PipelineEnvelope):
    node: Literal[0]
    identity: Identity
    architecture: Architecture
    persistence: Persistence
    external_services: list[ExternalService]
    dispatch_plan: list[AreaDef] = Field(min_length=1)
    schema_entities: list[SchemaEntity]
    key_files: list[KeyFile] = Field(min_length=1, max_length=20)
