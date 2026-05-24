/**
 * Node 3 — Goal Tree & Obstacle Register
 *
 * Reverse-engineers KAOS goals from statecharts, maps gaps to obstacles,
 * discovers new obstacles via forward analysis, produces requirements delta.
 *
 * No ReAct needed here: confirmed obstacles trace to Node 2 gaps (already
 * grounded), and the goal tree is analytical construction. New obstacles
 * from forward analysis carry evidence references but don't need the full
 * Thought→Action→Observation loop.
 *
 * Validation layers:
 *   L1 (schema): field presence, ID formats, enum values, tree structure
 *   L2 (referential): obstacle.gapSource resolves to Node 2 gap;
 *                      obstacle.violatesGoal resolves in tree;
 *                      requirement.resolves resolves to obstacle;
 *                      phase.requirements all resolve
 *   L3 (semantic): CRITICAL gaps → MUST requirements;
 *                   every leaf goal served by ≥1 aggregate;
 *                   no orphan obstacles; no untethered requirements;
 *                   goal tree has exactly one root (G0)
 */

import { z } from "zod";
import {
  PipelineEnvelope,
  AggCode,
  GapID,
  GoalID,
  ObstacleID,
  ReqID,
  CodeRef,
  Severity,
  Priority,
  ResolutionType,
  GoalDecomposition,
} from "../primitives.js";

// ── Goal Tree ───────────────────────────────────────────────────────────────

export interface GoalNodeType {
  id: string;
  description: string;
  decomposition: "AND" | "OR" | null;
  agent: string | null;
  children: GoalNodeType[];
  obstacleRefs: string[];
}

export const GoalNode: z.ZodType<GoalNodeType> = z.lazy(() =>
  z.object({
    id: GoalID,
    description: z.string().min(1),
    decomposition: GoalDecomposition.nullable(),
    agent: z.string().nullable(),
    children: z.array(GoalNode),
    obstacleRefs: z.array(ObstacleID),
  })
);

// ── Obstacles ───────────────────────────────────────────────────────────────

export const ConfirmedObstacle = z.object({
  id: ObstacleID,
  violatesGoals: z.array(GoalID).min(1),
  gapSource: GapID,
  description: z.string().min(1),
  severity: Severity,
});
export type ConfirmedObstacle = z.infer<typeof ConfirmedObstacle>;

export const NewObstacle = z.object({
  id: ObstacleID.refine((s) => s.startsWith("O-N"), "New obstacles use O-N prefix"),
  violatesGoals: z.array(GoalID).min(1),
  evidence: z.string().min(1),
  description: z.string().min(1),
  severity: Severity,
  resolutionType: ResolutionType,
});
export type NewObstacle = z.infer<typeof NewObstacle>;

// ── Requirements ────────────────────────────────────────────────────────────

export const Requirement = z.object({
  id: ReqID,
  priority: Priority,
  description: z.string().min(1),
  resolves: z.array(ObstacleID).min(1, "Every requirement must resolve at least one obstacle"),
});
export type Requirement = z.infer<typeof Requirement>;

// ── Roadmap ─────────────────────────────────────────────────────────────────

export const Phase = z.object({
  number: z.number().int().min(1),
  name: z.string().min(1),
  scope: z.string().min(1),
  requirements: z.array(ReqID).min(1),
  gapsClosed: z.array(z.union([GapID, ObstacleID])),
  riskReduced: z.string().min(1),
});
export type Phase = z.infer<typeof Phase>;

// ── Node 3 Output ───────────────────────────────────────────────────────────

export const Node3Output = PipelineEnvelope.extend({
  node: z.literal(3),
  goalTree: GoalNode,
  confirmedObstacles: z.array(ConfirmedObstacle),
  newObstacles: z.array(NewObstacle),
  requirements: z.array(Requirement),
  roadmap: z.array(Phase).min(1),
  metrics: z.object({
    totalGoals: z.number().int().min(1),
    leafGoals: z.number().int().min(1),
    confirmedObstacles: z.number().int().min(0),
    newObstacles: z.number().int().min(0),
    totalRequirements: z.number().int().min(0),
    must: z.number().int().min(0),
    should: z.number().int().min(0),
    could: z.number().int().min(0),
  }),
});

export type Node3Output = z.infer<typeof Node3Output>;
