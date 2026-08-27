# EDE -- Domain Extraction Engine

Formal grammar and validators for the 5-node domain extraction pipeline. Defines the intermediate representation (IR) that flows between nodes, with four-layer validation.

## Architecture

```
Code (ephemeral)
  |
Node 0 -> JSON  -->  ede validate (L1+L2)
  |
Node 1 -> JSON  -->  ede validate (L1+L2+L3, needs Node 0)
  |
Node 2 -> JSON  -->  ede validate (L1+L2+L3, needs Node 1)
  |
Node 3 -> JSON  -->  ede validate (L1+L2+L3, needs Node 2)
  |
Node 4 -> JSON  -->  ede validate (L1+L2+L3, needs all prior)
```

Claude Code is the pipeline runner. It reads prompts, reads codebases, produces JSON, and runs `ede validate` to self-check. This Python package provides **guardrails** (validation + assembly), not orchestration.

## Installation

```bash
pip install -e .
```

## CLI Commands

### validate

Progressive validation with L1 (schema) + L2/L3 (cross-node) checks:

```bash
ede validate --node0 output/00-recon.json
ede validate --node0 output/00-recon.json --node1 output/01-events.json
ede validate --node0 00.json --node1 01.json --node2 02.json --node3 03.json --node4 04.json
ede validate --node0 00.json --strict  # reject coerced types
```

### assemble

Merge sub-agent fragments into validated node output:

```bash
ede assemble --fragments-dir fragments/node1/ --node 1 --registry-file 00-recon.json --output 01-events.json
ede assemble --fragments-dir fragments/node2/ --node 2 --registry-file 00-recon.json --node1-file 01-events.json --output 02-statecharts.json
```

### schema

Dump JSON Schema for a node model:

```bash
ede schema --node 1
```

### coverage

Cross-reference Node 0 keyFiles against Node 1 filesScanned. Also flags scan
areas that produced zero events, which usually means a sub-agent silently did
nothing:

```bash
ede coverage --node0 00-recon.json --node1 01-events.json
```

### validate-fragment

L1 + intra-fragment L2 on a single sub-agent fragment, so an agent can
self-check before the orchestrator ever sees the file. Pass `--repo` to include
L4 path probing:

```bash
ede validate-fragment --node 2 --fragment fragments/node2/ORD.json
ede validate-fragment --node 1 --fragment fragments/node1/US.json --repo /path/to/target
```

### verify-paths

L4 — resolve every path-typed field in the artifacts against the repository on
disk. Advisory (`WARN`); always exits 0:

```bash
ede verify-paths --repo /path/to/target --node0 00-recon.json --node1 01-events.json
```

### render

Deterministic Markdown spec from the five validated artifacts. Zero LLM cost,
no templating dependency:

```bash
ede render --node0 00.json --node1 01.json --node2 02.json --node3 03.json --node4 04.json --output SPEC.md
```

## Python API

```python
from ede import Node1Output, validate_pipeline

# L1: parse and validate structure
node1 = Node1Output.model_validate(raw_json)

# L2 + L3: cross-reference checks
result = validate_pipeline({"node0": n0, "node1": node1})
if not result["valid"]:
    for f in result["findings"]:
        print(f"{f.level} [{f.rule}]: {f.message}")
```

## Four Validation Layers

| Layer | What | How | When | Level |
|-------|------|-----|------|-------|
| L1 -- Schema | Structural validity | `NodeNOutput.model_validate(data)` | Per-node, immediate | raises |
| L2 -- Referential | IDs resolve across nodes | `validate_node_n(current, previous)` | At node boundary | `ERROR` |
| L3 -- Semantic | Domain-level correctness | Same validators, different rules | At node boundary | `WARN` |
| L4 -- Path | Claims resolve on disk | `verify_*_paths(artifact, repo_root)` | Against the target repo | `WARN` |

L1--L3 prove the JSON is self-consistent. L4 is the only layer that compares it
to reality: it resolves every path-typed field against the target repository,
including at the fragment boundary before assembly folds fragment output into
the node artifact. A missing path is a strong signal a claim was hallucinated
or stale.

L2 and L3 deliberately are **not** `@model_validator`s. A model validator sees
only its own instance, which is context-free scope; cross-node reference needs
data from another artifact. See `FORMAL_THEORY.md` for why that boundary is
forced rather than chosen.

See `CONSTRAINT_RULES.md` for the complete rule catalogue.

## Obstacle Grammar

`ede/grammar/` holds a frozen, versioned vocabulary of 20 stack-independent
obstacle claim types with declared operand arity, required slots, and a
two-layer evidence/inference discharge model. `doc/phase0/` holds its empirical
validation against a 92-obstacle corpus, plus a pre-registered falsification
test.

Data and analysis only -- not imported by the package, no effect on the CLI.
See the root `README.md` for the full description.

## Design Decisions

See `ARCHITECTURE_DECISIONS.md` for the full rationale behind all settled decisions.
