# `ede/` — the package

Seven modules and three subpackages. This is a map for reading the code; for
using it, see [`docs/cli-and-api.md`](../docs/cli-and-api.md).

| Module | Lines | Responsibility |
|---|---:|---|
| `primitives.py` | 163 | The atoms: six regex-constrained ID types, `CodeRef`, `Registry`, `PipelineEnvelope`, nine closed enums, and the shared `Finding` type every layer emits |
| `nodes/` | 535 | The five node schemas — [see its README](nodes/README.md) |
| `fragments.py` | 117 | Sub-agent output schemas. ID-free and name-linked, because no sub-agent can know the global ID space |
| `assemblers.py` | 314 | Fragments → node output. Every mechanical operation an LLM does badly: ID assignment, dedup, name→ID resolution, link-symmetry repair |
| `constraints.py` | 491 | L2 and L3 — the cross-node checks that cannot be model validators |
| `verifiers/` | 301 | L4 — claims vs. disk. [See its README](verifiers/README.md) |
| `renderer.py` | 382 | Deterministic Markdown from the five artifacts. Zero LLM cost, no templating dependency |
| `cli.py` | 433 | Seven Typer commands |
| `grammar/` | — | Obstacle claim vocabulary. Data only, imported by nothing. [See its README](grammar/README.md) |

## Where the validation layers live

The four layers are deliberately not four modules. Two of them live in the type
system:

- **L1** is `primitives.py` plus `nodes/` — enforced by Pydantic at
  `model_validate()`. There is no L1 module because there is no L1 code; the
  schema *is* the check.
- **L2 and L3** are both `constraints.py`, sharing the same `validate_node_n()`
  functions and differing only in severity. They are separate from L1 because a
  `@model_validator` can only see its own instance, and cross-node reference
  needs another artifact.
- **L4** is `verifiers/`, separate from `constraints.py` because it consults
  the filesystem rather than the document.

[`docs/formal-theory.md`](../docs/formal-theory.md) argues why that split is
forced rather than stylistic.

## Reading order

`primitives.py` first — every other module is built from its types, and the
design notes at the top explain why IDs are pattern-validated strings and why
`CodeRef` is an object rather than a `"file:line"` string (both are answers to
observed LLM failure modes).

Then `nodes/node1.py` as the simplest complete schema, `assemblers.py` for the
central architectural pattern, and `constraints.py` for the rule catalogue in
executable form.
