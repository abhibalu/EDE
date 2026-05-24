# Node 4 — Spec Assembly

## Purpose
Compile all pipeline outputs into a single, authoritative domain specification document. This is the final artifact — the reference document for all future implementation work on this codebase.

## Inputs
Read ALL previous pipeline outputs:
- `docs/pipeline/output/00-recon.md` — codebase structure
- `docs/pipeline/output/01-events.md` — event catalogue
- `docs/pipeline/output/02-statecharts.md` — aggregates, statecharts, gaps
- `docs/pipeline/output/03-goals.md` — goal tree, obstacles, requirements, roadmap

## Assembly Rules

You are NOT generating new analysis. You are compiling and cross-referencing existing artifacts into a single navigable document. Follow these rules:

1. **Do NOT invent new gaps, obstacles, or requirements.** Only include what the prior nodes produced.
2. **Do NOT change severity ratings.** Preserve them exactly.
3. **Do NOT omit anything.** Every gap, obstacle, and requirement from every node must appear in the final spec.
4. **Cross-reference everything.** Every requirement traces to an obstacle, every obstacle to a goal, every gap to a code location.
5. **Add the notation guide.** Include the ID system legend so any reader understands the prefixes.
6. **Add the file index.** Map every referenced source file to the requirements that touch it.
7. **Add the changelog.** Initialize with today's date and "Baseline: initial spec from pipeline."

## Document Structure

Produce the spec in this exact section order:

```markdown
# [Project Name] — Domain Specification

> **Generated**: [today's date]
> **Pipeline**: 5-node brownfield domain extraction
> **Status**: Baseline
> **Maintainer**: Update this spec when implementation closes gaps.

---

## How to Use This Spec

(Three paragraphs:
1. "If deciding what to build next → Implementation Roadmap"
2. "If implementing a requirement → find R-XX-XX, follow obstacle back to statechart, check File Index"
3. "If passing to AI agent → hand it the relevant aggregate section, which is self-contained")

---

## Notation Guide

(Table of all ID prefixes: G, O, O-N, [AGG]-G, R-[AGG], R-XA)
(Traceability chain example: Goal → Obstacle → Gap → Requirement → File)

---

## Table of Contents

(Anchor links to all sections)

---

## System Purpose

(From Node 0 recon: 1 paragraph describing the system, its stack, and deployment)
(State G0 — the top-level goal)
(Name the aggregates)

---

## Goal Tree

(Full KAOS tree from Node 3, WITH obstacle references per leaf goal)

---

## Aggregate Reference

(For EACH aggregate — self-contained section:)

### [AggregateName]

**Root entity:** ...
**Key files:** ...
**Goals served:** ...

#### States
(Table from Node 2)

#### Statechart
(Text notation from Node 2)

#### Gaps
(Table from Node 2)

#### Requirements
(MUST/SHOULD/COULD tables from Node 3, inline with this aggregate)

---

## Cross-Aggregate Architecture

### Transition Map
(From Node 2)

### Boundary Risks
(From Node 2 + Node 3)

### Impossible State Combinations
(From Node 2)

### Cross-Aggregate Requirements
(From Node 3)

---

## Obstacle Register

### Summary by Severity
(Counts table)

### CRITICAL Obstacles
(Full list)

### Most-Violated Goals
(Ranked table)

---

## Requirements Delta

### Summary
(Counts by MUST/SHOULD/COULD)

### Requirements by Aggregate
(Counts table)

---

## Implementation Roadmap

(Phased plan from Node 3, with requirement lists and gap-closure per phase)

---

## File Index

(Every source file referenced in the spec, with which requirements touch it.
Group by: Backend, Frontend Hooks, Frontend Components, Frontend State, Config/Schema)

---

## Metrics

(Summary table: goals, obstacles, requirements, phases, files)

---

## Changelog

| Date | Change |
|------|--------|
| [today] | Baseline: initial spec from 5-node pipeline |
```

## Output

Write the assembled spec to TWO locations:
1. `docs/pipeline/output/domain-spec.md` (pipeline output directory)
2. `docs/domain-spec.md` (project-level location for daily use)

Your first line must be the document title. No preamble.

## Constraints
- The final document should be comprehensive but not padded. Every line earns its place.
- Preserve exact gap IDs, obstacle IDs, and requirement IDs from prior nodes.
- Do NOT re-analyze the codebase. Only compile existing outputs.
- The File Index must be built by scanning all requirement entries for file references — do not guess.
