/**
 * @ootomic/domain-pipeline-schema
 *
 * Formal grammar for the domain extraction pipeline.
 * Three validation layers:
 *   L1 — Schema (Zod parse): structural validity
 *   L2 — Referential integrity: IDs resolve across nodes
 *   L3 — Semantic invariants: domain-level correctness
 *
 * Usage:
 *   import { Node1Output, validatePipeline } from '@ootomic/domain-pipeline-schema';
 *
 *   // L1: parse and validate structure
 *   const parsed = Node1Output.parse(rawJson);
 *
 *   // L2 + L3: cross-reference checks
 *   const result = validatePipeline({ node0, node1: parsed });
 *   if (!result.valid) { ... }
 */

// ── Primitives ──────────────────────────────────────────────────────────────
export {
  AggCode,
  EventID,
  GapID,
  GoalID,
  ObstacleID,
  ReqID,
  CodeRef,
  Severity,
  Priority,
  StateType,
  TransitionAnnotation,
  ResolutionType,
  GoalDecomposition,
  ArchitectureType,
  AreaDef,
  Registry,
  PipelineEnvelope,
  HotSpot,
} from "./primitives.js";

// ── Node schemas ────────────────────────────────────────────────────────────
export { Node0Output } from "./nodes/node0.js";
export { Node1Output, DomainEvent, ScanArea } from "./nodes/node1.js";
export {
  Node2Output,
  Aggregate,
  StateEntry,
  Transition,
  Gap,
  CrossAggTransition,
  ImpossibleCombination,
  MigrationCandidate,
} from "./nodes/node2.js";
export {
  Node3Output,
  GoalNode,
  ConfirmedObstacle,
  NewObstacle,
  Requirement,
  Phase,
} from "./nodes/node3.js";
export { Node4Output, FileIndexEntry } from "./nodes/node4.js";

// ── Validators ──────────────────────────────────────────────────────────────
export {
  validateNode0,
  validateNode1,
  validateNode2,
  validateNode3,
  validateNode4,
  validatePipeline,
} from "./constraints.js";
export type {
  Finding,
  FindingLevel,
  PipelineData,
  ValidationResult,
} from "./constraints.js";

// ── Fragments (sub-agent output schemas) ────────────────────────────────
export {
  EventFragment,
  Node1Fragment,
  Node2Fragment,
  Node3Fragment,
} from "./fragments.js";

// ── Assemblers (deterministic fragment → node output) ───────────────────
export {
  assembleNode1,
  assembleNode2,
} from "./assemblers.js";
export type {
  AssembleNode1Input,
  AssembleNode2Input,
  AssembleResult,
} from "./assemblers.js";
