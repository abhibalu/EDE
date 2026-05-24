# Node 2 — Aggregate & Statechart Extraction

## Purpose
Cluster the domain events from Node 1 into aggregates, extract the implicit state machine hiding in each aggregate's code, and perform gap analysis. The output feeds Node 3 (goal tree & obstacles).

## Input
Read the Node 1 output JSON from `docs/pipeline/output/01-events.json`.

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

### Step 3: Assemble
Collect all sub-agent outputs. Then you:
1. Verify cross-aggregate transitions are consistent
2. Compile the gap analysis with sequential IDs per aggregate
3. Verify gapSummary counts match actual gaps
4. Build the migration priority ranking
5. Verify every StateEntry has a non-empty `evidence` field
6. Produce the final JSON.

---

## Sub-Agent Prompt

```
You are extracting the implicit state machine for one aggregate.

AGGREGATE: [AGGREGATE_NAME]
AGGREGATE CODE: [AGG_CODE]
ROOT ENTITY: [ROOT_ENTITY]
RELEVANT EVENTS:
[paste the events from Node 1 that belong to this aggregate, as JSON]

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

3. PRODUCE OUTPUT
Return JSON conforming to the Aggregate interface above.

CONSTRAINTS:
- Every state must trace to actual code with evidence.
- Every transition source and target must match a declared state name.
- Every transition event must match an EventID from the input catalogue.
- Gap IDs use the aggregate code as prefix: {AGG_CODE}-G1, {AGG_CODE}-G2, etc.
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
