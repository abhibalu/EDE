# Node 3 — Goal Tree & Obstacle Register

## Purpose
Reverse-engineer a KAOS goal tree from the statecharts, map every gap to a confirmed obstacle, run forward obstacle analysis, and produce a prioritised requirements delta. The output feeds Node 4 (spec assembly).

## Input
Read the Node 2 output JSON from `docs/pipeline/output/02-statecharts.json`.

## Key Concepts

**KAOS Goal Tree**: Decomposes system purpose into AND/OR sub-goals until every leaf is assignable to a single agent (software module, external API, or user). Each gap from Node 2 maps to a confirmed obstacle against a goal.

**Obstacle**: A condition that prevents a goal from being achieved. Confirmed obstacles come from Node 2 gaps. New obstacles come from forward analysis.

**Requirement**: An action needed to resolve an obstacle. Every requirement MUST trace to an obstacle. Every obstacle MUST trace to a goal.

## Output Schema

```typescript
interface Node3Output {
  pipelineVersion: "0.1.0";
  node: 3;
  generatedAt: string;
  registry: Registry;

  goalTree: GoalNode;                 // recursive tree, root MUST be G0
  confirmedObstacles: ConfirmedObstacle[];
  newObstacles: NewObstacle[];
  requirements: Requirement[];
  roadmap: Phase[];                   // min 1 phase
  metrics: {
    totalGoals: number;               // all nodes in tree
    leafGoals: number;                // nodes with no children
    confirmedObstacles: number;
    newObstacles: number;
    totalRequirements: number;
    must: number;
    should: number;
    could: number;
    // totalRequirements MUST equal must + should + could
  };
}

interface GoalNode {
  id: string;                         // G0 (root), G1, G1.1, G1.2, G2, G2.1, etc.
  description: string;
  decomposition: "AND" | "OR" | null; // null for leaf goals
  agent: string | null;               // leaf only: "[Software: Module]", "[External: Service]", "[User]"
  children: GoalNode[];               // [] for leaf goals
  obstacleRefs: string[];             // ObstacleIDs that threaten this goal
}

interface ConfirmedObstacle {
  id: string;                         // format: O-{AggCode}-{seq} e.g. "O-MS-1"
  violatesGoals: string[];            // GoalIDs — must exist in tree. Min 1.
  gapSource: string;                  // GapID from Node 2 — must exist. e.g. "MS-G1"
  description: string;
  severity: "CRITICAL" | "HIGH" | "MED" | "LOW";
}

interface NewObstacle {
  id: string;                         // format: O-N{seq} e.g. "O-N1"
  violatesGoals: string[];            // GoalIDs. Min 1.
  evidence: string;                   // filepath:line or logical argument
  description: string;
  severity: "CRITICAL" | "HIGH" | "MED" | "LOW";
  resolutionType: "New requirement" | "Goal weakening" | "Operational workaround";
}

interface Requirement {
  id: string;                         // format: R-{AggCode}-{seq} or R-XA-{seq} (cross-aggregate)
  priority: "MUST" | "SHOULD" | "COULD";
  description: string;
  resolves: string[];                 // ObstacleIDs. Min 1. Every req resolves ≥1 obstacle.
}

interface Phase {
  number: number;                     // sequential from 1
  name: string;
  scope: string;                      // what this phase covers
  requirements: string[];             // ReqIDs scheduled in this phase. Min 1.
  gapsClosed: string[];               // GapIDs and ObstacleIDs addressed
  riskReduced: string;
}
```

## Execution Strategy

### Step 1: Build the goal tree (you do this yourself)
Read the Node 2 analysis. Reverse-engineer:
- **G0**: one top-level goal for the entire system
- **G1–G5**: 3-5 second-level goals, one per major capability
- **Leaf goals**: one per aggregate or cross-cutting concern (G1.1, G1.2, etc.)
- Mark each leaf with its responsible agent

Target 15-25 leaf goals. Fewer = too abstract. More = mixing requirements into goals.

### Step 2: Map confirmed obstacles (you do this yourself)
For every gap in Node 2 (across all aggregates), create a confirmed obstacle:
- id: O-{AggCode}-{sequential number}
- gapSource: the gap ID from Node 2
- violatesGoals: which leaf goal(s) this gap threatens
- severity: preserve from Node 2's gap severity

### Step 3: Forward obstacle analysis (dispatch sub-agents)
One sub-agent per aggregate reads code looking for obstacles the statechart analysis missed.

### Step 4: Requirements delta (you do this yourself)
For every obstacle (confirmed + new):
- Create a requirement that resolves it
- Assign priority:
  - **MUST**: blocks goal achievability (typically resolves CRITICAL/HIGH obstacles)
  - **SHOULD**: degrades goal quality (typically resolves MED obstacles)
  - **COULD**: improves robustness (typically resolves LOW obstacles or is additive)

### Step 5: Roadmap
Phase requirements using Node 2's migration priority ranking.
- Phase 1: all MUST requirements for highest-priority aggregate
- Subsequent phases: SHOULD, COULD, and remaining aggregates
- Every requirement must appear in exactly one phase

### Step 6: Validate before emitting
Before producing the final JSON, self-check:
- [ ] Every confirmed obstacle's gapSource exists in Node 2 gaps
- [ ] Every obstacle's violatesGoals exist in the goal tree
- [ ] Every requirement's resolves references a defined obstacle
- [ ] Every CRITICAL obstacle has at least one MUST requirement
- [ ] Every phase's requirements are defined
- [ ] metrics counts match actual counts
- [ ] totalRequirements == must + should + could
- [ ] Goal tree root is G0

---

## Sub-Agent Prompt (Forward Obstacle Analysis)

```
You are finding obstacles that statechart analysis missed for one aggregate.

AGGREGATE: [AGGREGATE_NAME]
GOAL TREE BRANCH:
[paste the relevant sub-tree as JSON]

STATECHART AND GAPS (from Node 2):
[paste the aggregate's states, transitions, and gaps as JSON]

For each leaf goal in this branch, read the relevant code files and ask:
"What ELSE could prevent this goal from being achieved?"

Look for:
- Error paths with no user recovery
- Data that can become stale or inconsistent
- External service dependencies with no degradation strategy
- Assumptions about user behaviour that may not hold
- Missing validation allowing bad data to propagate
- Concurrency issues
- Accessibility or cross-device issues

For each new obstacle found:

{
  "id": "O-N{seq}",
  "violatesGoals": ["G1.2"],
  "evidence": "src/services/order.ts:45 — no null check on payment_id",
  "description": "Order can be submitted with null payment reference",
  "severity": "HIGH",
  "resolutionType": "New requirement"
}

CONSTRAINTS:
- New obstacles must be genuinely new — not restatements of Node 2 gaps.
- Every obstacle must cite evidence (file:line or logical argument).
- Do NOT write implementation code. Observations only.
```

---

## ID Assignment Rules

| Entity | Format | Example | Sequential within |
|--------|--------|---------|-------------------|
| Confirmed obstacle | O-{AggCode}-{seq} | O-MS-1 | aggregate |
| New obstacle | O-N{seq} | O-N1 | global |
| Requirement | R-{AggCode}-{seq} | R-MS-01 | aggregate |
| Cross-agg requirement | R-XA-{seq} | R-XA-01 | global |

## Constraints
- Every requirement traces to a specific obstacle. No floating suggestions.
- Every obstacle traces to a specific goal. No unanchored problems.
- Goal tree root must be G0.
- Do NOT write implementation code. Requirements only.
- New obstacles must be genuinely new — not restatements of Node 2 gaps.
- Output ONLY the final JSON object. No markdown. No explanation.
- Run the self-check in Step 6 before emitting. If any check fails, fix it.
