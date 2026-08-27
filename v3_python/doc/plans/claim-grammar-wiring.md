# Plan: Wire the claim grammar into the EDE runtime (single-record migration, Phase A)

**Status:** 🟡 Ready to implement · **Created:** 2026-08-27
**Scope decision:** Phase A detailed for execution; Phases B–E are a sequenced roadmap, each re-approved when reached.

## Context

EDE's pipeline has a **formal envelope, lawless payload** shape: structured IDs/enums/`CodeRef`
wrap free-text `str` fields (`trigger`, `stateChange`, `representation`, `guard`, gap/obstacle
`description` — all `str, min_length=1`; `guard` is unconstrained `str | None`). Verified against
source: `ede/fragments.py`, `ede/nodes/node{1,2,3}.py`. Every drift and hallucination the project
has diagnosed lives inside those free-text fields, because that is the only place it *can* live —
the L1/L2/L3 validators can't see into a string. The dedup keys prove it literally: obstacles key
on `description::evidence` (`assemblers.py:294`) — free prose — so paraphrase drift breaks identity
and makes run-to-run comparison impossible.

The grammar that fixes this already exists and is **validated**: `ede/grammar/vocabulary.json` (20
claim types, slots, `vocabularyVersion`) was tested against 92 real Documenso records in
`doc/phase0/`. But it is **not wired into the runtime** — only `doc/phase0/analyze.py` reads it. This
plan wires it in, starting where the payoff is highest and the vocabulary is already proven: **gap
and obstacle emission**.

**Outcome:** Node 2/3 emit gaps/obstacles as generic `{claim_type, slots, evidence}` claims validated
against the versioned vocabulary; `description` becomes a deterministically *rendered* view, never
authored by the LLM; identity becomes content-addressed (paraphrase-invariant); and the runtime
grammar-wiring built here serves every later phase.

## The reframe (why this shape, not typed per-field Pydantic)

This is **point 1** (one record, `kind` discriminator, kind determines required slots) applied at the
schema layer. The central fork — generic `{claim_type, slots}` validated against `vocabulary.json` at
runtime, vs. typed `StrEnum` Pydantic fields — resolves to **generic**, because:

- The proven mechanism is already generic: `doc/phase0/analyze.py:22-27,64` validates the 92-record
  annotation as `{primary, operands, slots}` against `vocabulary.json`-as-data. Records in
  `annotation.json` already have this shape. We are wiring in a *working* validator, not inventing one.
- With typed fields, the freeze point is the Pydantic source, and `vocabularyVersion` degrades to a
  convention policed by a parity test. With generic slots, the versioned JSON **is** what validates —
  the version is load-bearing, which is the cross-corpus comparability thesis.
- Cost (accepted): we trade Pydantic's static per-field typing for a runtime slot validator, which
  **must be as strict** as the typed fields it replaces (enum membership, `required_slots`, arity,
  value shape) or L1 silently weakens. Mitigation: port `analyze.py`'s checks and gate on the frozen
  92-record regression harness.

Scope guard: generic is adopted **for Phase A claim records (gaps/obstacles) only**. Events/states/
transitions stay untouched typed-prose until Phase B, which decides propagation after watching A.

## Phase A — detailed (the executable, independently-verifiable slice)

Wire the grammar against the **existing 20 gap types** — zero new vocabulary authored — so a wiring
bug and a vocabulary-design mistake can never be confused in the first failing run.

1. **Runtime grammar loader + validator.** New `ede/grammar/__init__.py` (loader) + `ede/claims.py`:
   - Load the versioned `vocabulary.json`; expose `claim_types`, `required_slots`, `operand_arity`.
   - `Claim` Pydantic model: `{kind, claim_type: str, slots: dict, evidence: str(min_len 10),
     code_location: CodeRef, severity: Severity, note: str | None}`.
   - `SlotValidator`: `claim_type ∈ vocabulary[version]`; required slots present; arity/enum-membership
     honored; `UNCLASSIFIED` requires only `evidence` and forbids junk slots. Port the check logic
     from `doc/phase0/analyze.py` (`required_slots`, status buckets) — do not re-derive it.
   - `content_address(claim_type, slots)` helper — reuse `analyze.py:64` semantics exactly, including
     the **ordered-tuple** operand comparison that keeps `O-SIGN-5 ✗ O-N10` from merging
     (`analyze.py:66-67,135-137`). Sort operands only for commutative types (driven off vocabulary),
     never blindly.

2. **Fragment + node schema changes** (`ede/fragments.py`, `ede/nodes/node2.py`, `node3.py`):
   - `GapFragment` / `Gap`: drop `description: str`; carry `claim_type`, `slots`, keep `evidence`,
     `code_location`, `severity`; add `note`.
   - `ObstacleFragment` / `NewObstacle` / `ConfirmedObstacle`: same move (`claim_type` + `slots`,
     description dropped).
   - **Consequence-half cut (decided here, not in the diff):** ship **pattern-slotting only**. The
     frozen 20 types cover the *pattern* side; consequence classes and derived severity are *new*
     vocabulary and are **deferred** — severity stays LLM-authored, consequence rides in the
     quarantined `note` for now. Keeps Phase A's new-design surface at zero.

3. **Assembler** (`ede/assemblers.py`): dedup gaps/obstacles by `content_address(claim_type, slots)`
   instead of `description::evidence` (`:294`) and the gap path; description copy line (`:228`)
   removed. Gap-summary/truncation/symmetry logic untouched.

4. **Rendered description** (`ede/renderer.py`): deterministic `(claim_type, slots) → text`. The
   renderer becomes the single home of the human-readable "rendered view."

5. **Prompt = generated from the vocabulary, not hand-maintained** (`prompts/node2.md`, `node3.md`):
   the allowed `claim_type`s + `required_slots` the sub-agent sees are **rendered from
   `vocabulary.json`** (the same versioned source the validator reads), and the fragment JSON-schema
   block is regenerated via the existing `ede schema --fragment` command (`cli.py:187-198`). This
   removes a standing drift surface (stale hand-edited schema) and one of the "4 coordinated edits."
   The LLM's remaining freedom is judgment-only: select `claim_type`, fill grep-anchored slots, or
   signal a gap via `UNCLASSIFIED` + evidence. Prose goes only in `note`.

6. **Run identity, formalized now** (before any table exists): standardize the emitted artifact
   header to `(project, run_date, vocabularyVersion, pipelineVersion)`. Introduce a single
   `PIPELINE_VERSION` constant (today hardcoded ≥6 places: `primitives.py:128,136`,
   `assemblers.py:173,262`, prompts, `conftest.py:39`) and **bump `0.1.0 → 0.2.0`** so old prose-schema
   JSON fails fast against the new models.

7. **`falsifiedIf` on `Requirement`** (`ede/nodes/node3.py:74`) — add now while the count is 4
   (`conftest.py:368-393`). `FalsifiedIf{check: CheckKind, target: CodeRef, predicate: str}` where
   `CheckKind` mirrors `mechanisms.json` `evidence_enum` (`AST | STATIC_QUERY | RUNTIME | MODEL_CHECK`)
   — a requirement without a mechanically checkable done-condition is the same disease as an absence
   claim without scope.

8. **UNCLASSIFIED harvest signal** (`ede/cli.py`): extend the `coverage` command to report the
   per-run `UNCLASSIFIED` rate. A high rate means the *vocabulary* is wrong, not the run; it is the
   harvest queue for the next `vocabularyVersion`.

9. **Dedup cutover declared discontinuous:** slot-ification changes identity semantics, so the
   Documenso prose baseline is **incomparable** with post-slot runs. Accepted and explicit: bump
   `vocabularyVersion`, freeze legacy runs as legacy, restart comparisons. No dual-keying (it would
   preserve comparability of numbers already known to be drift-contaminated).

**Critical files:** `ede/grammar/__init__.py` (new), `ede/claims.py` (new), `ede/fragments.py`,
`ede/nodes/node2.py`, `ede/nodes/node3.py`, `ede/assemblers.py`, `ede/renderer.py`, `ede/cli.py`,
`ede/primitives.py` (`PIPELINE_VERSION`, `content_address`), `prompts/node2.md`, `prompts/node3.md`,
`ede/grammar/vocabulary.json` (version stamp), `tests/conftest.py` + `tests/test_assemblers.py`
(fixtures → claim shape; dedup tests → content-address).

## Verification (exit criterion)

- **Regression harness (already owned):** `SlotValidator` validates all 92 frozen records in
  `doc/phase0/runs/documenso-2026-05-27/annotation.json`; `analyze.py` matrix stays byte-identical.
  This proves the wiring on trusted types with zero new vocabulary.
- **Drift test (the strongest version):** re-emit Node 2 gaps for Documenso and assert gap identity is
  content-addressed and **paraphrase-invariant** vs. the frozen annotation — run on the exact field
  where drift was worst. This is Phase A's go/no-go.
- **Unit:** `pytest` green after fixture updates; new tests for `SlotValidator`, `content_address`
  (including the `O-SIGN-5 ✗ O-N10` non-merge), and `FalsifiedIf` required-slot.

## Roadmap (sequenced, each re-approved when reached — not detailed here)

- **Phase B — structural-field vocabularies.** Author `trigger` / `stateChange` / `representation` /
  `guard` as **new** slot vocabularies on the proven generic wiring. Candidate shapes (from the design
  pass): `StateDelta{field, from_value, to_value}` with `ABSENT` sentinels; `StateRepr{kind, field,
  clauses}` where `clauses` reuse a `GuardClause{field, op, value}` conjunction — this makes a state
  *constructible* (needed by Phase D) and handles boolean/nullable states a single `field` cannot;
  `guard` = flat AND-list of clauses (z3-consumable, no expression language, no `raw` prose backdoor).
  Events move from `name::file` to content-address here; the split-brain is declared and tolerable
  until then (names drift far less than descriptions).
- **Phase C — two-table DuckDB.** Assembler **dual-writes** JSON + `claim`/`edge` tables; DuckDB is
  **read-only, off the write-critical path**; JSON stays the wire format. `run` table keyed
  `(project, date, vocabularyVersion, pipelineVersion)` — comparability becomes a join constraint. The
  `edge` table externalizes exactly the links `constraints.py` already enumerates. L2/L3 reimplemented
  as SQL views (`L3-no-dead-ends`, `L3-critical-needs-must`, `L3-req-in-roadmap` are each one-line
  joins). **`constraints.py` kept only as a differential oracle** until the views match it on one full
  run, then deleted — dual authority must not persist past one validated run. `claim.status`
  (extracted/verified/refuted/stale) added here for the fix workflow (point 3).
- **Phase D — statechart test-gen (new L4-executable).** From transitions: coverage tests, negative
  complement tests, impossible-combination invariants via Hypothesis `RuleBasedStateMachine`, guard-
  boundary tests. Runs against the *target* codebase; a transition that can't render to a runnable
  test is thereby flagged under-specified. Executing beats an adversarial sub-agent because it runs
  rather than argues. This is also the original obstacle plan's discharge harness. Depends on Phase B's
  constructible `StateRepr`. Adds a `hypothesis` dev-dep.
- **Phase E — runner manifests.** Last; orchestration is the part that already works.

## Risks

- **R1 — runtime validator weaker than the typed fields it replaces** (L1 silently erodes). Mitigate:
  port `analyze.py` checks verbatim; gate on the 92-record regression harness; property-test the
  validator against known-good and known-bad slot sets.
- **R2 — version boundary.** Clean, **no data migration** — the old Documenso artifact is a frozen
  *input* to `analyze.py`, never re-parsed by new models. `PIPELINE_VERSION` bump via one constant;
  vocabulary version stamped in the artifact header.
- **R3 — closed-vocab lossiness (first Firefly III / PHP run).** `UNCLASSIFIED` absorbs it *iff*:
  evidence-gated (not prose), excluded from content-address dedup, `note` quarantined, and the
  coverage report surfaces the `UNCLASSIFIED` rate as the harvest signal.
- **R4 — dedup discontinuity.** Declared, legacy frozen, comparisons restart (see A.9).
- **R5 — test blast radius (broad, shallow).** Fixtures + renderer updates across `tests/conftest.py`,
  `test_assemblers.py`, `test_schema.py`, `test_renderer.py`; the renderer *becomes* the rendered-view
  home, so several "fixes" are the feature.

## Implementation order (suggested first commits)

1. `ede/claims.py` + `ede/grammar/__init__.py` (loader, `Claim`, `SlotValidator`, `content_address`) +
   tests against the 92 frozen records — **land and green before touching any node schema.**
2. `PIPELINE_VERSION` constant + `0.2.0` bump (mechanical, isolated).
3. Fragment/node schema changes for gaps/obstacles + assembler content-address dedup + renderer.
4. `FalsifiedIf` on `Requirement`.
5. Prompt generation from vocabulary; `coverage` UNCLASSIFIED rate.
6. Fixture/test updates; run the drift test as the exit gate.
