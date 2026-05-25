# Node 2 — Aggregate & Statechart Extraction

## Purpose
Cluster the domain events from Node 1 into aggregates, extract the implicit state machine hiding in each aggregate's code, and perform gap analysis. The output feeds Node 3 (goal tree & obstacles).

## Input
Read the Node 1 output JSON from `docs/pipeline/runs/{RUN_DATE}/01-events.json`.

## Key Concepts

**Aggregate**: A cluster of domain events sharing a single root entity with a lifecycle. The root entity owns the state; commands are validated against that state.

**Harel Statechart**: Extends flat state machines with hierarchy (nested states), parallel regions (concurrent concerns), guards (conditional transitions), and history states (resume after interruption).

## Output Schema

```typescript
interface Node2Output {
  pipelineVersion: "0.1.0";
  node: 2;
  generatedAt: string;
  registry: Registry;            // carried forward — area codes now confirmed as aggregate codes

  aggregates: Aggregate[];
  crossAggTransitions: {
    fromEvent: string;           // EventID
    fromAggregate: string;       // AggCode
    toEvent: string;             // EventID
    toAggregate: string;         // AggCode
    mechanism: string;           // how these connect (API call, shared DB, event bus)
  }[];
  impossibleCombinations: {
    combination: string;
    risk: string;
    source: string;
  }[];
  migrationPriority: {
    rank: number;
    aggregate: string;           // AggCode
    rationale: string;
  }[];
  gapSummary: {
    critical: number;
    high: number;
    med: number;
    low: number;
    total: number;               // must equal sum of above
  };
}

interface Aggregate {
  code: string;                  // AggCode from registry, e.g. "MS"
  name: string;
  rootEntity: string;            // the entity that owns the state
  keyFiles: CodeRef[];
  states: StateEntry[];          // min 1
  transitions: Transition[];
  gaps: Gap[];
  trivialLifecycle: boolean;     // true if ≤2 states
}

interface StateEntry {
  name: string;                  // domain language, e.g. "Pending", "Generated"
  type: "atomic" | "compound" | "parallel" | "final";
  representation: string;       // how it appears in code (enum value, boolean combo, etc.)
  location: CodeRef;
  evidence: string;              // REQUIRED — code that proves this state exists
}

interface Transition {
  source: string;                // state name (must exist in states[])
  target: string;                // state name (must exist in states[])
  event: string;                 // EventID from Node 1 catalogue
  guard: string | null;          // condition, or null if unconditional
  sideEffects: string[];         // API calls, notifications, etc.
  annotation: "DISCOVERED" | "PROPOSED" | null;
  // DISCOVERED = found in code but not in event catalogue
  // PROPOSED = needed by gap analysis but not in code
}

interface Gap {
  id: string;                    // format: {AggCode}-G{seq} e.g. "MS-G1"
  severity: "CRITICAL" | "HIGH" | "MED" | "LOW";
  description: string;
  codeLocation: CodeRef;
}

interface CodeRef {
  file: string;
  anchor: string;
}
```

## Execution Strategy — Sub-Agents

### Step 1: Validate aggregates (you do this yourself)
Read the event catalogue. For each event group:
- Confirm whether the group is a true aggregate (shared root entity with lifecycle)
- Split groups containing multiple independent lifecycles
- Merge groups that are one lifecycle split across areas
- Name each aggregate and confirm its area code matches the registry

### Step 2: Dispatch sub-agents (one per aggregate)
Each sub-agent gets the relevant events and follows the sub-agent prompt below.

### Step 3: Output Fragments
Each sub-agent writes its aggregate fragment to `docs/pipeline/runs/{RUN_DATE}/fragments/node2/{AGG_CODE}.json`.

Do NOT assign final gap IDs (e.g., MS-G1) yourself. Use provisional sequential
numbers (seq: 1, seq: 2) in your fragments.

Run the assembler:
```
ede assemble --fragments-dir docs/pipeline/runs/{RUN_DATE}/fragments/node2/ --node 2 --registry-file docs/pipeline/runs/{RUN_DATE}/00-recon.json --node1-file docs/pipeline/runs/{RUN_DATE}/01-events.json --output docs/pipeline/runs/{RUN_DATE}/02-statecharts.json
```

The assembler handles:
- Prefixing gap IDs with aggregate code ({AggCode}-G{seq})
- Resolving transition event names to EventIDs from Node 1
- Computing gap summary counts

After assembly, you still need to add these yourself (they require analytical reasoning):
- crossAggTransitions: how aggregates connect
- impossibleCombinations: which state combos can't coexist
- migrationPriority: which aggregates to migrate first

Then validate with --node0 --node1 --node2.

---

## Sub-Agent Prompt

```
You are extracting the implicit state machine for one aggregate.

AGGREGATE: [AGGREGATE_NAME]
AGGREGATE CODE: [AGG_CODE]
ROOT ENTITY: [ROOT_ENTITY]
RELEVANT EVENTS (summary — query 01-events.json for full details):
| ID | Name | Trigger | File |
|----|------|---------|------|
[paste one row per event belonging to this aggregate, e.g.]
| E-MS-01 | SessionGenerated | User requests new session | src/session/create.ts |
| E-MS-02 | AudioMixed | Background mixing completes | src/audio/mixer.ts |

For full event details (evidence, predecessors, successors, stateChange),
use: READ_FILE docs/pipeline/runs/{RUN_DATE}/01-events.json
and locate the event by ID.

Your job has two phases with different protocols.

## PHASE A — State Discovery (ReAct Protocol)

States are factual claims about code. You must ground each one.

THOUGHT: I need to find all possible states of [ROOT_ENTITY] in the codebase.
ACTION: READ_FILE [filepath from event locations]
OBSERVATION: [file contents]
THOUGHT: I see these state representations:
  - Line [X]: [what I see — enum, status string, boolean pattern]

For each state found, record:
- name: domain language (e.g. "Pending", not "PENDING" or "isPending")
- type: atomic (simple), compound (has substates), parallel (concurrent), final (terminal)
- representation: exactly how it appears in code
- location: { file, anchor }
- evidence: the actual code line(s) you observed

Look for:
- Status fields, enums, or string literals
- Boolean flag combinations that encode implicit states
- Nullable fields whose null/non-null pattern represents state
- Component-level state variables tracking lifecycle position
- Database columns that track status

## PHASE B — Statechart Construction (Analytical)

This phase reasons over the events and states you've already grounded. No additional code reading required.

1. MAP TRANSITIONS
For each event in the catalogue, determine:
- source: what state must the entity be in? (must match a state from Phase A)
- target: what state after the event? (must match a state from Phase A)
- guard: what else must be true? (null if unconditional)
- sideEffects: what else happens? (API calls, notifications)
- annotation: null if this maps cleanly to a catalogue event

2. FIND GAPS
After mapping all transitions, check for:
- Dead-end states: no outgoing transition (except final states)
- Unreachable states: no incoming transition (except initial states)
- Missing error states: transitions that can fail but have no failure target
- Missing transitions: events unhandled in certain states
- Implicit states: boolean combos allowing impossible combinations
- Missing timeout/expiry: long-running states with no escape
- No recovery path: error states with no way back

For each gap, assign:
- id: {AGG_CODE}-G{sequential number}
- severity: CRITICAL (data loss/corruption), HIGH (broken user flow),
            MED (degraded experience), LOW (edge case)

## Large Area Protocol

If this aggregate has >10 states after PHASE A (State Discovery):
1. Split your Phase A work into logical groups for manageability.
2. Write temporary working notes per group.
3. In Phase B and PRODUCE OUTPUT, merge ALL groups into a SINGLE Node2Fragment.
   The assembler expects one fragment per aggregate code.

Unlike Node 1 (where multiple fragments per area merge naturally),
Node 2 requires exactly one fragment per aggregate code.

3. PRODUCE OUTPUT
Return JSON conforming to the Node2Fragment schema. Note: use event NAMES
(not EventIDs) for transitions, and provisional sequential numbers (seq: 1, 2, ...)
for gaps. The assembler resolves names to IDs and prefixes gap IDs.

After writing your fragment JSON, validate it:
  ede validate-fragment --node 2 --fragment docs/pipeline/runs/{RUN_DATE}/fragments/node2/{AGG_CODE}.json
If validation fails, read the error output, fix your JSON, and re-validate.
The validator checks both schema (L1) and transition source/target references (L2).

{
  "aggCode": "[AGG_CODE]",
  "aggName": "[AGGREGATE_NAME]",
  "rootEntity": "[ROOT_ENTITY]",
  "keyFiles": [{"file": "...", "anchor": "..."}],
  "states": [{"name": "...", "type": "atomic", "representation": "...", "location": {...}, "evidence": "..."}],
  "transitions": [{"source": "...", "target": "...", "eventName": "EventName", "guard": null, "sideEffects": [], "annotation": null}],
  "gaps": [{"seq": 1, "severity": "HIGH", "description": "...", "codeLocation": {...}}],
  "trivialLifecycle": false
}

Run `ede schema --fragment node2` to regenerate this if the schema changes.

### Fragment Schema

```json
{
  "$defs": {
    "CodeRef": {
      "properties": {
        "file": { "minLength": 1, "type": "string" },
        "anchor": { "minLength": 1, "type": "string" }
      },
      "required": ["file", "anchor"],
      "type": "object"
    },
    "GapFragment": {
      "properties": {
        "seq": { "minimum": 1, "type": "integer" },
        "severity": { "enum": ["CRITICAL", "HIGH", "MED", "LOW"], "type": "string" },
        "description": { "minLength": 1, "type": "string" },
        "codeLocation": { "$ref": "#/$defs/CodeRef" }
      },
      "required": ["seq", "severity", "description", "codeLocation"],
      "type": "object"
    },
    "StateFragment": {
      "properties": {
        "name": { "minLength": 1, "type": "string" },
        "type": { "enum": ["atomic", "compound", "parallel", "final"], "type": "string" },
        "representation": { "minLength": 1, "type": "string" },
        "location": { "$ref": "#/$defs/CodeRef" },
        "evidence": { "minLength": 10, "type": "string" }
      },
      "required": ["name", "type", "representation", "location", "evidence"],
      "type": "object"
    },
    "TransitionFragment": {
      "properties": {
        "source": { "minLength": 1, "type": "string" },
        "target": { "minLength": 1, "type": "string" },
        "eventName": { "minLength": 1, "type": "string" },
        "guard": { "anyOf": [{ "type": "string" }, { "type": "null" }] },
        "sideEffects": { "items": { "type": "string" }, "type": "array" },
        "annotation": { "anyOf": [{ "enum": ["DISCOVERED", "PROPOSED"] }, { "type": "null" }] }
      },
      "required": ["source", "target", "eventName", "guard", "sideEffects", "annotation"],
      "type": "object"
    }
  },
  "properties": {
    "aggCode": { "pattern": "^[A-Z]{2,4}$", "type": "string" },
    "aggName": { "minLength": 1, "type": "string" },
    "rootEntity": { "minLength": 1, "type": "string" },
    "keyFiles": { "items": { "$ref": "#/$defs/CodeRef" }, "minItems": 1, "type": "array" },
    "states": { "items": { "$ref": "#/$defs/StateFragment" }, "minItems": 1, "type": "array" },
    "transitions": { "items": { "$ref": "#/$defs/TransitionFragment" }, "type": "array" },
    "gaps": { "items": { "$ref": "#/$defs/GapFragment" }, "type": "array" },
    "trivialLifecycle": { "type": "boolean" }
  },
  "required": ["aggCode", "aggName", "rootEntity", "keyFiles", "states", "transitions", "gaps", "trivialLifecycle"],
  "type": "object"
}
```

### Common Schema Mistakes

Your output MUST parse against the fragment schema. These mistakes will cause assembly to fail:

- `annotation` must be exactly `"DISCOVERED"`, `"PROPOSED"`, or `null` -- NOT a free-text description like `"found in code but not in catalogue"`
- `severity` must be exactly `"CRITICAL"`, `"HIGH"`, `"MED"`, or `"LOW"` -- NOT `"Medium"` or `"medium"`
- `type` (state type) must be exactly `"atomic"`, `"compound"`, `"parallel"`, or `"final"` -- NOT `"simple"` or `"terminal"`
- `eventName` is an event NAME string (e.g. `"UserActivated"`), not an EventID (not `"E-US-02"`)
- `guard` and `annotation` must be `null` (not omitted) when not applicable
- `evidence` must be at least 10 characters of actual code observed
- `codeLocation` and `location` must be objects `{"file": "...", "anchor": "..."}` -- NOT strings
- `seq` for gaps is a plain integer (1, 2, 3), NOT a string and NOT a prefixed ID

CONSTRAINTS:
- Every state must trace to actual code with evidence.
- Every transition source and target must match a declared state name.
- Use event NAMES in transitions (the assembler maps them to EventIDs from Node 1).
- Use provisional sequential numbers for gaps (the assembler prefixes with AggCode).
- Do NOT invent states not evidenced in code (unless gap analysis requires a PROPOSED state).
- Do NOT suggest fixes. Read-only analysis.
```

---

## Constraints
- Every state must trace to actual code with evidence.
- Every gap must reference a specific file via codeLocation.
- Transition source/target must be names declared in the states array.
- Transition events must be EventIDs from Node 1.
- Gap IDs must use the aggregate's code as prefix.
- gapSummary counts must match actual gap counts. The validator will check this.
- Do NOT suggest fixes or refactoring. Read-only analysis.
- If an aggregate has ≤2 states, set trivialLifecycle to true.
- Output ONLY the final JSON object. No markdown. No explanation.
