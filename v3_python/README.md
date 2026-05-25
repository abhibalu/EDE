# EDE -- Domain Extraction Engine

Formal grammar and validators for the 5-node domain extraction pipeline. Defines the intermediate representation (IR) that flows between nodes, with three-layer validation.

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

Cross-reference Node 0 keyFiles against Node 1 filesScanned:

```bash
ede coverage --node0 00-recon.json --node1 01-events.json
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

## Three Validation Layers

| Layer | What | How | When |
|-------|------|-----|------|
| L1 -- Schema | Structural validity | `NodeNOutput.model_validate(data)` | Per-node, immediate |
| L2 -- Referential | IDs resolve across nodes | `validate_node_n(current, previous)` | At node boundary |
| L3 -- Semantic | Domain-level correctness | Same validators, different rules | At node boundary |

See `CONSTRAINT_RULES.md` for the complete rule catalogue.

## Design Decisions

See `ARCHITECTURE_DECISIONS.md` for the full rationale behind all settled decisions.
