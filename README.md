# EDE — Domain Extraction Engine

A formal, validator-backed pipeline for extracting a domain specification from an existing codebase. The code itself is ephemeral input; the persisted artifacts are JSON intermediates that flow through a 5-node pipeline, each with progressive schema and cross-reference validation.

The pipeline is run by an LLM (Claude Code). This repository provides the **prompts, schemas, and validators** that turn freeform extraction into a reproducible, checkable process.

## The pipeline

```
Code (ephemeral)
  │
  ▼
Node 0 — Recon          → 00-recon.json        (registry, key files)
  │
  ▼
Node 1 — Events         → 01-events.json       (event catalogue w/ evidence)
  │
  ▼
Node 2 — Statecharts    → 02-statecharts.json  (state machines w/ evidence)
  │
  ▼
Node 3 — Goals          → 03-goals.json        (goals, obstacles, requirements)
  │
  ▼
Node 4 — Assembly       → 04-assembly.json     (compiled spec + file index)
  │
  ▼
Renderer → Markdown (human-readable spec)
```

Each JSON artifact is validated at four layers before the next node runs:

| Layer | Scope | Purpose |
|-------|-------|---------|
| **L1 — Schema** | Single node | Structural validity (types, required fields, ID patterns) |
| **L2 — Referential** | Cross-node | IDs declared in earlier nodes resolve in later ones |
| **L3 — Semantic** | Cross-node | Domain-level invariants (e.g. every state change has evidence) |
| **L4 — Path** | JSON vs. disk | Every path-typed field resolves against the real repository |

If L1, L2, or L3 fails, the node is re-prompted. No partial state ever propagates.

L4 is the layer that compares claims to reality. L1–L3 only prove the JSON is
self-consistent — a model can be perfectly coherent internally and still have
invented every file path it cites. L4 resolves each path-typed field across
Nodes 0/1/2/4 and at the fragment boundary, before assembly folds fragment
output into the node artifact. Findings are advisory (`WARN`): a missing path
is a strong signal a claim was hallucinated or stale, but a legitimately moved
file should not halt the pipeline. Run it with `ede verify-paths`.

## Repository layout

```
v3_python/   Python implementation: Pydantic models, validators, CLI, assemblers
```

The earlier passes — V1 (markdown prompts) and V2 (TypeScript / Zod) — live on
the `archive/v1-v2` branch for design lineage. They are not part of `main`.

### v3_python (current)

Installable Python package providing the `ede` CLI and library:

```bash
cd v3_python
pip install -e .

ede validate --node0 output/00-recon.json
ede validate --node0 00.json --node1 01.json --node2 02.json --node3 03.json --node4 04.json
ede assemble --fragments-dir fragments/node1/ --node 1 --registry-file 00-recon.json --output 01-events.json
ede schema --node 1
ede coverage --node0 00-recon.json --node1 01-events.json
ede verify-paths --repo /path/to/target --node0 00-recon.json
ede render --node0 00.json --node1 01.json --node2 02.json --node3 03.json --node4 04.json --output SPEC.md
```

## Documentation

| Document | What it covers |
|----------|----------------|
| [`v3_python/README.md`](v3_python/README.md) | Full CLI and Python API surface |
| [`v3_python/FORMAL_THEORY.md`](v3_python/FORMAL_THEORY.md) | Why the layer split is *forced* rather than chosen — the validation layers mapped onto the Chomsky hierarchy, with termination and decidability arguments |
| [`v3_python/CONSTRAINT_RULES.md`](v3_python/CONSTRAINT_RULES.md) | The complete rule catalogue and the evidence → requirement traceability chain |
| [`v3_python/ARCHITECTURE_DECISIONS.md`](v3_python/ARCHITECTURE_DECISIONS.md) | Settled decisions and what was explicitly rejected, with reasons |

The word "grammar" in this repository is not a metaphor. The Pydantic models
*are* a formal grammar — terminals, nonterminals, production rules, start
symbol — and `model_validate()` is its parser. L1 is context-free and L2 is
context-sensitive, which is precisely why L2 cannot be a `@model_validator`: a
model validator has access only to its own instance. The argument is worked out
in [`FORMAL_THEORY.md`](v3_python/FORMAL_THEORY.md).

## Design principles

- **Code is input, JSON is output.** Source code is never stored in the pipeline state. Only validated JSON artifacts persist.
- **Evidence over assertion.** Events and states must carry a `CodeRef` (`{ file, anchor }`) pointing at the line that justifies the claim. Ungrounded claims fail L1.
- **Registry-driven, project-agnostic.** Node 0 establishes the ID registry; every later ID derives from it. A new project gets a new registry — the grammar and validators are unchanged.
- **Claude Code is the runner.** Orchestration lives in the LLM driver. This repo is the guardrail: prompts tell the LLM what to produce; validators tell it when it got the structure wrong.

## Obstacle grammar (research)

The four validation layers constrain the *shape* of what the pipeline emits.
They say nothing about whether an individual finding is **true**. Node 3
produces obstacles as prose, so "is this real?" stays a judgement call.

`v3_python/ede/grammar/` is the vocabulary that makes it a mechanical one:

- **20 claim types** (`TOCTOU`, `ERROR_COLLAPSED`, `NO_WRITER`, …), each
  stack- and project-independent, declaring its operand arity and the slots a
  claim must fill to be well-formed. Required slots are the fields that
  discriminate a true claim from a false one — `ERROR_COLLAPSED` requires
  `handler_form` because the literal form (`.catch(null)` no-op vs.
  `.catch(() => null)` swallow) is the whole discriminator.
- **Two-layer discharge** (`mechanisms.json`): `evidence_mechanism` proves the
  *code fact* and is cheap and replayable against a baseline commit;
  `inference_mechanism` proves the *harm follows* and usually needs a runtime.
  Keeping them apart puts false-positive measurement at the evidence layer.
- `NONE` is defined as **discharge-resistant** — membership is a mechanical
  test (can a discharge be stated?), not a judgement.

`doc/phase0/` holds the empirical validation: all 92 obstacles from a
Documenso run, hand-annotated under the frozen vocabulary. The 11 core types
cover 66/76 real obstacles (87%); content-addressed identity collapses 92
records to 89 while correctly refusing a predicted fourth merge;
`phase1_falsification.py` is a pre-registered test that passes only if a wrong
finding and its source-corrected form differ in a **load-bearing** field rather
than in prose.

Where [`FORMAL_THEORY.md`](v3_python/FORMAL_THEORY.md) treats the *pipeline* as
a formal language and asks whether an artifact is well-formed, the obstacle
grammar asks the next question down: given a well-formed finding, can its truth
be discharged? The first is a membership problem, the second a falsifiability
one.

Status: data and analysis only. `ede/grammar/checkers/` is empty by design —
it fixes the `(claim_type, stack, layer)` keying convention before any checker
exists, so they cannot fork per project. Nothing here is imported by the `ede`
package or affects the CLI.

## Status

- v3_python: active (this branch)
- V1 (markdown prompts) and V2 (TypeScript / Zod): preserved on `archive/v1-v2`
