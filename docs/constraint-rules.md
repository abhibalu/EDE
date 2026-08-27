# Constraint Rules Reference

Every validation rule in the pipeline, grouped by layer and node.

## Layer 1 -- Schema (Pydantic model_validate)

Structural validity. Checked by `NodeNOutput.model_validate()`. Failures raise `ValidationError`.

| Rule | Node | What it checks |
|------|------|---------------|
| ID format | All | EventID, GapID, GoalID, ObstacleID, ReqID match their regex patterns |
| AggCode format | All | 2-4 uppercase letters |
| CodeRef structure | 1,2 | `{ file, anchor }` -- both non-empty strings |
| Event name format | 1 | PascalCase: `/^[A-Z][a-zA-Z0-9]+$/` |
| Evidence minimum | 1,2 | >=10 characters (ReAct grounding contract) |
| Severity enum | 2,3 | `CRITICAL | HIGH | MED | LOW` -- closed set |
| Priority enum | 3 | `MUST | SHOULD | COULD` -- closed set |
| StateType enum | 2 | `atomic | compound | parallel | final` |
| GoalNode recursion | 3 | Valid tree structure with typed fields at every level |
| Per-area cap | 1 | <=15 events per area (enforced by assembler, not Pydantic) |
| New obstacle prefix | 3 | IDs starting with `O-N` required for new obstacles (**promoted from L3**) |
| Requirement resolves | 3 | `resolves` array must have >=1 entry |
| Pipeline version | All | Literal `"0.1.0"` -- versioned schema |
| Gap summary total | 2 | `total == critical + high + med + low` (**promoted from L3**) |
| Metrics req count | 3 | `total_requirements == must + should + could` (**promoted from L3**) |

## Layer 2 -- Referential Integrity

Cross-reference checks. Checked by `validate_node_n()`. Failures produce `ERROR` findings.

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

## Layer 3 -- Semantic Invariants

Domain-level correctness. Checked by `validate_node_n()`. Produce `WARN` findings.

| Rule ID | Node | What it checks |
|---------|------|---------------|
| L3-schema-completeness | 0 | If database != "none", schema entities should exist |
| L3-no-self-reference | 1 | Event cannot list itself as predecessor/successor |
| L3-link-symmetry | 1 | If A->B successor, B should list A as predecessor |
| L3-minimum-events | 1 | Fewer than 5 events suggests incomplete extraction |
| L3-no-dead-ends | 2 | Non-final states should have outgoing transitions |
| L3-critical-needs-must | 3 | CRITICAL obstacles should have >=1 MUST requirement |
| L3-req-in-roadmap | 3 | Every requirement should appear in a roadmap phase |
| L3-root-is-G0 | 3 | Goal tree root must be G0 |
| L3-metrics-match | 3 | Declared metrics (totalGoals, leafGoals, etc.) match computed |
| L3-req-in-file-index | 4 | Every requirement should appear in file index |
| L3-metrics-consistency | 4 | Node 4 metrics match actual counts from prior nodes |

**Promoted to L1:** L3-gap-counts-match (now `GapSummary` model_validator), L3-metrics-match for total_requirements (now `Node3Metrics` model_validator), New obstacle O-N prefix (now `NewObstacle` model_validator).

## Layer 4 -- Path Verification

Claims versus disk. Checked by `verify_*_paths()` in `ede/verifiers/paths.py`.
Produce `WARN` findings. Run with `ede verify-paths --repo <target>`.

L1 through L3 all ask the same kind of question: is this document
self-consistent? They can all pass on an artifact whose every file reference
was invented, because nothing in the JSON contradicts anything else in the
JSON. L4 is the only layer that consults something outside the document.

| Rule ID | Node | What it checks |
|---------|------|---------------|
| L4-path-missing | 0,1,2,4 | A path-typed field does not resolve against the target repository |
| L4-path-wrong-kind | 0,1,2,4 | The path resolves but is a file where a directory was expected, or the reverse |

Two rules, but they probe every path-typed field in the pipeline:

| Verifier | Node | Fields probed |
|----------|------|--------------|
| `verify_recon_paths` | 0 | registry area directories, architecture frontend/backend/shared dirs, persistence schemaLocation, external service configLocation, dispatch plan directories, keyFiles |
| `verify_events_paths` | 1 | scan area directories, filesScanned, filesSkipped, event location, event hotSpot locations, hotSpotSummary locations |
| `verify_aggregates_paths` | 2 | aggregate keyFiles, state locations, transition codeLocation, gap codeLocation |
| `verify_spec_paths` | 4 | fileIndex entries |
| `verify_fragment_paths` | 1,2,3 | the same fields at the sub-agent boundary, before assembly folds them into node output |

Node 3 has no path-typed fields, so it has no verifier. That is a property of
the schema, not an omission.

Findings are `WARN` and the command always exits 0. A missing path is strong
evidence a claim was hallucinated or has gone stale, but a legitimately moved
or renamed file should not halt a pipeline run. The fragment-level verifier
matters most: it catches an invented path while it can still be traced to the
sub-agent that produced it.

L4 sits outside the formal-language framing that governs L1 through L3 --
it queries an oracle rather than inspecting a string. See
[`formal-theory.md`](formal-theory.md) for why that distinction is principled
rather than incidental.

## Traceability Chain

```
CodeRef (file:anchor)
  ^ evidenced by
DomainEvent (E-XX-NN)
  ^ transitions mapped in
Aggregate/Gap (XX-GN)
  ^ obstacle mapped to
Obstacle (O-XX-N / O-NN)
  ^ violates
Goal (GN.N)
  ^ resolved by
Requirement (R-XX-NN)
  ^ scheduled in
Phase (roadmap)
  ^ indexed against
File Index (file -> requirements)
```

## Registry Propagation

```
Node 0: Seeds registry with area codes from directory scan
         | (areas carry forward)
Node 1: Uses area codes as event ID prefixes (E-{code}-NN)
         |
Node 2: Confirms/refines as aggregate codes; gap IDs use same prefix
         |
Node 3: Obstacle and requirement IDs inherit aggregate codes
         |
Node 4: Validates all IDs against the registry -- no hardcoded knowledge
```
