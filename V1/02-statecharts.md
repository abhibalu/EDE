# Node 2 — Aggregate & Statechart Extraction

## Purpose
Cluster the domain events from Node 1 into aggregates, extract the implicit state machine hiding in each aggregate's code, and perform gap analysis. The output feeds Node 3 (goal tree & obstacles).

## Input
Read the Node 1 event catalogue from `docs/pipeline/output/01-events.md`.

## Key Concepts

**Aggregate**: A cluster of domain events sharing a single root entity with a lifecycle. The root entity owns the state; commands are validated against that state.

**Harel Statechart**: Extends flat state machines with hierarchy (nested states), parallel regions (concurrent concerns), guards (conditional transitions), and history states (resume after interruption).

## Execution Strategy — Use Sub-Agents

### Step 1: Validate aggregates (you do this yourself)
Read the event catalogue. For each event group:
- Confirm whether the group is a true aggregate (shared root entity with lifecycle)
- Split groups containing multiple independent lifecycles
- Merge groups that are one lifecycle split across areas
- Name each aggregate and identify its root entity

### Step 2: Dispatch sub-agents (one per aggregate)
Each sub-agent gets the relevant events from the catalogue, the Sub-Agent Prompt below, and access to the codebase files referenced in event locations.

### Step 3: Assemble
Collect all sub-agent statecharts. Then you:
1. Verify cross-aggregate transitions are consistent
2. Compile the gap analysis
3. Build the cross-aggregate transition map
4. Identify impossible state combinations
5. Rank aggregates by XState migration value

---

## Sub-Agent Prompt

```
You are extracting the implicit state machine for one aggregate from a codebase.

AGGREGATE: [AGGREGATE_NAME]
ROOT ENTITY: [ROOT_ENTITY]
RELEVANT EVENTS:
[paste the events from the catalogue that belong to this aggregate]

Your job:

1. FIND THE CURRENT STATES
Open the code files listed in the event locations. Look for:
- Status fields, enums, or string literals that represent states
- Boolean flag combinations that encode implicit states
- Nullable fields whose null/non-null pattern represents state
- Component-level state variables (useState) that track lifecycle position
- Database columns that track status

For each state found, record:
- The state name (domain language, not variable names)
- Where it's defined: `[filepath:line]`
- How it's represented in code (enum value, boolean combo, nullable field)

2. MAP TRANSITIONS
For each event in the catalogue, identify:
- Source state (what state must the entity be in?)
- Target state (what state after the event?)
- Guard condition (what else must be true?)
- Side effects (API calls, notifications, etc.)

3. FIND GAPS
After mapping all transitions, check for:
- Dead-end states (no outgoing transition)
- Unreachable states (no incoming transition)
- Missing error states (transitions that can fail but have no failure target)
- Missing transitions (events unhandled in certain states)
- Implicit states (boolean combos allowing impossible combinations)
- Missing timeout/expiry (long-running states with no escape)
- No recovery path (error states with no way back)

4. PRODUCE THE STATECHART

Use this format:

### States
| State | Type | Representation in Code | Location |
|-------|------|----------------------|----------|
| [Name] | atomic/compound/parallel/final | [how it appears in code] | [file:line] |

### State Machine
(Text-based statechart notation with transitions, guards, and ⚠ gap markers)

### Gaps
| ID | Sev | Description | Location |
|----|-----|-------------|----------|
| [AGG]-G[N] | CRITICAL/HIGH/MED/LOW | [description] | [file:line] |

Mark discovered transitions not in catalogue: ⚠ DISCOVERED
Mark proposed states/transitions not in code: 💡 PROPOSED

CONSTRAINTS:
- Every state must trace to actual code.
- Every transition must correspond to a catalogue event or a discovered gap.
- Do NOT invent states not evidenced in code or required by gap analysis.
- Do NOT suggest fixes. Read-only analysis.
```

---

## Output Format

Your first line must be `# Aggregate & Statechart Analysis`. No preamble.

```markdown
# Aggregate & Statechart Analysis

## Aggregate Map

| Aggregate | Root Entity | States Found | Gaps Found |
|-----------|-------------|--------------|------------|
| [name] | [entity] | [N] | [N] |

---

## [AggregateName]

**Root entity:** [what]
**Key files:** [list]
**Goals served:** (leave blank — Node 3 fills this in)

### States
| State | Type | Representation in Code | Location |
|-------|------|----------------------|----------|

### Statechart
(text-based state machine)

### Gaps
| ID | Sev | Description | Code Location |
|----|-----|-------------|---------------|

---

(repeat for each aggregate)

## Cross-Aggregate Transition Map

(Show how aggregates connect — which exit event triggers which entry)

## Impossible State Combinations

| Combination | Risk | Source |
|-------------|------|--------|

## Gap Summary — All Aggregates by Severity

**CRITICAL:** ...
**HIGH:** ...
**MEDIUM:** ...
**LOW:** ...
Total: [N] gaps across [N] aggregates

## XState Migration Priority

| Rank | Aggregate | Rationale |
|------|-----------|-----------|
```

## Constraints
- Every state must trace to actual code.
- Every gap must reference a specific file and line.
- Do NOT suggest fixes or refactoring. Read-only analysis.
- If an aggregate has fewer than 3 states, note it as "trivial lifecycle" and skip the full statechart format.
- Focus depth on aggregates with the most complex state spaces.
- Your first line must be `# Aggregate & Statechart Analysis`. No preamble.
