# EDE v3 -- Architecture Decisions

This document consolidates two independent reviews of the V2->V3 migration plan.
It is the reference for why certain decisions were made.

## Settled Decisions

These are final. Do not revisit during implementation.

1. **Pydantic v2 BaseModel replaces Zod schemas.** Direct translation, no conceptual changes.

2. **Three-layer validation stays.** L1 (schema parse), L2 (cross-node referential integrity), L3 (semantic invariants). Do NOT collapse L2/L3 into `@model_validator` -- those checks need data from other nodes.

3. **Fragments and assemblers are first-class.** Sub-agents produce fragments (small, no IDs). Assemblers merge deterministically (dedup, ID assignment, name->ID resolution, symmetry enforcement). This is the core architectural pattern.

4. **Registry propagation.** Node 0 seeds area codes. Every subsequent ID prefix derives from the registry. No hardcoded project knowledge anywhere.

5. **Evidence field is the ReAct grounding contract.** `DomainEvent.evidence` and `StateEntry.evidence` must have `min_length=10`. This prevents LLM fabrication at the schema level.

6. **Claude Code is the pipeline runner.** Claude Code has direct filesystem access to the target codebase. It reads the prompt, reads the code, produces JSON output, and runs `ede validate` to self-check. There is no separate Python process calling an LLM API.

7. **EDE is a CLI validation library, not an LLM orchestrator.** No FastAPI. No `PipelineRunner` class. No LLM API calls. Typer CLI for validation and assembly commands that Claude Code invokes.

## L1 Promotions

Some checks that were L3 in V2 (because Zod's `.refine()` was awkward) became L1 in V3 via Pydantic's `@model_validator(mode='after')`:

- `GapSummary.check_total` -- total must equal sum of components
- `Node3Metrics.check_totals` -- total_requirements must equal must + should + could
- `NewObstacle.check_new_prefix` -- ID must start with O-N

These DO NOT cross node boundaries and only operate on data within the model itself.

## What Was Explicitly Rejected

| Suggestion | Why rejected |
|-----------|-------------|
| FastAPI integration | EDE is not a web server. CLI + library only. |
| OpenAI SDK `response_format` | Claude Code produces output directly. No SDK call involved. |
| `instructor` library | OpenAI-specific, and there's no API call to instrument. |
| `PipelineRunner` class | Claude Code IS the runner. Python provides validation, not orchestration. |
| `@model_validator` for all L2/L3 | Only true for intra-model checks. Cross-node validation cannot be model validators. |
| Retry loop in Python | The retry loop is Claude Code reading validation output and fixing its work. Not a Python `for` loop calling an API. |

## Execution Model

```
User -> Claude Code -> reads prompts/*.md + reads codebase -> writes JSON
                        |
                  runs `ede validate` on its own output
                        |
                  OK -> saves, moves to next node
                  FAIL -> reads findings, fixes output, re-validates
```

### What Python provides

| Component | What it does | How Claude Code uses it |
|-----------|-------------|------------------------|
| `ede validate` | Schema parse + cross-node checks | Claude Code runs it after each node |
| `ede assemble` | Merges sub-agent fragments | Claude Code runs it instead of doing assembly itself |
| `ede schema` | Dumps JSON Schema for a node | Claude Code reads it to know expected output shape |
| `ede coverage` | Cross-references keyFiles vs scanned | Quality check Claude Code runs after Node 1 |
| Pydantic models | Define the grammar | Validators enforce it at boundaries |
