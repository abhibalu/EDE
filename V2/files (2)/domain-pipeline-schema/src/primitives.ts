/**
 * @ootomic/domain-pipeline-schema — Primitives
 *
 * The atomic types that every node builds on.
 *
 * Design decisions:
 * 1. IDs are strings validated by pattern, not branded types.
 *    Reason: they serialize to JSON and LLMs produce them as strings.
 * 2. CodeRef is a structured object, not a "file:line" string.
 *    Reason: LLMs are inconsistent with delimiter formats. Explicit fields
 *    eliminate ambiguity and make file-existence checks trivial.
 * 3. The Registry is a first-class artifact, not implicit.
 *    Reason: every ID prefix derives from it. No hardcoded project knowledge.
 * 4. Severity and Priority are closed enums.
 *    Reason: these drive the semantic constraint "CRITICAL → MUST".
 *    Allowing freeform text would break that invariant.
 */

import { z } from "zod";

// ── ID Patterns ─────────────────────────────────────────────────────────────
// These are the regex patterns for structural validation (Layer 1).
// Referential integrity (do these IDs actually resolve?) is Layer 2,
// handled by the constraint validators.

/** 2-4 uppercase letters. Derived from aggregate/area names. */
export const AggCode = z
  .string()
  .regex(/^[A-Z]{2,4}$/, "AggCode must be 2-4 uppercase letters");

/** E-{AggCode}-{seq} — domain events get IDs starting at Node 1 */
export const EventID = z
  .string()
  .regex(/^E-[A-Z]{2,4}-\d{1,3}$/, "EventID format: E-XX-01");

/** {AggCode}-G{seq} — gaps identified in statechart analysis */
export const GapID = z
  .string()
  .regex(/^[A-Z]{2,4}-G\d{1,3}$/, "GapID format: XX-G1");

/** G{n} or G{n}.{m} — KAOS goal tree nodes */
export const GoalID = z
  .string()
  .regex(/^G\d{1,2}(\.\d{1,2})?$/, "GoalID format: G0, G1, G1.2");

/**
 * Obstacle IDs come in two flavours:
 * - Confirmed (from gap): O-{AggCode}-{seq}
 * - New (from forward analysis): O-N{seq}
 */
export const ObstacleID = z
  .string()
  .regex(
    /^O-([A-Z]{2,4}|XA)-\d{1,3}$|^O-N\d{1,3}$/,
    "ObstacleID format: O-XX-1 or O-N1"
  );

/** R-{AggCode|XA}-{seq} — requirements. XA = cross-aggregate. */
export const ReqID = z
  .string()
  .regex(/^R-([A-Z]{2,4}|XA)-\d{1,3}$/, "ReqID format: R-XX-01 or R-XA-01");

// ── Code References ─────────────────────────────────────────────────────────
// Never stores content. Only pointers. This is the "never store code" contract.

export const CodeRef = z.object({
  file: z.string().min(1, "File path cannot be empty"),
  /** Function name, line number, or line range. Whatever the LLM found. */
  anchor: z.string().min(1, "Anchor (function/line) cannot be empty"),
});
export type CodeRef = z.infer<typeof CodeRef>;

// ── Enums ───────────────────────────────────────────────────────────────────

export const Severity = z.enum(["CRITICAL", "HIGH", "MED", "LOW"]);
export type Severity = z.infer<typeof Severity>;

export const Priority = z.enum(["MUST", "SHOULD", "COULD"]);
export type Priority = z.infer<typeof Priority>;

export const StateType = z.enum(["atomic", "compound", "parallel", "final"]);
export type StateType = z.infer<typeof StateType>;

export const TransitionAnnotation = z.enum(["DISCOVERED", "PROPOSED"]);
export type TransitionAnnotation = z.infer<typeof TransitionAnnotation>;

export const ResolutionType = z.enum([
  "New requirement",
  "Goal weakening",
  "Operational workaround",
]);
export type ResolutionType = z.infer<typeof ResolutionType>;

export const GoalDecomposition = z.enum(["AND", "OR"]);
export type GoalDecomposition = z.infer<typeof GoalDecomposition>;

export const ArchitectureType = z.enum([
  "monorepo",
  "frontend-only",
  "backend-only",
  "fullstack",
]);
export type ArchitectureType = z.infer<typeof ArchitectureType>;

// ── Registry ────────────────────────────────────────────────────────────────
// Established at Node 0, refined at Node 2. This is the backbone that
// parameterizes all ID validation downstream.

export const AreaDef = z.object({
  code: AggCode,
  name: z.string().min(1),
  directories: z.array(z.string()).min(1),
});
export type AreaDef = z.infer<typeof AreaDef>;

export const Registry = z.object({
  project: z.string().min(1),
  version: z.literal("0.1.0"),
  areas: z.array(AreaDef).min(1),
});
export type Registry = z.infer<typeof Registry>;

// ── Pipeline metadata ───────────────────────────────────────────────────────
// Every node output carries this envelope. Makes storage and retrieval trivial.

export const PipelineEnvelope = z.object({
  pipelineVersion: z.literal("0.1.0"),
  node: z.number().int().min(0).max(4),
  generatedAt: z.string().datetime(),
  registry: Registry,
});
export type PipelineEnvelope = z.infer<typeof PipelineEnvelope>;

// ── Hot Spot ────────────────────────────────────────────────────────────────

export const HotSpot = z.object({
  description: z.string().min(1),
  location: CodeRef,
});
export type HotSpot = z.infer<typeof HotSpot>;
