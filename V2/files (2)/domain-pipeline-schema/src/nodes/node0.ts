/**
 * Node 0 — Codebase Reconnaissance
 *
 * Pure structural scan. No domain analysis.
 * Seeds the Registry that all subsequent nodes inherit.
 *
 * Validation layers:
 *   L1 (schema): field presence, types, enums
 *   L2 (referential): area codes unique; dispatch plan areas match registry
 *   L3 (semantic): keyFiles count within bounds; schema entities non-empty if persistence declared
 */

import { z } from "zod";
import {
  PipelineEnvelope,
  ArchitectureType,
  AreaDef,
} from "../primitives.js";

// ── Sub-structures ──────────────────────────────────────────────────────────

export const Identity = z.object({
  repo: z.string().min(1),
  languages: z.array(z.string().min(1)).min(1),
  frameworks: z.array(z.string()),
  packageManagers: z.array(z.string()),
});

export const Architecture = z.object({
  type: ArchitectureType,
  frontendDir: z.string().nullable(),
  backendDir: z.string().nullable(),
  sharedDir: z.string().nullable(),
});

export const Persistence = z.object({
  database: z.string(),
  orm: z.string(),
  schemaLocation: z.string().nullable(),
  storage: z.string().nullable(),
});

export const ExternalService = z.object({
  name: z.string().min(1),
  purpose: z.string().min(1),
  configLocation: z.string().min(1),
});

export const SchemaEntity = z.object({
  table: z.string().min(1),
  keyColumns: z.array(z.string().min(1)).min(1),
  relationships: z.array(z.string()),
});

export const KeyFile = z.object({
  path: z.string().min(1),
  rationale: z.string().min(1),
});

// ── Node 0 Output ───────────────────────────────────────────────────────────

export const Node0Output = PipelineEnvelope.extend({
  node: z.literal(0),
  identity: Identity,
  architecture: Architecture,
  persistence: Persistence,
  externalServices: z.array(ExternalService),
  dispatchPlan: z.array(AreaDef).min(1),
  schemaEntities: z.array(SchemaEntity),
  keyFiles: z.array(KeyFile).min(1).max(20),
});

export type Node0Output = z.infer<typeof Node0Output>;
