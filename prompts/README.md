# `prompts/` — what the LLM runner reads

**Start with [`PIPELINE.md`](PIPELINE.md).** It is the orchestration runbook:
what to run at each stage, in what order, and what to do when validation fails.

| File | Lines | Stage |
|---|---:|---|
| [`PIPELINE.md`](PIPELINE.md) | 62 | The runbook — read this first |
| [`node0.md`](node0.md) | 107 | Recon: structural survey and area-code assignment |
| [`node1.md`](node1.md) | 317 | Event extraction, with the sub-agent ReAct loop |
| [`node2.md`](node2.md) | 338 | Statecharts: states, transitions, gaps |
| [`node3.md`](node3.md) | 295 | KAOS goals, obstacles, requirements, roadmap |
| [`node4.md`](node4.md) | 237 | Compilation into the final spec |

## How these are meant to work

The retry loop is not Python. A node prompt tells the model what to produce; it
writes JSON; it runs `ede validate`; if that reports findings, it reads them,
fixes its own output, and re-validates. That loop *is* the error handling — see
`architecture-decisions.md`, which records the explicit rejection of a Python
retry loop and of a `PipelineRunner` class.

Each prompt embeds the JSON Schema for its stage verbatim, and tells the model
to regenerate it with `ede schema --node N` or `ede schema --fragment nodeN` if
it looks stale. The CLI is the single source of truth for the contract in both
directions.

## Two things to notice when editing them

**The grounding is structural, not polite.** `node1.md` runs an explicit
THOUGHT → ACTION → OBSERVATION loop with a hard rule: *before claiming any
state change exists, you must have an OBSERVATION showing the relevant code. No
observation = no event.* The schema then enforces it — `evidence` has
`min_length=10`, so an ungrounded claim cannot parse. Prompt and schema are
saying the same thing at two different levels, deliberately.

**The "Common Schema Mistakes" sections are empirical.** They are not generic
advice; each entry is a parse failure actually observed in practice
(`hotSpots` as strings rather than objects, `"Medium"` instead of `"MED"`,
`guard` omitted rather than set to `null`). When a new failure mode shows up,
it belongs there.

`node2.md` splits into a grounded Phase A (states are factual claims about
code, each needing evidence) and an analytical Phase B (reasoning over what was
already grounded, no further code reading). Keep that split when editing —
it is what stops analysis from being mistaken for observation.

## Related

- [`docs/cli-and-api.md`](../docs/cli-and-api.md) — the commands these prompts invoke
- [`docs/constraint-rules.md`](../docs/constraint-rules.md) — what `ede validate` will object to
