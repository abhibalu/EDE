/**
 * Assemblers — Deterministic Fragment → Node Output
 *
 * These functions take validated fragments (from sub-agents) and produce
 * the final node output. All mechanical operations that LLMs do poorly:
 * - ID assignment (sequential, prefixed)
 * - Deduplication (by name + location)
 * - Name → ID resolution (predecessors/successors)
 * - Count computation (metrics, summaries)
 *
 * Every assembler returns { output, findings } where findings captures
 * any issues encountered during assembly (unresolved links, duplicates, etc).
 */

import { z } from "zod";
import { Node1Fragment, EventFragment, Node2Fragment } from "./fragments.js";
import { Node1Output } from "./nodes/node1.js";
import { Node2Output } from "./nodes/node2.js";
import { Registry, HotSpot } from "./primitives.js";

// ── Inferred types ──────────────────────────────────────────────────────────

type N1Frag = z.infer<typeof Node1Fragment>;
type EvFrag = z.infer<typeof EventFragment>;
type N2Frag = z.infer<typeof Node2Fragment>;
type N1Out = z.infer<typeof Node1Output>;
type N2Out = z.infer<typeof Node2Output>;
type Reg = z.infer<typeof Registry>;
type HS = z.infer<typeof HotSpot>;

// ── Finding (local to avoid circular imports) ───────────────────────────────

interface Finding {
  level: "ERROR" | "WARN" | "INFO";
  node: number;
  where: string;
  message: string;
  rule?: string;
}

function info(node: number, where: string, message: string, rule?: string): Finding {
  return { level: "INFO", node, where, message, rule };
}
function warn(node: number, where: string, message: string, rule?: string): Finding {
  return { level: "WARN", node, where, message, rule };
}

// ── Node 1 Assembler ────────────────────────────────────────────────────────

export interface AssembleNode1Input {
  registry: Reg;
  fragments: N1Frag[];
  generatedAt?: string;
}

export interface AssembleResult<T> {
  output: T;
  findings: Finding[];
}

export function assembleNode1(input: AssembleNode1Input): AssembleResult<N1Out> {
  const findings: Finding[] = [];
  const { registry, fragments } = input;
  const generatedAt = input.generatedAt ?? new Date().toISOString();

  // ── Step 1: Deduplicate ──
  const seen = new Map<string, { areaCode: string; event: EvFrag }>();
  const dedupedByArea = new Map<string, EvFrag[]>();

  for (const fragment of fragments) {
    if (!dedupedByArea.has(fragment.areaCode)) {
      dedupedByArea.set(fragment.areaCode, []);
    }
    for (const event of fragment.events) {
      const key = `${event.name}::${event.location.file}`;
      if (seen.has(key)) {
        const original = seen.get(key)!;
        findings.push(info(1, `Event ${event.name}`, `Duplicate in '${fragment.areaCode}', already in '${original.areaCode}'`, "ASSEMBLE-dedup"));
        continue;
      }
      seen.set(key, { areaCode: fragment.areaCode, event });
      dedupedByArea.get(fragment.areaCode)!.push(event);
    }
  }

  // ── Step 2: Assign IDs ──
  const nameToId = new Map<string, string>();
  for (const [areaCode, events] of dedupedByArea) {
    events.forEach((event, idx) => {
      nameToId.set(event.name, `E-${areaCode}-${String(idx + 1).padStart(2, "0")}`);
    });
  }

  // ── Step 3: Resolve names → IDs, build final events ──
  type FinalEvent = N1Out["events"][number];
  const allEvents: FinalEvent[] = [];

  for (const [areaCode, events] of dedupedByArea) {
    events.forEach((event, idx) => {
      const id = `E-${areaCode}-${String(idx + 1).padStart(2, "0")}`;

      const predecessors: string[] = [];
      for (const name of event.predecessorNames) {
        const resolved = nameToId.get(name);
        if (resolved) predecessors.push(resolved);
        else findings.push(warn(1, `Event ${event.name} (${id})`, `Predecessor '${name}' not found`, "ASSEMBLE-unresolved-predecessor"));
      }

      const successors: string[] = [];
      for (const name of event.successorNames) {
        const resolved = nameToId.get(name);
        if (resolved) successors.push(resolved);
        else findings.push(warn(1, `Event ${event.name} (${id})`, `Successor '${name}' not found`, "ASSEMBLE-unresolved-successor"));
      }

      allEvents.push({
        id, name: event.name, trigger: event.trigger, location: event.location,
        predecessors, successors, stateChange: event.stateChange,
        evidence: event.evidence, hotSpots: event.hotSpots,
      });
    });
  }

  // ── Step 4: Enforce symmetry ──
  const eventById = new Map(allEvents.map((e) => [e.id, e]));
  for (const event of allEvents) {
    for (const succId of event.successors) {
      const succ = eventById.get(succId);
      if (succ && !succ.predecessors.includes(event.id)) {
        succ.predecessors.push(event.id);
        findings.push(info(1, `Event ${succ.name} (${succ.id})`, `Auto-added predecessor '${event.id}' for symmetry`, "ASSEMBLE-symmetry-fix"));
      }
    }
    for (const predId of event.predecessors) {
      const pred = eventById.get(predId);
      if (pred && !pred.successors.includes(event.id)) {
        pred.successors.push(event.id);
        findings.push(info(1, `Event ${pred.name} (${pred.id})`, `Auto-added successor '${event.id}' for symmetry`, "ASSEMBLE-symmetry-fix"));
      }
    }
  }

  // ── Step 5: Build metadata ──
  const scanAreas = fragments.map((f) => ({
    name: f.areaName, areaCode: f.areaCode,
    directories: registry.areas.find((a) => a.code === f.areaCode)?.directories ?? [],
    filesScanned: f.filesScanned, filesSkipped: f.filesSkipped,
  }));

  const hotSpotSummary: HS[] = allEvents.flatMap((e) => e.hotSpots);
  const truncation = allEvents.length > 50
    ? { estimatedTotal: allEvents.length, areasAffected: [...dedupedByArea.keys()] }
    : null;

  const output: N1Out = {
    pipelineVersion: "0.1.0", node: 1, generatedAt, registry,
    metadata: { totalFilesScanned: fragments.reduce((s, f) => s + f.filesScanned.length, 0), scanAreas },
    events: allEvents.slice(0, 50), hotSpotSummary, truncation,
  };

  return { output, findings };
}

// ── Node 2 Assembler ────────────────────────────────────────────────────────

export interface AssembleNode2Input {
  registry: Reg;
  fragments: N2Frag[];
  node1: N1Out;
  generatedAt?: string;
}

export function assembleNode2(input: AssembleNode2Input): AssembleResult<N2Out> {
  const findings: Finding[] = [];
  const { registry, fragments, node1 } = input;
  const generatedAt = input.generatedAt ?? new Date().toISOString();

  const eventNameToId = new Map(node1.events.map((e) => [e.name, e.id]));

  const aggregates = fragments.map((frag) => {
    const transitions = frag.transitions.map((t) => {
      const eventId = eventNameToId.get(t.eventName);
      if (!eventId) findings.push(warn(2, `${frag.aggCode} ${t.source}→${t.target}`, `Event '${t.eventName}' not in catalogue`, "ASSEMBLE-unresolved-event"));
      return {
        source: t.source, target: t.target, event: eventId ?? `UNRESOLVED:${t.eventName}`,
        guard: t.guard, sideEffects: t.sideEffects, annotation: t.annotation,
      };
    });

    const gaps = frag.gaps.map((g) => ({
      id: `${frag.aggCode}-G${g.seq}`, severity: g.severity,
      description: g.description, codeLocation: g.codeLocation,
    }));

    return {
      code: frag.aggCode, name: frag.aggName, rootEntity: frag.rootEntity,
      keyFiles: frag.keyFiles,
      states: frag.states.map((s) => ({ name: s.name, type: s.type, representation: s.representation, location: s.location, evidence: s.evidence })),
      transitions, gaps, trivialLifecycle: frag.trivialLifecycle,
    };
  });

  const gapSummary = { critical: 0, high: 0, med: 0, low: 0, total: 0 };
  for (const agg of aggregates) {
    for (const gap of agg.gaps) {
      gapSummary[gap.severity.toLowerCase() as "critical" | "high" | "med" | "low"]++;
      gapSummary.total++;
    }
  }

  const output: N2Out = {
    pipelineVersion: "0.1.0", node: 2, generatedAt, registry, aggregates,
    crossAggTransitions: [], impossibleCombinations: [], migrationPriority: [], gapSummary,
  };

  return { output, findings };
}
