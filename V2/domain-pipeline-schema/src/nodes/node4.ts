/**
 * Node 4 — Spec Assembly
 *
 * Compiles all prior node outputs into a single artifact.
 * Introduces no new analysis — only compilation and cross-referencing.
 *
 * The Node4Output is the STORED format (JSON). The human-readable markdown
 * is a rendering concern handled by a separate renderer module.
 *
 * Validation layers:
 *   L1 (schema): structural validity
 *   L2 (referential): file index req IDs resolve; all prior IDs preserved
 *   L3 (semantic): metrics match actual counts; every requirement appears
 *                   in file index; every requirement appears in roadmap;
 *                   no data lost from prior nodes
 */

import { z } from "zod";
import { PipelineEnvelope, ReqID } from "../primitives.js";

// ── File Index ──────────────────────────────────────────────────────────────
// Maps source files to the requirements that touch them.
// Built by scanning requirement entries for file references — not guessed.

export const FileIndexEntry = z.object({
  file: z.string().min(1),
  category: z.enum([
    "backend-router",
    "backend-service",
    "backend-agent",
    "frontend-hook",
    "frontend-component",
    "frontend-state",
    "config",
    "schema",
    "shared",
    "other",
  ]),
  requirements: z.array(ReqID).min(1),
});
export type FileIndexEntry = z.infer<typeof FileIndexEntry>;

// ── Changelog ───────────────────────────────────────────────────────────────

export const ChangelogEntry = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  change: z.string().min(1),
});

// ── Node 4 Output ───────────────────────────────────────────────────────────
// The compiled spec as structured data. Contains references to prior node
// outputs but does NOT duplicate them inline — the prior JSONs remain the
// source of truth. Node 4 adds cross-cutting concerns: file index, changelog,
// computed metrics, and renders to markdown.

export const Node4Output = PipelineEnvelope.extend({
  node: z.literal(4),

  /** Summary of system purpose — one paragraph, not re-analysis. */
  systemPurpose: z.string().min(1),

  /** File index: which files are touched by which requirements. */
  fileIndex: z.array(FileIndexEntry),

  /** Initialised with baseline entry. */
  changelog: z.array(ChangelogEntry).min(1),

  /**
   * Computed metrics. Validated against actual counts from prior nodes.
   * Any mismatch = assembly error.
   */
  metrics: z.object({
    totalGoals: z.number().int(),
    totalAggregates: z.number().int(),
    totalEvents: z.number().int(),
    totalGaps: z.number().int(),
    confirmedObstacles: z.number().int(),
    newObstacles: z.number().int(),
    totalRequirements: z.number().int(),
    must: z.number().int(),
    should: z.number().int(),
    could: z.number().int(),
    phases: z.number().int(),
    filesIndexed: z.number().int(),
  }),

  /**
   * References to the source node outputs.
   * In storage, these could be URIs or object IDs.
   * In local execution, these are file paths.
   */
  sources: z.object({
    node0: z.string().min(1),
    node1: z.string().min(1),
    node2: z.string().min(1),
    node3: z.string().min(1),
  }),
});

export type Node4Output = z.infer<typeof Node4Output>;
