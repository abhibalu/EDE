/**
 * Node 1 — Domain Event Extraction
 *
 * Every event is a factual claim about code. The `evidence` field is
 * the ReAct grounding mechanism: it records the observation (code snippet
 * or pattern match) that justifies the event's existence.
 *
 * Validation layers:
 *   L1 (schema): field presence, ID format, CodeRef structure
 *   L2 (referential): predecessor/successor IDs resolve within catalogue;
 *                      area code prefix matches registry
 *   L3 (semantic): event names PascalCase+past tense;
 *                   no self-referential predecessor/successor;
 *                   evidence field non-empty (ReAct contract)
 */

import { z } from "zod";
import {
  PipelineEnvelope,
  EventID,
  CodeRef,
  HotSpot,
} from "../primitives.js";

// ── Domain Event ────────────────────────────────────────────────────────────

export const DomainEvent = z.object({
  id: EventID,
  name: z
    .string()
    .min(1)
    .regex(
      /^[A-Z][a-zA-Z0-9]+$/,
      "Event name must be PascalCase (e.g., AudioMixedWithAmbient)"
    ),
  trigger: z.string().min(1),
  location: CodeRef,
  predecessors: z.array(EventID),
  successors: z.array(EventID),
  stateChange: z.string().min(1),
  hotSpots: z.array(HotSpot),

  /**
   * ReAct grounding: the code evidence that proves this event exists.
   * Must contain the actual code pattern observed (status assignment,
   * DB write, API call, etc). An empty evidence field = ungrounded claim.
   *
   * This is NOT a free-text justification. It's a structured observation:
   * what was literally seen in the code that constitutes this state change.
   */
  evidence: z.string().min(10, "Evidence must contain actual code observation"),
});

export type DomainEvent = z.infer<typeof DomainEvent>;

// ── Scan metadata ───────────────────────────────────────────────────────────

export const ScanArea = z.object({
  name: z.string().min(1),
  areaCode: z.string().regex(/^[A-Z]{2,4}$/),
  directories: z.array(z.string().min(1)).min(1),
  filesScanned: z.array(z.string().min(1)),
  filesSkipped: z.array(z.string()),
});

// ── Node 1 Output ───────────────────────────────────────────────────────────

export const Node1Output = PipelineEnvelope.extend({
  node: z.literal(1),
  metadata: z.object({
    totalFilesScanned: z.number().int().min(0),
    scanAreas: z.array(ScanArea).min(1),
  }),
  events: z
    .array(DomainEvent)
    .max(50, "Catalogue capped at 50 events"),
  hotSpotSummary: z.array(HotSpot),

  /**
   * If more than 50 events exist, record what was truncated.
   * null = no truncation.
   */
  truncation: z
    .object({
      estimatedTotal: z.number().int(),
      areasAffected: z.array(z.string()),
    })
    .nullable(),
});

export type Node1Output = z.infer<typeof Node1Output>;
