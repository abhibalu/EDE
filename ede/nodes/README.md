# `ede/nodes/` — the five node schemas

One module per pipeline stage. Together these are the formal grammar: 34 models
whose field definitions are the production rules, and whose `model_validate()`
is the parser. This is L1 in its entirety — there is no separate L1 code.

| Module | Output model | Models | What the stage produces |
|---|---|---:|---|
| `node0.py` | `Node0Output` | 7 | Recon: the registry of area codes, architecture, persistence, key files, dispatch plan |
| `node1.py` | `Node1Output` | 5 | The event catalogue — `DomainEvent`, `ScanArea`, `TruncationInfo` |
| `node2.py` | `Node2Output` | 9 | Statecharts — `Aggregate`, `StateEntry`, `Transition`, `Gap`, cross-aggregate edges |
| `node3.py` | `Node3Output` | 7 | KAOS model — recursive `GoalNode`, obstacles, `Requirement`, roadmap `Phase` |
| `node4.py` | `Node4Output` | 6 | Compiled spec — file index, changelog, metrics |

`__init__.py` re-exports all of them.

## What to notice

**Node 0 is the source of every ID.** The registry it emits seeds the area
codes that become event ID prefixes at Node 1, aggregate codes at Node 2, and
obstacle/requirement prefixes at Node 3. Nothing downstream hardcodes project
knowledge — a new project is a new registry and the same grammar.

**`GoalNode` is directly recursive.** `children: list[GoalNode]` needs
`model_rebuild()`, and it is the reason Node 3 checks require tree traversal
rather than field comparison. It is also the clearest example in the codebase
of a context-free construct: validating it needs a stack.

**Evidence is a schema constraint, not a convention.** `DomainEvent`,
`StateEntry`, and `Transition` all carry `evidence` with `min_length=10`, so an
ungrounded claim fails to parse. `Transition` gained this later than the
others — see decision 10 in
[`architecture-decisions.md`](../../docs/architecture-decisions.md).

**Three model validators sit here rather than in `constraints.py`.**
`GapSummary.check_total`, `Node3Metrics.check_totals`, and
`NewObstacle.check_new_prefix` were L3 rules in the TypeScript version. They
belong at L1 because they reference only fields within their own model. The
boundary is exact: a check can be a `@model_validator` if and only if it never
crosses a node.

## Related

- Rule catalogue: [`docs/constraint-rules.md`](../../docs/constraint-rules.md)
- Why the L1/L2 boundary falls where it does: [`docs/formal-theory.md`](../../docs/formal-theory.md) §5, §6
- The JSON Schema the LLM is given: `ede schema --node N`
