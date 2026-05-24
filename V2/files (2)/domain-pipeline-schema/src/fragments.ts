/**
 * Fragment Schemas — Sub-Agent Output Types
 *
 * Sub-agents produce fragments. Fragments are smaller, easier to validate,
 * and don't carry the full pipeline envelope. The assembler merges fragments
 * into the final Node output.
 *
 * Key difference from final schemas:
 * - No EventIDs, GapIDs, ObstacleIDs — the assembler assigns these
 * - Predecessor/successor links use event NAMES, not IDs
 * - No pipeline envelope — fragments are intermediate, not stored long-term
 *   (though they CAN be stored for debugging/audit)
 */

import { z } from "zod";
import { AggCode, CodeRef, HotSpot, Severity, StateType, TransitionAnnotation, ResolutionType } from "./primitives.js";

// ── Node 1 Fragment ─────────────────────────────────────────────────────────
// One per scan area. Sub-agent reads code, extracts events, links by name.

export const EventFragment = z.object({
  /** PascalCase past tense. This is the dedup key. */
  name: z
    .string()
    .regex(/^[A-Z][a-zA-Z0-9]+$/, "PascalCase event name"),
  trigger: z.string().min(1),
  location: CodeRef,
  /** Link by name, not ID. Assembler resolves to EventIDs. */
  predecessorNames: z.array(z.string()),
  /** Link by name, not ID. Assembler resolves to EventIDs. */
  successorNames: z.array(z.string()),
  stateChange: z.string().min(1),
  evidence: z.string().min(10, "Evidence must contain actual code observation"),
  hotSpots: z.array(HotSpot),
});
export type EventFragment = z.infer<typeof EventFragment>;

export const Node1Fragment = z.object({
  areaCode: AggCode,
  areaName: z.string().min(1),
  filesScanned: z.array(z.string().min(1)).min(1),
  filesSkipped: z.array(z.string()),
  events: z.array(EventFragment),
});
export type Node1Fragment = z.infer<typeof Node1Fragment>;

// ── Node 2 Fragment ─────────────────────────────────────────────────────────
// One per aggregate. Sub-agent discovers states (ReAct) and maps transitions.
// Gap IDs are provisional (just sequential numbers) — assembler prefixes them.

export const StateFragment = z.object({
  name: z.string().min(1),
  type: StateType,
  representation: z.string().min(1),
  location: CodeRef,
  evidence: z.string().min(10),
});

export const TransitionFragment = z.object({
  source: z.string().min(1),         // state name
  target: z.string().min(1),         // state name
  eventName: z.string().min(1),      // event NAME, not ID — assembler resolves
  guard: z.string().nullable(),
  sideEffects: z.array(z.string()),
  annotation: TransitionAnnotation.nullable(),
});

export const GapFragment = z.object({
  /** Sequential number only. Assembler prefixes with AggCode. */
  seq: z.number().int().min(1),
  severity: Severity,
  description: z.string().min(1),
  codeLocation: CodeRef,
});

export const Node2Fragment = z.object({
  aggCode: AggCode,
  aggName: z.string().min(1),
  rootEntity: z.string().min(1),
  keyFiles: z.array(CodeRef).min(1),
  states: z.array(StateFragment).min(1),
  transitions: z.array(TransitionFragment),
  gaps: z.array(GapFragment),
  trivialLifecycle: z.boolean(),
});
export type Node2Fragment = z.infer<typeof Node2Fragment>;

// ── Node 3 Fragment ─────────────────────────────────────────────────────────
// One per aggregate. Forward obstacle analysis results.
// Obstacle IDs are provisional sequential numbers — assembler assigns O-N{seq}.

export const ObstacleFragment = z.object({
  /** Sequential number. Assembler assigns global O-N{seq}. */
  seq: z.number().int().min(1),
  /** Goal IDs (these are already assigned by the orchestrator). */
  violatesGoals: z.array(z.string()).min(1),
  evidence: z.string().min(1),
  description: z.string().min(1),
  severity: Severity,
  resolutionType: ResolutionType,
});

export const Node3Fragment = z.object({
  aggCode: AggCode,
  aggName: z.string().min(1),
  newObstacles: z.array(ObstacleFragment),
});
export type Node3Fragment = z.infer<typeof Node3Fragment>;
