# EDE Validator Implementation — Reconnaissance Report

> **Status: a self-audit, kept as a record.** This report drove the L4 work that
> followed it — the gap it identified between "the JSON is self-consistent" and
> "the JSON describes the actual repository" is what `ede/verifiers/paths.py`
> now closes. The L4 column below was added afterwards; everything else is the
> original findings, and they still hold. In particular the L2-fragment
> asymmetry is unchanged: the `validate-fragment` L2 block is still guarded by
> `if node == 2`, so Nodes 1 and 3 get no intra-fragment referential checks.

## Summary Table

| Node | L1 | L2-fragment | L2-assembled | L3 | L4 | CLI wired |
|------|-----|-------------|--------------|-----|-----|-----------|
| 0    | ✅  | N/A (no fragments) | ✅ | ⚠️ | ✅ | ✅ |
| 1    | ✅  | ⚠️ | ✅ | ⚠️ | ✅ | ✅ |
| 2    | ✅  | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| 3    | ✅  | ❌ | ✅ | ⚠️ | N/A (no path fields) | ✅ |
| 4    | ✅  | N/A (no fragments) | ✅ | ⚠️ | ✅ | ✅ |

Legend: ✅ implemented, ⚠️ partial (some checks present but gaps vs. spec), ❌ missing, N/A not applicable.

Fragments also get L4 coverage through `verify_fragment_paths`, reachable via
`ede validate-fragment --repo <target>`. That is the highest-value probe point:
it catches an invented path while it can still be attributed to the sub-agent
that produced it, before assembly folds it into the node output.

---

## Shared Infrastructure

- **CLI framework**: Typer at `ede/cli.py`
- **Subcommands wired** (all in `ede/cli.py`):
  - `validate` (line 22) — L1 parse + L2/L3 via `validate_pipeline()`
  - `assemble` (line 93) — fragment assembly for nodes 1, 2, 3
  - `schema` (line 165) — JSON Schema dump for node or fragment models
  - `coverage` (line 206) — Node 0 keyFiles vs Node 1 filesScanned cross-ref
  - `validate-fragment` (line 256) — L1 + cheap L2 for individual fragments, optional L4 via `--repo`
  - `verify-paths` (line 330) — L4 path resolution against the target repository
  - `render` (line 392) — Markdown spec generation from all 5 nodes
- **Shared validation error type**: `Finding` at `ede/primitives.py:152-164`
  - Fields: `level: FindingLevel (ERROR|WARN|INFO)`, `node: int`, `where: str`, `message: str`, `rule: str | None`
- **Orchestrator return type**: `ValidationResult` (TypedDict) at `ede/constraints.py:449-454`
  - Fields: `valid: bool`, `errors: int`, `warnings: int`, `infos: int`, `findings: list[Finding]`
- **Fragment schemas**: Pydantic models in `ede/fragments.py` (Node1Fragment, Node2Fragment, Node3Fragment)
- **Node output schemas**: Pydantic models in `ede/nodes/node0.py` through `node4.py`

---

## Per-Node Detail

### Node 0: Codebase Reconnaissance

- **L1**
  - Status: implemented
  - File(s): `ede/nodes/node0.py`
  - Validates: Field presence, type constraints (min_length on repo, languages, key file paths), enum validation for ArchitectureType, dispatch_plan length (1-20)
  - Gaps vs. spec: none observed

- **L2-fragment**
  - Status: N/A — Node 0 has no fragment type (produced directly, not by sub-agents)

- **L2-assembled**
  - Status: implemented
  - File(s): `ede/constraints.py:75-98` (`validate_node0`)
  - Validates: Unique area codes in registry (L2-unique-area-codes); dispatch plan area codes match registry (L2-dispatch-matches-registry)
  - Gaps vs. spec: none observed

- **L3**
  - Status: partial
  - File(s): `ede/constraints.py:92-96`
  - Validates: If persistence.database != "none", schema_entities should be non-empty (L3-schema-completeness)
  - Gaps vs. spec: Only one semantic invariant. No checks for dispatch_plan coverage (every area dispatched?), no validation of architecture type vs actual structure.

- **CLI hook**: `ede validate --node0 <path>` → `cli.py:30-40` → parses with `Node0Output.model_validate()`, then `validate_pipeline()` at `constraints.py:457`

- **Test fixtures**:
  - Pass fixtures: `tests/conftest.py:45-79` (node0_data fixture) — 1 complete pipeline fixture
  - Fail fixtures: no dedicated Node 0 negative tests; constraint tests only cover it as part of full pipeline pass case

### Node 1: Domain Event Extraction

- **L1**
  - Status: implemented
  - File(s): `ede/nodes/node1.py`, `ede/fragments.py:36-54`
  - Validates: EventID format regex, event name PascalCase regex, evidence min_length=10, trigger min_length=1, state_change min_length=1, area_code regex, ScanArea.directories min_length=1, CodeRef structure
  - Gaps vs. spec: No check that event names are **past-tense** (only PascalCase enforced); no check that trigger starts with an **imperative verb**; no check that state_change matches "from X to Y" shape; no check that evidence contains **code-shaped tokens** (function names, file paths, etc.)

- **L2-fragment**
  - Status: partial
  - File(s): `ede/cli.py:290-310` (validate-fragment command, node==1 branch)
  - Validates: L1 schema only — **no intra-fragment referential checks** for Node 1. The L2 block at cli.py:293-299 only fires for node==2.
  - Gaps vs. spec: No check that `predecessor_names`/`successor_names` reference other events in the same fragment; no check that `location.file` appears in `files_scanned`; no area_code registry check (would need registry file for that).

- **L2-assembled**
  - Status: implemented
  - File(s): `ede/constraints.py:104-165` (`validate_node1`)
  - Validates: Event area code prefix in registry (L2-event-area-code); predecessor/successor IDs resolve in catalogue (L2-predecessor-resolves, L2-successor-resolves); unique event IDs (L2-unique-event-ids)
  - Gaps vs. spec: No check for duplicate `name + location` pairs (dedup is done by assembler but not re-checked post-assembly). No check that `location.file` appears in any ScanArea's `files_scanned`.

- **L3**
  - Status: partial
  - File(s): `ede/constraints.py:129-156`
  - Validates:
    - No self-referential predecessor/successor links (L3-no-self-reference)
    - Predecessor/successor symmetry — if A lists B as successor, B should list A as predecessor (L3-link-symmetry)
    - Minimum 5 events warning if no truncation (L3-minimum-events)
  - Gaps vs. spec:
    - No past-tense check on event names (only PascalCase at L1)
    - No imperative-verb check on trigger field
    - No "from X to Y" shape check on state_change
    - No code-shaped evidence check
    - No predecessor graph acyclicity check
    - No per-area event count ≤ 15 check at L3 (assembler truncates at 15 but constraint layer doesn't flag it)

- **CLI hook**: `ede validate --node1 <path>` → `cli.py:42-48` → `Node1Output.model_validate()` + `validate_pipeline()`. Fragment: `ede validate-fragment --node 1 --fragment <path>` → `cli.py:256-310`.

- **Test fixtures**:
  - Pass fixtures: `tests/conftest.py:83-164` (node1_data) — 4 events across 2 areas
  - Fail fixtures: `tests/test_negative.py` (3 L1 tests), `tests/test_constraints.py` (4 L2/L3 tests), `tests/test_fragment_validation.py` (2 node1 tests)

### Node 2: Aggregate & Statechart Extraction

- **L1**
  - Status: implemented
  - File(s): `ede/nodes/node2.py`, `ede/fragments.py:57-95`
  - Validates: StateEntry evidence min_length=10, Gap ID format regex, Aggregate.states min_length=1, GapSummary total == critical+high+med+low (L1 promotion via model_validator at node2.py:98)
  - Gaps vs. spec: none observed

- **L2-fragment**
  - Status: implemented
  - File(s): `ede/cli.py:293-308`
  - Validates: Transition source/target must be declared state names within the fragment
  - Gaps vs. spec: No check that gap `seq` values are unique within fragment; no check that `event_name` in transitions matches any known event name (would require cross-fragment context).

- **L2-assembled**
  - Status: implemented
  - File(s): `ede/constraints.py:171-257` (`validate_node2`)
  - Validates: Unique aggregate codes (L2-unique-agg-codes); transition events resolve in Node 1 catalogue (L2-transition-event-resolves); gap ID prefix matches aggregate code (L2-gap-prefix); transition source/target are declared states (L2-state-exists); unique state names per aggregate (L2-unique-states); cross-agg transition events and aggregates resolve (L2-cross-agg-event, L2-cross-agg-code)
  - Gaps vs. spec: none observed

- **L3**
  - Status: partial
  - File(s): `ede/constraints.py:214-227`
  - Validates:
    - Non-final states should have outgoing transitions (L3-no-dead-ends) — WARN level
  - Gaps vs. spec: No check for unreachable states (states with no incoming transitions except initial); no check that each aggregate has at least one final state; no statechart well-formedness beyond dead-ends.

- **CLI hook**: `ede validate --node2 <path>` + `--node1 <path>` → `cli.py` → `validate_pipeline()`. Fragment: `ede validate-fragment --node 2 --fragment <path>` → `cli.py:293-308`.

- **Test fixtures**:
  - Pass fixtures: `tests/conftest.py:168-280` (node2_data) — 2 aggregates
  - Fail fixtures: `tests/test_constraints.py:77-96` (2 tests: gap prefix, dead-end state), `tests/test_fragment_validation.py:80-153` (2 tests: valid + bad transition ref)

### Node 3: Goal Tree & Obstacle Register

- **L1**
  - Status: implemented
  - File(s): `ede/nodes/node3.py`, `ede/fragments.py:98-115`
  - Validates: GoalID format regex, ObstacleID format regex, ReqID format regex, NewObstacle must use O-N prefix (model_validator at node3.py:67), Node3Metrics totalRequirements == must+should+could (model_validator at node3.py:102), Requirement.resolves min_length=1, Phase.requirements min_length=1
  - Gaps vs. spec: none observed

- **L2-fragment**
  - Status: missing
  - File(s): `ede/cli.py:293-308` — the L2 block only handles `node == 2`
  - Validates: nothing for Node 3 fragments
  - Gaps vs. spec: No check that `violates_goals` reference plausible goal IDs; no check that `seq` values are unique within fragment; no intra-fragment referential integrity at all.

- **L2-assembled**
  - Status: implemented
  - File(s): `ede/constraints.py:263-366` (`validate_node3`)
  - Validates: Confirmed obstacle gap_source resolves in Node 2 gaps (L2-obstacle-gap-source); obstacles reference valid goals (L2-obstacle-goal-ref); requirements resolve valid obstacles (L2-req-resolves); phase requirements exist (L2-phase-req-exists); unique obstacle IDs (L2-unique-obstacle-ids); unique requirement IDs (L2-unique-req-ids)
  - Gaps vs. spec: none observed

- **L3**
  - Status: partial
  - File(s): `ede/constraints.py:312-350`
  - Validates:
    - CRITICAL severity obstacle → at least one MUST requirement resolves it (L3-critical-needs-must)
    - Every requirement in at least one roadmap phase (L3-req-in-roadmap)
    - Goal tree root is G0 (L3-root-is-G0)
    - Metrics match actual counts for totalGoals, leafGoals, confirmedObstacles, newObstacles (L3-metrics-match)
  - Gaps vs. spec: No check for goal tree completeness (every leaf goal should have at least one obstacle or be marked clean); no check that roadmap phases are monotonically numbered; no check that obstacle severity distributions are plausible.

- **CLI hook**: `ede validate --node3 <path>` + `--node2 <path>` → `validate_pipeline()`. Fragment: `ede validate-fragment --node 3 --fragment <path>` → L1 only (cli.py:288, no L2 block).

- **Test fixtures**:
  - Pass fixtures: `tests/conftest.py:284-418` (node3_data)
  - Fail fixtures: `tests/test_constraints.py:100-117` (1 test: critical-without-must), `tests/test_fragment_validation.py:155-184` (2 tests: valid + empty obstacles)

### Node 4: Spec Assembly (Compilation Layer)

- **L1**
  - Status: implemented
  - File(s): `ede/nodes/node4.py`
  - Validates: FileIndexEntry.requirements min_length=1, ChangelogEntry.date ISO format regex, FileCategory enum, all numeric metric fields present
  - Gaps vs. spec: none observed

- **L2-fragment**
  - Status: N/A — Node 4 has no fragment type (produced as final compilation, not by sub-agents)

- **L2-assembled**
  - Status: implemented
  - File(s): `ede/constraints.py:372-435` (`validate_node4`)
  - Validates: File index requirement IDs exist in Node 3 (L2-file-index-req)
  - Gaps vs. spec: none observed

- **L3**
  - Status: partial
  - File(s): `ede/constraints.py:391-433`
  - Validates:
    - Every Node 3 requirement appears in file index (L3-req-in-file-index)
    - 12-field metrics consistency cross-check against Nodes 1-3 actual counts (L3-metrics-consistency)
  - Gaps vs. spec: No check that changelog entries are sorted by date; no check that system_purpose is non-trivial; no check that sources reference valid nodes.

- **CLI hook**: `ede validate --node4 <path>` + all prior nodes → `validate_pipeline()`.

- **Test fixtures**:
  - Pass fixtures: `tests/conftest.py:422-453` (node4_data)
  - Fail fixtures: `tests/test_constraints.py:121-133` (1 test: metrics consistency)

---

## Cross-cutting Observations

- **No dedicated `validators/` directory**: All validation lives in three files — `constraints.py` (L2+L3 post-assembly), `cli.py:256-310` (L2-fragment for node 2 only), and the Pydantic models themselves (L1). This is clean but means L2-fragment logic for node 2 is embedded in the CLI rather than in a reusable function.

- **L2-fragment checks are asymmetric**: Node 2 has intra-fragment referential checks (transition source/target vs declared states); Nodes 1 and 3 have **zero** L2-fragment checks. The `validate-fragment` command's L2 block (`cli.py:293-299`) is guarded by `if node == 2`.

- **L3 is consistently thin across all nodes**: Every node has basic L3 invariants (self-reference, symmetry, dead-ends, critical→MUST) but none reach the deeper semantic checks described in the spec (past-tense names, imperative triggers, acyclicity, code-shaped evidence).

- **Assemblers carry some validation responsibility**: `ede/assemblers.py` performs deduplication (name+location), truncation enforcement (15 events/area), and symmetry auto-fixing. These emit `Finding` objects but aren't part of the `validate_*` functions — they run during `assemble` only.

- **Naming is consistent**: All constraint functions use `validate_nodeN()`, all rules use `L{N}-kebab-case` naming for the `rule` field. Findings use the shared `Finding` type everywhere.

- **No JSON Schema files on disk**: All schema definition is via Pydantic models; JSON Schema is generated on-the-fly by `ede schema` command.

- **Test fixtures are code-only** (in `conftest.py`), not external JSON files. No `tests/fixtures/` directory exists.

---

## Open Questions

1. **Node 1 L3 spec vs. implementation divergence**: The node1.py docstring (line 12) claims L3 includes "event names PascalCase" — but PascalCase is enforced at L1 via regex. The deeper L3 checks mentioned in the task spec (past-tense, imperative trigger, stateChange shape, code evidence, acyclicity) are not implemented anywhere. Is the docstring the authoritative spec, or is the task spec?

2. **Per-area cap enforcement layer**: The 15-event-per-area truncation is enforced by the assembler (`assemblers.py:72-96`), not by the constraint layer. Should this also be a post-assembly L3 warning, or is assembler enforcement sufficient?

3. **L2-fragment for Node 1**: Should `validate-fragment --node 1` check that `predecessor_names`/`successor_names` reference other events within the same fragment? Currently it only does L1.

4. **Coverage command vs. L2-fragment overlap**: The `coverage` command (`cli.py:206-251`) checks keyFiles vs filesScanned, which is conceptually an L2 check. Should `location.file ∈ filesScanned` also be checked at the L2-fragment or L2-assembled layer?

5. **Node 3 fragment L2**: Should `validate-fragment --node 3` check that `violates_goals` entries look like valid GoalIDs (regex match), even without the full goal tree available?
