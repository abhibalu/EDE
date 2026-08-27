# Documentation

Five documents, ~1,100 lines. They answer different questions, and two of them
are historical records rather than living documentation. This page routes you
to the right one.

## Start with the question you have

| If you want to know… | Read | Where exactly |
|---|---|---|
| What command do I run, and what are its flags? | [`cli-and-api.md`](cli-and-api.md) | CLI Commands |
| How do I call this from Python? | [`cli-and-api.md`](cli-and-api.md) | Python API |
| What exactly does the validator check? | [`constraint-rules.md`](constraint-rules.md) | Layer 1–4 tables |
| Why did *this specific* rule fire? | [`constraint-rules.md`](constraint-rules.md) | find the rule ID, e.g. `L2-predecessor-resolves` |
| How does a requirement trace back to a line of code? | [`constraint-rules.md`](constraint-rules.md) | Traceability Chain |
| Where do the ID prefixes come from? | [`constraint-rules.md`](constraint-rules.md) | Registry Propagation |
| Why are there four layers instead of one big validator? | [`formal-theory.md`](formal-theory.md) | §3, §13 |
| Why can't L2 just be a `@model_validator`? | [`formal-theory.md`](formal-theory.md) | §6, §13 |
| Why is L4 different from the other three? | [`formal-theory.md`](formal-theory.md) | §14 |
| What can this system provably *not* express? | [`formal-theory.md`](formal-theory.md) | §15 |
| Why was it built this way, and what was rejected? | [`architecture-decisions.md`](architecture-decisions.md) | Settled Decisions, and the rejections table |
| What is known to be incomplete right now? | [`validator-recon.md`](validator-recon.md) | Summary Table |

## The documents

**[`cli-and-api.md`](cli-and-api.md)** — *reference, current.*
Every command and flag, the Python API, and the four-layer table with severity
levels. The place to look when you need to *use* the thing.

**[`constraint-rules.md`](constraint-rules.md)** — *reference, current.*
The complete rule catalogue: 15 L1 rule families, 20 L2 rule IDs, 11 L3 rule
IDs, and 2 L4 rule IDs with a per-node map of which fields each verifier
probes. Every rule ID that `ede validate` prints appears here. Also carries the
traceability chain (`CodeRef → event → gap → obstacle → goal → requirement →
phase → file index`) and how the Node 0 registry propagates into every
downstream ID.

**[`formal-theory.md`](formal-theory.md)** — *argument, current.* 16 sections.
The claim that the word "grammar" in this repository is technically precise
rather than metaphorical, worked out properly: Pydantic models as a formal
grammar, the layers mapped onto the Chomsky hierarchy, and the proof that the
L1/L2 split is *forced* rather than chosen — a `@model_validator` has
context-free scope, and cross-node reference is context-sensitive.

§14 is the one to read if you only read one: L4 is not a fourth rung on the
ladder. L1–L3 decide membership by inspecting a string, which is what puts them
on the hierarchy at all. L4 asks whether the names in a string *denote*
anything, with the filesystem as the interpretation — so two byte-identical
documents can disagree on it. That is why every verifier takes a `repo_root`,
and why its findings are `WARN` rather than `ERROR`.

**[`architecture-decisions.md`](architecture-decisions.md)** — *record, dated.*
The decisions settled during the V2→V3 migration, kept verbatim, plus a
rejections table giving a reason for each thing deliberately *not* built
(FastAPI, a `PipelineRunner`, a Python retry loop). Later decisions are
appended under "Decisions Since" rather than edited in, so the account of what
was decided when stays honest. Read it before proposing an architectural
change — the answer may already be there, with its reasoning.

**[`validator-recon.md`](validator-recon.md)** — *record, dated.*
A self-audit of the validators against their spec, with a per-node gap matrix.
This is the report that drove the L4 work, so its central gap is now closed.
Others are not: the `validate-fragment` L2 block is still guarded by
`if node == 2`, so Nodes 1 and 3 get no intra-fragment referential checks. The
most useful document here for finding something worth fixing.

## Not in this directory

| Tree | What it holds |
|---|---|
| [`../prompts/`](../prompts/) | The node prompts the LLM runner reads. `PIPELINE.md` is the orchestration runbook; `node0.md`–`node4.md` are the per-node instructions, each embedding the JSON Schema the node must satisfy. |
| [`../research/phase0/`](../research/phase0/) | The obstacle-grammar corpus: 92 hand-annotated obstacles, the analysis scripts, and the pre-registered falsification test. `runs/*/matrix.md` holds the results. |
| [`../examples/`](../examples/) | Sample pipeline artifacts, starting with a pretix Node 0 recon output. |
| [`../ede/grammar/`](../ede/grammar/) | The frozen claim vocabulary and discharge-mechanism tables the research above is built on. Data only — nothing imports it. |

## A note on the two records

`architecture-decisions.md` and `validator-recon.md` are snapshots, not
maintained pages. That is deliberate. A decision log that gets edited whenever
the code changes stops being a record of what was decided and becomes a
description of the present, which the code already provides. Both carry a
status note saying what has changed since they were written.
