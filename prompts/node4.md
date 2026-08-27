# Node 4 — Spec Assembly

## Purpose
Compile all pipeline outputs into two artifacts:
1. A **JSON compilation** (Node 4 output) that adds the file index, changelog, and computed metrics
2. A **rendered markdown spec** for human consumption

## Inputs
Read ALL previous pipeline outputs:
- `docs/pipeline/runs/{RUN_DATE}/00-recon.json`
- `docs/pipeline/runs/{RUN_DATE}/01-events.json`
- `docs/pipeline/runs/{RUN_DATE}/02-statecharts.json`
- `docs/pipeline/runs/{RUN_DATE}/03-goals.json`

## Assembly Rules

You are NOT generating new analysis. You are compiling and cross-referencing. Follow these rules:

1. Do NOT invent new gaps, obstacles, or requirements.
2. Do NOT change severity or priority ratings.
3. Do NOT omit anything. Every gap, obstacle, and requirement must appear.
4. Cross-reference everything. The file index maps source files to requirements.
5. Metrics must match actual counts from prior nodes exactly.

## Step 1: Two-Pass JSON Assembly

### Pass 1 — Programmatic Tracing (write staging file)
Read all prior outputs. For each requirement in Node 3:
1. Find which obstacles it resolves (`resolves` array)
2. For confirmed obstacles: look up `gapSource` → find gap's `codeLocation.file`
3. For new obstacles: look up `evidence` field → extract file path
4. Collect all unique files referenced

Write a compact staging file:
  `docs/pipeline/runs/{RUN_DATE}/staging/node4/pass1-traces.json`
Format:
```json
{
  "traces": [
    {
      "reqId": "R-OR-01",
      "obstacles": ["O-OR-1"],
      "gaps": ["OR-G1"],
      "files": ["src/services/order/index.ts"]
    }
  ],
  "allFiles": ["src/services/order/index.ts", "..."]
}
```

### Pass 2 — Categorization and Metrics
Read the staging file from Pass 1 plus Node 0 (for architecture context).
For each file in `allFiles`:
1. Determine category from directory structure and Node 0 architecture
2. Assign requirement list from the traces

Then compute all metrics by counting actual items from prior node outputs.

Produce the final `Node4Output` JSON.

### Node4Output Schema

```typescript
interface Node4Output {
  pipelineVersion: "0.1.0";
  node: 4;
  generatedAt: string;
  registry: Registry;

  systemPurpose: string;                // one paragraph from Node 0 context

  fileIndex: FileIndexEntry[];
  changelog: { date: string; change: string; }[];  // initialised with baseline
  metrics: {
    totalGoals: number;                 // count from Node 3 goal tree
    totalAggregates: number;            // count from Node 2
    totalEvents: number;                // count from Node 1
    totalGaps: number;                  // count from Node 2 (all aggregates)
    confirmedObstacles: number;         // count from Node 3
    newObstacles: number;               // count from Node 3
    totalRequirements: number;          // count from Node 3
    must: number;
    should: number;
    could: number;
    phases: number;                     // count from Node 3 roadmap
    filesIndexed: number;               // count of fileIndex entries
  };
  sources: {
    node0: string;                      // path to Node 0 output
    node1: string;
    node2: string;
    node3: string;
  };
}

interface FileIndexEntry {
  file: string;
  category: "backend-router" | "backend-service" | "backend-agent"
           | "frontend-hook" | "frontend-component" | "frontend-state"
           | "config" | "schema" | "shared" | "other";
  requirements: string[];              // ReqIDs that touch this file
}
```

### Metrics Validation

Before emitting the JSON, verify every metric matches the actual count from the source node. If any mismatch: recount, do not adjust the source.

## Step 2: Render the Markdown Spec

Using ALL four prior JSON outputs plus the Node 4 JSON you just produced, render a human-readable markdown document.

Write this to: `docs/pipeline/runs/{RUN_DATE}/domain-spec.md` and `docs/pipeline/runs/{RUN_DATE}/domain-spec.md`

### Markdown Structure

```markdown
# [Project Name] — Domain Specification

> **Generated**: [date]
> **Pipeline**: 5-node domain extraction v0.1.0
> **Status**: Baseline

---

## How to Use This Spec

(Three short paragraphs:
1. "If deciding what to build next → Implementation Roadmap"
2. "If implementing a requirement → find R-XX-XX, trace to obstacle, check File Index"
3. "If handing to an AI agent → pass the relevant aggregate section")

## Notation Guide

| Prefix | Meaning | Example | Introduced at |
|--------|---------|---------|---------------|
| E-{XX}-{NN} | Domain event | E-MS-01 | Node 1 |
| {XX}-G{N} | Gap in statechart | MS-G1 | Node 2 |
| O-{XX}-{N} | Confirmed obstacle | O-MS-1 | Node 3 |
| O-N{N} | New obstacle | O-N1 | Node 3 |
| R-{XX}-{NN} | Requirement | R-MS-01 | Node 3 |
| R-XA-{NN} | Cross-aggregate req | R-XA-01 | Node 3 |
| G{N}.{N} | Goal | G1.2 | Node 3 |

## System Purpose

(From Node 0: one paragraph. State G0. Name the aggregates.)

## Goal Tree

(Render the full KAOS tree from Node 3 as indented text with obstacle refs)

## Aggregate Reference

(For EACH aggregate — self-contained section:)

### [AggregateName]

**Root entity:** ...
**Key files:** ...
**Goals served:** ...

#### States
(Table: Name | Type | Representation | Location)

#### Statechart
(Text notation: State -[Event/Guard]→ State, with annotations)

#### Gaps
(Table: ID | Sev | Description | Code Location)

#### Requirements
**MUST:**
(Table: ID | Requirement | Resolves)

**SHOULD:**
(Table: ID | Requirement | Resolves)

**COULD:**
(Table: ID | Requirement | Resolves)

---

## Cross-Aggregate Architecture

### Transition Map
(From Node 2)

### Impossible State Combinations
(From Node 2)

### Cross-Aggregate Requirements
(From Node 3, R-XA-* requirements)

## Obstacle Register

### Summary
(Table: Severity | Count)

### All Obstacles by Severity
(Group by CRITICAL, HIGH, MED, LOW — list each with goal ref and description)

## Requirements Delta

### Summary
(Table: Priority | Count)

## Implementation Roadmap

(Phases from Node 3 with requirement lists)

## File Index

(Table: File | Category | Requirements — grouped by category)

## Metrics

(Summary table from Node 4 metrics)

## Changelog

| Date | Change |
|------|--------|
| [today] | Baseline: initial spec from 5-node pipeline |
```

## Constraints
- The JSON output contains ONLY new artifacts (file index, changelog, metrics, system purpose). It does NOT duplicate events, aggregates, goals, etc.
- The markdown spec renders FROM all five JSON files — it's a view, not a copy.
- Preserve exact IDs from prior nodes. Do not renumber.
- Every metric must match actual counts. The validator will check.
- Output the JSON first, then render the markdown.

After producing 04-spec.json, generate the human-readable markdown:
```
ede render --node0 docs/pipeline/runs/{RUN_DATE}/00-recon.json --node1 docs/pipeline/runs/{RUN_DATE}/01-events.json --node2 docs/pipeline/runs/{RUN_DATE}/02-statecharts.json --node3 docs/pipeline/runs/{RUN_DATE}/03-goals.json --node4 docs/pipeline/runs/{RUN_DATE}/04-spec.json --output docs/pipeline/runs/{RUN_DATE}/domain-spec.md
```
