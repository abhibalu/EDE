# Constraint Rules Reference

Every validation rule in the pipeline, grouped by layer and node.

## Layer 1 — Schema (Zod parse)

Structural validity. Checked by `NodeNOutput.parse()`. Failures throw `ZodError`.

| Rule | Node | What it checks |
|------|------|---------------|
| ID format | All | EventID, GapID, GoalID, ObstacleID, ReqID match their regex patterns |
| AggCode format | All | 2-4 uppercase letters |
| CodeRef structure | 1,2 | `{ file, anchor }` — both non-empty strings |
| Event name format | 1 | PascalCase: `/^[A-Z][a-zA-Z0-9]+$/` |
| Evidence minimum | 1,2 | ≥10 characters (ReAct grounding contract) |
| Severity enum | 2,3 | `CRITICAL \| HIGH \| MED \| LOW` — closed set |
| Priority enum | 3 | `MUST \| SHOULD \| COULD` — closed set |
| StateType enum | 2 | `atomic \| compound \| parallel \| final` |
| GoalNode recursion | 3 | Valid tree structure with typed fields at every level |
| Catalogue cap | 1 | ≤50 events |
| New obstacle prefix | 3 | IDs starting with `O-N` required for new obstacles |
| Requirement resolves | 3 | `resolves` array must have ≥1 entry |
| Pipeline version | All | Literal `"0.1.0"` — versioned schema |

## Layer 2 — Referential Integrity

Cross-reference checks. Checked by `validateNodeN()`. Failures produce `ERROR` findings.

| Rule ID | Node | What it checks |
|---------|------|---------------|
| L2-unique-area-codes | 0 | No duplicate area codes in registry |
| L2-dispatch-matches-registry | 0 | Dispatch plan area codes exist in registry |
| L2-event-area-code | 1 | Event ID prefix matches a registry area code |
| L2-predecessor-resolves | 1 | Every predecessor ID exists in the event catalogue |
| L2-successor-resolves | 1 | Every successor ID exists in the event catalogue |
| L2-unique-event-ids | 1 | No duplicate event IDs |
| L2-unique-agg-codes | 2 | No duplicate aggregate codes |
| L2-transition-event-resolves | 2 | Transition event IDs exist in Node 1 catalogue |
| L2-gap-prefix | 2 | Gap ID prefix matches its owning aggregate code |
| L2-state-exists | 2 | Transition source/target are declared states |
| L2-unique-states | 2 | No duplicate state names within an aggregate |
| L2-cross-agg-event | 2 | Cross-aggregate transition events exist in catalogue |
| L2-cross-agg-code | 2 | Cross-aggregate transition aggregates are defined |
| L2-obstacle-gap-source | 3 | Confirmed obstacle's gap source exists in Node 2 |
| L2-obstacle-goal-ref | 3 | Obstacle's violatesGoals exist in goal tree |
| L2-req-resolves | 3 | Requirement's resolves reference defined obstacles |
| L2-phase-req-exists | 3 | Phase requirements are defined in Node 3 |
| L2-unique-obstacle-ids | 3 | No duplicate obstacle IDs |
| L2-unique-req-ids | 3 | No duplicate requirement IDs |
| L2-file-index-req | 4 | File index requirement IDs exist in Node 3 |

## Layer 3 — Semantic Invariants

Domain-level correctness. Checked by `validateNodeN()`. Produce `WARN` findings.

| Rule ID | Node | What it checks |
|---------|------|---------------|
| L3-schema-completeness | 0 | If database ≠ "none", schema entities should exist |
| L3-no-self-reference | 1 | Event cannot list itself as predecessor/successor |
| L3-link-symmetry | 1 | If A→B successor, B should list A as predecessor |
| L3-minimum-events | 1 | Fewer than 5 events suggests incomplete extraction |
| L3-no-dead-ends | 2 | Non-final states should have outgoing transitions |
| L3-gap-counts-match | 2 | Gap summary counts match actual gap counts |
| L3-critical-needs-must | 3 | CRITICAL obstacles should have ≥1 MUST requirement |
| L3-req-in-roadmap | 3 | Every requirement should appear in a roadmap phase |
| L3-root-is-G0 | 3 | Goal tree root must be G0 |
| L3-metrics-match | 3 | Declared metrics match computed counts |
| L3-req-in-file-index | 4 | Every requirement should appear in file index |
| L3-metrics-consistency | 4 | Node 4 metrics match actual counts from prior nodes |

## Traceability Chain

Every artifact traces back to code through this chain:

```
CodeRef (file:anchor)
  ↑ evidenced by
DomainEvent (E-XX-NN)
  ↑ transitions mapped in
Aggregate/Gap (XX-GN)
  ↑ obstacle mapped to
Obstacle (O-XX-N / O-NN)
  ↑ violates
Goal (GN.N)
  ↑ resolved by
Requirement (R-XX-NN)
  ↑ scheduled in
Phase (roadmap)
  ↑ indexed against
File Index (file → requirements)
```

Every link in this chain is validated by a Layer 2 rule.

## Registry Propagation

```
Node 0: Seeds registry with area codes from directory scan
         ↓ (areas carry forward)
Node 1: Uses area codes as event ID prefixes (E-{code}-NN)
         ↓
Node 2: Confirms/refines as aggregate codes; gap IDs use same prefix
         ↓
Node 3: Obstacle and requirement IDs inherit aggregate codes
         ↓
Node 4: Validates all IDs against the registry — no hardcoded knowledge
```

The registry makes the entire grammar project-agnostic.
