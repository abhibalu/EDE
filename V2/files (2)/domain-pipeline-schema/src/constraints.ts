/**
 * Constraint Validators — Layers 2 & 3
 *
 * Layer 1 (schema) is handled by Zod parse().
 * Layer 2 (referential integrity) checks that IDs resolve across nodes.
 * Layer 3 (semantic invariants) checks domain-level correctness.
 *
 * All validators are project-agnostic. They derive allowed ID prefixes
 * from the Registry, not from hardcoded constants.
 *
 * Each validator returns a Finding[] — same concept as the Python validator,
 * but typed and structured.
 */

import type { Node0Output } from "./nodes/node0.js";
import type { Node1Output } from "./nodes/node1.js";
import type { Node2Output } from "./nodes/node2.js";
import type { Node3Output } from "./nodes/node3.js";
import type { Node4Output } from "./nodes/node4.js";

// ── Finding ─────────────────────────────────────────────────────────────────

export type FindingLevel = "ERROR" | "WARN" | "INFO";

export interface Finding {
  level: FindingLevel;
  node: number;
  where: string;
  message: string;
  /** Optional: which constraint rule was violated */
  rule?: string;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function error(node: number, where: string, message: string, rule?: string): Finding {
  return { level: "ERROR", node, where, message, rule };
}

function warn(node: number, where: string, message: string, rule?: string): Finding {
  return { level: "WARN", node, where, message, rule };
}

function info(node: number, where: string, message: string, rule?: string): Finding {
  return { level: "INFO", node, where, message, rule };
}

/** Extract the AggCode prefix from a compound ID. */
function aggPrefix(id: string): string | null {
  // E-MS-01 → MS,  MS-G1 → MS,  O-MS-1 → MS,  R-MS-01 → MS
  const m = id.match(/^(?:E-|R-|O-)([A-Z]{2,4})-/) || id.match(/^([A-Z]{2,4})-G/);
  return m ? m[1] : null;
}

// ── Node 0 Constraints ─────────────────────────────────────────────────────

export function validateNode0(n0: Node0Output): Finding[] {
  const findings: Finding[] = [];
  const codes = new Set<string>();

  for (const area of n0.registry.areas) {
    if (codes.has(area.code)) {
      findings.push(error(0, `Registry area ${area.code}`, "Duplicate area code", "L2-unique-area-codes"));
    }
    codes.add(area.code);
  }

  // dispatch plan areas should match registry
  const registryCodes = new Set(n0.registry.areas.map((a) => a.code));
  for (const dp of n0.dispatchPlan) {
    if (!registryCodes.has(dp.code)) {
      findings.push(
        error(0, `Dispatch plan ${dp.code}`, "Area code not in registry", "L2-dispatch-matches-registry")
      );
    }
  }

  // L3: if persistence.database is not "none", schemaEntities should be non-empty
  if (
    n0.persistence.database.toLowerCase() !== "none" &&
    n0.schemaEntities.length === 0
  ) {
    findings.push(
      warn(0, "Persistence", "Database declared but no schema entities found", "L3-schema-completeness")
    );
  }

  return findings;
}

// ── Node 1 Constraints ─────────────────────────────────────────────────────

export function validateNode1(n1: Node1Output, n0: Node0Output): Finding[] {
  const findings: Finding[] = [];
  const validCodes = new Set(n0.registry.areas.map((a) => a.code));
  const eventIndex = new Map(n1.events.map((e) => [e.id, e]));

  for (const event of n1.events) {
    // L2: area code prefix must be in registry
    const prefix = aggPrefix(event.id);
    if (prefix && !validCodes.has(prefix)) {
      findings.push(
        error(1, `Event ${event.id}`, `Area code '${prefix}' not in registry`, "L2-event-area-code")
      );
    }

    // L2: predecessor/successor IDs must resolve
    for (const pred of event.predecessors) {
      if (!eventIndex.has(pred)) {
        findings.push(
          error(1, `Event ${event.id}`, `Predecessor '${pred}' not found in catalogue`, "L2-predecessor-resolves")
        );
      }
    }
    for (const succ of event.successors) {
      if (!eventIndex.has(succ)) {
        findings.push(
          error(1, `Event ${event.id}`, `Successor '${succ}' not found in catalogue`, "L2-successor-resolves")
        );
      }
    }

    // L3: no self-referential links
    if (event.predecessors.includes(event.id)) {
      findings.push(
        error(1, `Event ${event.id}`, "Lists itself as predecessor", "L3-no-self-reference")
      );
    }
    if (event.successors.includes(event.id)) {
      findings.push(
        error(1, `Event ${event.id}`, "Lists itself as successor", "L3-no-self-reference")
      );
    }

    // L3: predecessor/successor symmetry (if A lists B as successor, B should list A as predecessor)
    for (const succ of event.successors) {
      const target = eventIndex.get(succ);
      if (target && !target.predecessors.includes(event.id)) {
        findings.push(
          warn(
            1,
            `Event ${event.id}`,
            `Lists '${succ}' as successor, but '${succ}' doesn't list '${event.id}' as predecessor`,
            "L3-link-symmetry"
          )
        );
      }
    }
  }

  // L3: if fewer than 5 events, likely missed state changes
  if (n1.events.length < 5 && !n1.truncation) {
    findings.push(
      warn(1, "Event catalogue", `Only ${n1.events.length} events found — likely incomplete`, "L3-minimum-events")
    );
  }

  // L3: unique event IDs
  const seenIds = new Set<string>();
  for (const event of n1.events) {
    if (seenIds.has(event.id)) {
      findings.push(error(1, `Event ${event.id}`, "Duplicate event ID", "L2-unique-event-ids"));
    }
    seenIds.add(event.id);
  }

  return findings;
}

// ── Node 2 Constraints ─────────────────────────────────────────────────────

export function validateNode2(n2: Node2Output, n1: Node1Output): Finding[] {
  const findings: Finding[] = [];
  const eventIndex = new Set(n1.events.map((e) => e.id));
  const aggCodes = new Set<string>();

  for (const agg of n2.aggregates) {
    // L2: unique aggregate codes
    if (aggCodes.has(agg.code)) {
      findings.push(error(2, `Aggregate ${agg.code}`, "Duplicate aggregate code", "L2-unique-agg-codes"));
    }
    aggCodes.add(agg.code);

    // L2: transition events resolve to catalogue
    for (const t of agg.transitions) {
      if (!eventIndex.has(t.event)) {
        findings.push(
          error(
            2,
            `Aggregate ${agg.code}, transition ${t.source}→${t.target}`,
            `Event '${t.event}' not in Node 1 catalogue`,
            "L2-transition-event-resolves"
          )
        );
      }
    }

    // L2: gap ID prefix matches aggregate code
    for (const gap of agg.gaps) {
      const prefix = gap.id.replace(/-G\d+$/, "");
      if (prefix !== agg.code) {
        findings.push(
          error(2, `Gap ${gap.id}`, `Prefix '${prefix}' doesn't match aggregate '${agg.code}'`, "L2-gap-prefix")
        );
      }
    }

    // L2: transition source/target must be declared states
    const stateNames = new Set(agg.states.map((s) => s.name));
    for (const t of agg.transitions) {
      if (!stateNames.has(t.source)) {
        findings.push(
          error(2, `Aggregate ${agg.code}`, `Transition source '${t.source}' is not a declared state`, "L2-state-exists")
        );
      }
      if (!stateNames.has(t.target)) {
        findings.push(
          error(2, `Aggregate ${agg.code}`, `Transition target '${t.target}' is not a declared state`, "L2-state-exists")
        );
      }
    }

    // L3: states with no outgoing transitions (dead ends) — warn unless final
    for (const state of agg.states) {
      if (state.type === "final") continue;
      const hasOutgoing = agg.transitions.some((t) => t.source === state.name);
      if (!hasOutgoing) {
        findings.push(
          warn(
            2,
            `Aggregate ${agg.code}, state '${state.name}'`,
            "No outgoing transitions (dead-end state)",
            "L3-no-dead-ends"
          )
        );
      }
    }

    // L3: unique state names within aggregate
    const seenStates = new Set<string>();
    for (const state of agg.states) {
      if (seenStates.has(state.name)) {
        findings.push(error(2, `Aggregate ${agg.code}`, `Duplicate state name '${state.name}'`, "L2-unique-states"));
      }
      seenStates.add(state.name);
    }
  }

  // L2: cross-aggregate transitions reference valid events and aggregates
  for (const cat of n2.crossAggTransitions) {
    if (!eventIndex.has(cat.fromEvent)) {
      findings.push(
        error(2, "Cross-agg transition", `Event '${cat.fromEvent}' not in catalogue`, "L2-cross-agg-event")
      );
    }
    if (!eventIndex.has(cat.toEvent)) {
      findings.push(
        error(2, "Cross-agg transition", `Event '${cat.toEvent}' not in catalogue`, "L2-cross-agg-event")
      );
    }
    if (!aggCodes.has(cat.fromAggregate)) {
      findings.push(
        error(2, "Cross-agg transition", `Aggregate '${cat.fromAggregate}' not defined`, "L2-cross-agg-code")
      );
    }
    if (!aggCodes.has(cat.toAggregate)) {
      findings.push(
        error(2, "Cross-agg transition", `Aggregate '${cat.toAggregate}' not defined`, "L2-cross-agg-code")
      );
    }
  }

  // L3: gap summary counts match actual
  const actual = { critical: 0, high: 0, med: 0, low: 0, total: 0 };
  for (const agg of n2.aggregates) {
    for (const gap of agg.gaps) {
      actual[gap.severity.toLowerCase() as keyof typeof actual]++;
      actual.total++;
    }
  }
  for (const key of ["critical", "high", "med", "low", "total"] as const) {
    if (n2.gapSummary[key] !== actual[key]) {
      findings.push(
        warn(
          2,
          "Gap summary",
          `Declared ${key}=${n2.gapSummary[key]}, actual=${actual[key]}`,
          "L3-gap-counts-match"
        )
      );
    }
  }

  return findings;
}

// ── Node 3 Constraints ─────────────────────────────────────────────────────

/** Recursively collect all goal IDs from the tree. */
function collectGoalIds(node: { id: string; children?: any[] }): Set<string> {
  const ids = new Set<string>([node.id]);
  for (const child of node.children ?? []) {
    for (const id of collectGoalIds(child)) {
      ids.add(id);
    }
  }
  return ids;
}

/** Collect leaf goal IDs (no children). */
function collectLeafGoals(node: { id: string; children?: any[] }): Set<string> {
  if (!node.children || node.children.length === 0) {
    return new Set([node.id]);
  }
  const leaves = new Set<string>();
  for (const child of node.children) {
    for (const id of collectLeafGoals(child)) {
      leaves.add(id);
    }
  }
  return leaves;
}

export function validateNode3(n3: Node3Output, n2: Node2Output): Finding[] {
  const findings: Finding[] = [];

  const goalIds = collectGoalIds(n3.goalTree);
  const leafGoals = collectLeafGoals(n3.goalTree);
  const gapIndex = new Map<string, string>();
  for (const agg of n2.aggregates) {
    for (const gap of agg.gaps) {
      gapIndex.set(gap.id, gap.severity);
    }
  }

  // Build obstacle index (both confirmed + new)
  const obstacleIndex = new Map<string, { severity: string; violatesGoals: string[] }>();
  for (const o of n3.confirmedObstacles) {
    obstacleIndex.set(o.id, { severity: o.severity, violatesGoals: o.violatesGoals });
  }
  for (const o of n3.newObstacles) {
    obstacleIndex.set(o.id, { severity: o.severity, violatesGoals: o.violatesGoals });
  }

  // L2: confirmed obstacles reference valid gaps
  for (const o of n3.confirmedObstacles) {
    if (!gapIndex.has(o.gapSource)) {
      findings.push(
        error(3, `Obstacle ${o.id}`, `Gap source '${o.gapSource}' not found in Node 2`, "L2-obstacle-gap-source")
      );
    }
  }

  // L2: obstacles reference valid goals
  for (const o of [...n3.confirmedObstacles, ...n3.newObstacles]) {
    for (const gid of o.violatesGoals) {
      if (!goalIds.has(gid)) {
        findings.push(
          error(3, `Obstacle ${o.id}`, `Goal '${gid}' not in goal tree`, "L2-obstacle-goal-ref")
        );
      }
    }
  }

  // L2: requirements resolve valid obstacles
  for (const req of n3.requirements) {
    for (const oid of req.resolves) {
      if (!obstacleIndex.has(oid)) {
        findings.push(
          error(3, `Requirement ${req.id}`, `Resolves '${oid}' which is not a defined obstacle`, "L2-req-resolves")
        );
      }
    }
  }

  // L2: phase requirements all exist
  const reqIndex = new Set(n3.requirements.map((r) => r.id));
  for (const phase of n3.roadmap) {
    for (const rid of phase.requirements) {
      if (!reqIndex.has(rid)) {
        findings.push(
          error(3, `Phase ${phase.number}`, `Requirement '${rid}' not defined`, "L2-phase-req-exists")
        );
      }
    }
  }

  // L3: CRITICAL severity → at least one MUST requirement
  for (const [oid, ob] of obstacleIndex) {
    if (ob.severity === "CRITICAL") {
      const hasMusts = n3.requirements.some(
        (r) => r.priority === "MUST" && r.resolves.includes(oid)
      );
      if (!hasMusts) {
        findings.push(
          warn(
            3,
            `Obstacle ${oid}`,
            "CRITICAL severity but no MUST requirement resolves it",
            "L3-critical-needs-must"
          )
        );
      }
    }
  }

  // L3: every requirement should appear in at least one phase
  const scheduledReqs = new Set(n3.roadmap.flatMap((p) => p.requirements));
  for (const req of n3.requirements) {
    if (!scheduledReqs.has(req.id)) {
      findings.push(
        warn(3, `Requirement ${req.id}`, "Not scheduled in any roadmap phase", "L3-req-in-roadmap")
      );
    }
  }

  // L3: goal tree root is G0
  if (n3.goalTree.id !== "G0") {
    findings.push(error(3, "Goal tree", `Root is '${n3.goalTree.id}', expected 'G0'`, "L3-root-is-G0"));
  }

  // L3: metrics match actual
  const counts = {
    totalGoals: goalIds.size,
    leafGoals: leafGoals.size,
    confirmedObstacles: n3.confirmedObstacles.length,
    newObstacles: n3.newObstacles.length,
    totalRequirements: n3.requirements.length,
    must: n3.requirements.filter((r) => r.priority === "MUST").length,
    should: n3.requirements.filter((r) => r.priority === "SHOULD").length,
    could: n3.requirements.filter((r) => r.priority === "COULD").length,
  };
  for (const [key, actual] of Object.entries(counts)) {
    const declared = n3.metrics[key as keyof typeof n3.metrics];
    if (declared !== undefined && declared !== actual) {
      findings.push(
        warn(3, "Metrics", `'${key}' declared ${declared}, actual ${actual}`, "L3-metrics-match")
      );
    }
  }

  // L2: unique obstacle IDs
  const seenObstacles = new Set<string>();
  for (const o of [...n3.confirmedObstacles, ...n3.newObstacles]) {
    if (seenObstacles.has(o.id)) {
      findings.push(error(3, `Obstacle ${o.id}`, "Duplicate obstacle ID", "L2-unique-obstacle-ids"));
    }
    seenObstacles.add(o.id);
  }

  // L2: unique requirement IDs
  const seenReqs = new Set<string>();
  for (const r of n3.requirements) {
    if (seenReqs.has(r.id)) {
      findings.push(error(3, `Requirement ${r.id}`, "Duplicate requirement ID", "L2-unique-req-ids"));
    }
    seenReqs.add(r.id);
  }

  return findings;
}

// ── Node 4 Constraints ─────────────────────────────────────────────────────

export function validateNode4(
  n4: Node4Output,
  n3: Node3Output,
  n2: Node2Output,
  n1: Node1Output
): Finding[] {
  const findings: Finding[] = [];

  // Collect all requirement IDs from Node 3
  const allReqIds = new Set(n3.requirements.map((r) => r.id));

  // L2: file index references valid requirements
  for (const entry of n4.fileIndex) {
    for (const rid of entry.requirements) {
      if (!allReqIds.has(rid)) {
        findings.push(
          error(4, `File index '${entry.file}'`, `Requirement '${rid}' not defined in Node 3`, "L2-file-index-req")
        );
      }
    }
  }

  // L3: every requirement should appear in file index
  const indexedReqs = new Set(n4.fileIndex.flatMap((e) => e.requirements));
  for (const rid of allReqIds) {
    if (!indexedReqs.has(rid)) {
      findings.push(
        warn(4, `Requirement ${rid}`, "Not assigned to any file in File Index", "L3-req-in-file-index")
      );
    }
  }

  // L3: metrics consistency
  const expected = {
    totalGoals: collectGoalIds(n3.goalTree).size,
    totalAggregates: n2.aggregates.length,
    totalEvents: n1.events.length,
    totalGaps: n2.aggregates.reduce((sum, a) => sum + a.gaps.length, 0),
    confirmedObstacles: n3.confirmedObstacles.length,
    newObstacles: n3.newObstacles.length,
    totalRequirements: n3.requirements.length,
    must: n3.requirements.filter((r) => r.priority === "MUST").length,
    should: n3.requirements.filter((r) => r.priority === "SHOULD").length,
    could: n3.requirements.filter((r) => r.priority === "COULD").length,
    phases: n3.roadmap.length,
    filesIndexed: n4.fileIndex.length,
  };
  for (const [key, actual] of Object.entries(expected)) {
    const declared = n4.metrics[key as keyof typeof n4.metrics];
    if (declared !== actual) {
      findings.push(
        warn(4, "Metrics", `'${key}' declared ${declared}, actual ${actual}`, "L3-metrics-consistency")
      );
    }
  }

  return findings;
}

// ── Full Pipeline Validation ────────────────────────────────────────────────

export interface PipelineData {
  node0: Node0Output;
  node1: Node1Output;
  node2: Node2Output;
  node3: Node3Output;
  node4: Node4Output;
}

export interface ValidationResult {
  valid: boolean;
  errors: number;
  warnings: number;
  infos: number;
  findings: Finding[];
}

/**
 * Run all constraint checks across the full pipeline.
 * Can also run partial: pass only the nodes you have.
 */
export function validatePipeline(data: Partial<PipelineData>): ValidationResult {
  const findings: Finding[] = [];

  if (data.node0) {
    findings.push(...validateNode0(data.node0));
  }
  if (data.node1 && data.node0) {
    findings.push(...validateNode1(data.node1, data.node0));
  }
  if (data.node2 && data.node1) {
    findings.push(...validateNode2(data.node2, data.node1));
  }
  if (data.node3 && data.node2) {
    findings.push(...validateNode3(data.node3, data.node2));
  }
  if (data.node4 && data.node3 && data.node2 && data.node1) {
    findings.push(...validateNode4(data.node4, data.node3, data.node2, data.node1));
  }

  const errors = findings.filter((f) => f.level === "ERROR").length;
  const warnings = findings.filter((f) => f.level === "WARN").length;
  const infos = findings.filter((f) => f.level === "INFO").length;

  return {
    valid: errors === 0,
    errors,
    warnings,
    infos,
    findings,
  };
}
