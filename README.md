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

Each JSON artifact is validated at three layers before the next node runs:

| Layer | Scope | Purpose |
|-------|-------|---------|
| **L1 — Schema** | Single node | Structural validity (types, required fields, ID patterns) |
| **L2 — Referential** | Cross-node | IDs declared in earlier nodes resolve in later ones |
| **L3 — Semantic** | Cross-node | Domain-level invariants (e.g. every state change has evidence) |

If any layer fails, the node is re-prompted. No partial state ever propagates.

## Repository layout

```
V1/          Earliest pass — node prompts only (markdown)
V2/          TypeScript implementation: Zod schemas, validators, prompts
v3_python/   Current Python implementation: Pydantic models, CLI, assemblers
```

`v3_python/` is the active version. V1 and V2 are kept for the design lineage.

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
```

See [`v3_python/README.md`](v3_python/README.md) for the full CLI/API surface and [`v3_python/ARCHITECTURE_DECISIONS.md`](v3_python/ARCHITECTURE_DECISIONS.md) for the rationale behind the settled design.

## Design principles

- **Code is input, JSON is output.** Source code is never stored in the pipeline state. Only validated JSON artifacts persist.
- **Evidence over assertion.** Events and states must carry a `CodeRef` (`{ file, anchor }`) pointing at the line that justifies the claim. Ungrounded claims fail L1.
- **Registry-driven, project-agnostic.** Node 0 establishes the ID registry; every later ID derives from it. A new project gets a new registry — the grammar and validators are unchanged.
- **Claude Code is the runner.** Orchestration lives in the LLM driver. This repo is the guardrail: prompts tell the LLM what to produce; validators tell it when it got the structure wrong.

## Status

- V1: archived (markdown prompts only)
- V2: archived (TypeScript / Zod implementation)
- v3_python: active
