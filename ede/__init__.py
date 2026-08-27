"""
EDE -- Domain Extraction Engine

Formal grammar and validators for the 5-node domain extraction pipeline.
Three validation layers:
  L1 -- Schema (Pydantic parse): structural validity
  L2 -- Referential integrity: IDs resolve across nodes
  L3 -- Semantic invariants: domain-level correctness

Usage:
  from ede import Node1Output, validate_pipeline

  # L1: parse and validate structure
  parsed = Node1Output.model_validate(raw_json)

  # L2 + L3: cross-reference checks
  result = validate_pipeline({"node0": n0, "node1": parsed})
  if not result["valid"]: ...
"""

# -- Primitives ---------------------------------------------------------------
from .primitives import (
    AggCode,
    ArchitectureType,
    AreaDef,
    CodeRef,
    EdeBaseModel,
    EventID,
    Finding,
    FindingLevel,
    GapID,
    GoalDecomposition,
    GoalID,
    HotSpot,
    ObstacleID,
    PipelineEnvelope,
    Priority,
    Registry,
    ReqID,
    ResolutionType,
    Severity,
    StateType,
    TransitionAnnotation,
)

# -- Node schemas -------------------------------------------------------------
from .nodes import (
    Aggregate,
    Architecture,
    ChangelogEntry,
    ConfirmedObstacle,
    CrossAggTransition,
    DomainEvent,
    ExternalService,
    FileCategory,
    FileIndexEntry,
    Gap,
    GapSummary,
    GoalNode,
    Identity,
    ImpossibleCombination,
    KeyFile,
    MigrationCandidate,
    NewObstacle,
    Node0Output,
    Node1Metadata,
    Node1Output,
    Node2Output,
    Node3Metrics,
    Node3Output,
    Node4Metrics,
    Node4Output,
    Persistence,
    Phase,
    Requirement,
    ScanArea,
    SchemaEntity,
    SourceRefs,
    StateEntry,
    Transition,
    TruncationInfo,
)

# -- Fragments ----------------------------------------------------------------
from .fragments import (
    EventFragment,
    GapFragment,
    Node1Fragment,
    Node2Fragment,
    Node3Fragment,
    ObstacleFragment,
    StateFragment,
    TransitionFragment,
)

# -- Assemblers ---------------------------------------------------------------
from .assemblers import AssembleResult, assemble_node1, assemble_node2, assemble_node3

# -- Renderer -----------------------------------------------------------------
from .renderer import render_markdown

# -- Validators ---------------------------------------------------------------
from .constraints import (
    PipelineData,
    ValidationResult,
    validate_node0,
    validate_node1,
    validate_node2,
    validate_node3,
    validate_node4,
    validate_pipeline,
)

__all__ = [
    # Primitives
    "AggCode", "ArchitectureType", "AreaDef", "CodeRef", "EdeBaseModel",
    "EventID", "Finding", "FindingLevel", "GapID", "GoalDecomposition",
    "GoalID", "HotSpot", "ObstacleID", "PipelineEnvelope", "Priority",
    "Registry", "ReqID", "ResolutionType", "Severity", "StateType",
    "TransitionAnnotation",
    # Nodes
    "Aggregate", "Architecture", "ChangelogEntry", "ConfirmedObstacle",
    "CrossAggTransition", "DomainEvent", "ExternalService", "FileCategory",
    "FileIndexEntry", "Gap", "GapSummary", "GoalNode", "Identity",
    "ImpossibleCombination", "KeyFile", "MigrationCandidate", "NewObstacle",
    "Node0Output", "Node1Metadata", "Node1Output", "Node2Output",
    "Node3Metrics", "Node3Output", "Node4Metrics", "Node4Output",
    "Persistence", "Phase", "Requirement", "ScanArea", "SchemaEntity",
    "SourceRefs", "StateEntry", "Transition", "TruncationInfo",
    # Fragments
    "EventFragment", "GapFragment", "Node1Fragment", "Node2Fragment",
    "Node3Fragment", "ObstacleFragment", "StateFragment", "TransitionFragment",
    # Assemblers
    "AssembleResult", "assemble_node1", "assemble_node2", "assemble_node3",
    # Renderer
    "render_markdown",
    # Validators
    "PipelineData", "ValidationResult", "validate_node0", "validate_node1",
    "validate_node2", "validate_node3", "validate_node4", "validate_pipeline",
]
