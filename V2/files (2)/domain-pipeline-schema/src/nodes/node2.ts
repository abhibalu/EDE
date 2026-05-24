/**
 * Node 2 — Aggregate & Statechart Extraction
 *
 * Clusters events into aggregates, extracts implicit state machines,
 * performs gap analysis. State discovery carries evidence (partial ReAct);
 * statechart construction is analytical reasoning over validated Node 1 data.
 *
 * Validation layers:
 *   L1 (schema): field presence, ID formats, enum values
 *   L2 (referential): aggregate codes match registry; transition.event
 *                      resolves to Node 1 catalogue; gap ID prefixes match aggregate
 *   L3 (semantic): no dead-end states without justification;
 *                   every event referenced; gap severity distribution sensible;
 *                   aggregate codes unique; state names unique within aggregate
 */

import { z } from "zod";
import {
  PipelineEnvelope,
  AggCode,
  EventID,
  GapID,
  CodeRef,
  Severity,
  StateType,
  TransitionAnnotation,
} from "../primitives.js";

// ── State ───────────────────────────────────────────────────────────────────

export const StateEntry = z.object({
  name: z.string().min(1),
  type: StateType,
  representation: z
    .string()
    .min(1, "How this state appears in code (enum value, boolean combo, etc)"),
  location: CodeRef,

  /** ReAct grounding for state discovery: what code pattern reveals this state. */
  evidence: z.string().min(10, "State must be evidenced from code"),
});
export type StateEntry = z.infer<typeof StateEntry>;

// ── Transition ──────────────────────────────────────────────────────────────

export const Transition = z.object({
  source: z.string().min(1),
  target: z.string().min(1),
  event: EventID,
  guard: z.string().nullable(),
  sideEffects: z.array(z.string()),
  annotation: TransitionAnnotation.nullable(),
});
export type Transition = z.infer<typeof Transition>;

// ── Gap ─────────────────────────────────────────────────────────────────────

export const Gap = z.object({
  id: GapID,
  severity: Severity,
  description: z.string().min(1),
  codeLocation: CodeRef,
});
export type Gap = z.infer<typeof Gap>;

// ── Aggregate ───────────────────────────────────────────────────────────────

export const Aggregate = z.object({
  code: AggCode,
  name: z.string().min(1),
  rootEntity: z.string().min(1),
  keyFiles: z.array(CodeRef).min(1),
  states: z.array(StateEntry).min(1),
  transitions: z.array(Transition),
  gaps: z.array(Gap),
  /** If ≤2 states: "trivial lifecycle". Full analysis only if 3+. */
  trivialLifecycle: z.boolean().default(false),
});
export type Aggregate = z.infer<typeof Aggregate>;

// ── Cross-aggregate structures ──────────────────────────────────────────────

export const CrossAggTransition = z.object({
  fromEvent: EventID,
  fromAggregate: AggCode,
  toEvent: EventID,
  toAggregate: AggCode,
  mechanism: z.string().min(1),
});

export const ImpossibleCombination = z.object({
  combination: z.string().min(1),
  risk: z.string().min(1),
  source: z.string().min(1),
});

export const MigrationCandidate = z.object({
  rank: z.number().int().min(1),
  aggregate: AggCode,
  rationale: z.string().min(1),
});

// ── Node 2 Output ───────────────────────────────────────────────────────────

export const Node2Output = PipelineEnvelope.extend({
  node: z.literal(2),
  aggregates: z.array(Aggregate).min(1),
  crossAggTransitions: z.array(CrossAggTransition),
  impossibleCombinations: z.array(ImpossibleCombination),
  migrationPriority: z.array(MigrationCandidate),
  gapSummary: z.object({
    critical: z.number().int().min(0),
    high: z.number().int().min(0),
    med: z.number().int().min(0),
    low: z.number().int().min(0),
    total: z.number().int().min(0),
  }),
});

export type Node2Output = z.infer<typeof Node2Output>;
