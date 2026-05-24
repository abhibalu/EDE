# Node 3 — Goal Tree & Obstacle Register

## Purpose
Reverse-engineer a KAOS goal tree from the statecharts, map every gap to a goal as a confirmed obstacle, run forward obstacle analysis to find what statechart analysis missed, and produce a prioritised requirements delta. The output feeds Node 4 (spec assembly).

## Input
Read the Node 2 statechart analysis from `docs/pipeline/output/02-statecharts.md`.

## Key Concepts

**KAOS Goal Tree**: Decomposes system purpose into AND/OR sub-goals until every leaf is assignable to a single agent (software module, external API, or user). Each gap from Node 2 maps to a confirmed obstacle against a goal.

**Obstacle**: A condition that prevents a goal from being achieved. Confirmed obstacles come from Node 2 gaps. New obstacles come from forward analysis (reading code with goals in mind).

**Requirement**: An action needed to resolve an obstacle. Prioritised as MUST / SHOULD / COULD.

## Execution Strategy — Use Sub-Agents

### Step 1: Build the goal tree (you do this yourself)
Read the Node 2 analysis. Reverse-engineer:
- One top-level goal for the entire system (G0)
- 3-5 second-level goals, one per major capability (G1–G5)
- Leaf goals under each, one per aggregate or cross-cutting concern (G1.1, G1.2, etc.)
- Mark each leaf with its responsible agent: `[Software: Module]`, `[External: Service]`, or `[User]`

Target 15-25 leaf goals. Fewer = too abstract. More = mixing requirements into goals.

### Step 2: Dispatch sub-agents (one per aggregate)
Each sub-agent gets the aggregate's statechart/gaps from Node 2, the relevant goal tree branch, the Sub-Agent Prompt, and access to the codebase.

### Step 3: Cross-aggregate obstacle analysis (you do this yourself)
After collecting sub-agent outputs, look for obstacles BETWEEN aggregates:
- Cross-aggregate boundary risks (from Node 2's transition map)
- Impossible state combinations (from Node 2)
- Gaps in the goal tree no aggregate owns
- Security, privacy, data integrity concerns

### Step 4: Assemble
Compile all obstacles, deduplicate, and produce the requirements delta with implementation roadmap.

---

## Sub-Agent Prompt

```
You are mapping confirmed gaps to goals for one aggregate, and discovering remaining obstacles.

AGGREGATE: [AGGREGATE_NAME]
GOAL TREE BRANCH:
[paste the relevant sub-tree]

STATECHART AND GAPS:
[paste the aggregate's statechart and gap table from Node 2]

Your job:

1. MAP EACH GAP TO A GOAL
For every gap (e.g., VP-G1, S-G1), identify which leaf goal it violates.
If a gap violates multiple goals, list all.
If a gap doesn't map to any goal, propose a new leaf goal.

Format:
[GapID] → violates [GoalID]: [one sentence]

2. FORWARD OBSTACLE ANALYSIS
Read the actual code files for this aggregate. For each leaf goal, ask:
"What ELSE could prevent this from being achieved?"

Look for:
- Error paths with no user recovery
- Data that can become stale or inconsistent over time
- External service dependencies with no degradation strategy
- Assumptions about user behaviour that may not hold
- Missing validation allowing bad data to propagate
- Concurrency issues beyond what statecharts found
- Accessibility or cross-device issues

For each new obstacle:

💡 NEW OBSTACLE for [GoalID]: [description]
   Evidence: [filepath:line or logical argument]
   Severity: [CRITICAL/HIGH/MED/LOW]
   Resolution type: [New requirement | Goal weakening | Operational workaround]
   Suggested resolution: [one sentence — do NOT implement]

3. REQUIREMENTS DELTA
List every requirement to close all gaps and obstacles.

MUST (blocks goal achievability):
- [R-XX] [requirement] — resolves [O-XX]

SHOULD (degrades goal quality):
- [R-XX] [requirement] — resolves [O-XX]

COULD (improves robustness):
- [R-XX] [requirement] — resolves [O-XX]

CONSTRAINTS:
- Every requirement traces to a gap or obstacle. No untethered suggestions.
- Do NOT write implementation code. Requirements only.
- One sentence per requirement.
```

---

## Output Format

Your first line must be `# Goal Tree & Obstacle Register`. No preamble.

```markdown
# Goal Tree & Obstacle Register

## System Goal Tree

(Full KAOS tree in text format with G0, G1-G5, leaf goals, agent assignments, and obstacle references per leaf)

## Obstacle Register

### Confirmed Obstacles (from Node 2 gaps)
| ID | Violates Goal | Gap Source | Description | Severity |
|----|---------------|-----------|-------------|----------|

### New Obstacles (from forward analysis)
| ID | Violates Goal | Evidence | Description | Severity | Resolution Type |
|----|---------------|----------|-------------|----------|-----------------|

## Requirements Delta

### [AggregateName] Requirements
**MUST:**
| ID | Requirement | Resolves |
|----|-------------|----------|

**SHOULD:**
| ID | Requirement | Resolves |
|----|-------------|----------|

**COULD:**
| ID | Requirement | Resolves |
|----|-------------|----------|

(repeat per aggregate)

### Cross-Aggregate Requirements
(same format)

## Implementation Roadmap

(Phased plan using XState Migration Priority from Node 2)

**Phase 1: [name] — [scope]**
- Requirements: [list]
- Gaps closed: [list]
- Risk reduced: [summary]

(repeat per phase)

## Metrics
| Metric | Value |
|--------|-------|
| Total goals | N |
| Confirmed obstacles | N |
| New obstacles | N |
| Total requirements | N |
| MUST | N |
| SHOULD | N |
| COULD | N |
```

## Constraints
- Every requirement traces to a specific obstacle. No floating suggestions.
- Every obstacle traces to a specific goal. No unanchored problems.
- Do NOT write implementation code.
- New obstacles must be genuinely new — not restatements of Node 2 gaps.
- Your first line must be `# Goal Tree & Obstacle Register`. No preamble.
