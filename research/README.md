# `research/` — empirical validation of the obstacle grammar

The question here is not whether the pipeline produces well-formed output —
the validation layers settle that. It is whether the findings it produces can
be **discharged**: stated precisely enough that something mechanical could
confirm or refute them.

Phase 0 tests that against real output: all 92 obstacles from a Documenso run,
hand-annotated under the frozen vocabulary in
[`ede/grammar/`](../ede/grammar/README.md).

**The results are in [`phase0/runs/documenso-2026-05-27/matrix.md`](phase0/runs/documenso-2026-05-27/matrix.md).**

## Findings

| | |
|---|---|
| Core-type coverage | 66/76 real obstacles (**87%**), excluding 16 discharge-resistant records |
| Duplicate collapse | 92 records → **89** distinct, via 3 clean merges on content address |
| Contested merge | 1 predicted merge correctly **refused** — same site, genuinely different claim |
| Required-slot violations | 9 records mandate a slot they do not fill — a work list, not an extraction bug |
| `premise` present | 8/92 — confirming the pre-registered prediction that it is normally implicit |
| False-positive signature | 13 records match `hedge ∩ HIGH/CRITICAL` |
| Falsification test | **PASS** |

The contested non-merge is the interesting one. The content address is
`(claim_type, site, operands)`, which is deliberately finer than a site hash:
two findings at the same location that make different claims must not collapse
into one. The test predicted a merge, the grammar refused it, and the refusal
was correct.

## What each file is

Inputs and hand-authored material:

| File | Role |
|---|---|
| `phase0/corpus.json` | The raw obstacles as the pipeline emitted them |
| `phase0/phase0_build.py` | Holds the **hand-authored annotation** of all 92 records. Keep it — it is the source of truth, not a script that can be regenerated |

Current pipeline:

| File | Role |
|---|---|
| `phase0/build_annotation.py` | One-off: extracts the annotation from `phase0_build.py` verbatim into `runs/…/annotation.json` |
| `phase0/analyze.py` | `(annotation, vocabulary, mechanisms) → matrix.md`. Generic — no project or vocabulary literals |
| `phase0/runs/documenso-2026-05-27/` | The current annotation and results |

Follow-up analyses:

| File | Role |
|---|---|
| `phase0/phase0_analysis.py` | Two adversarial self-tests → `phase0-followups.json` |
| `phase0/phase1_falsification.py` | The pre-registered falsification test → `phase1-falsification.json` |

Superseded but retained:

| File | Why kept |
|---|---|
| `phase0/phase0-annotation.json`, `phase0/phase0-matrix.md` | Legacy outputs of `phase0_build.py`. `phase0_analysis.py` still reads the annotation |

## Reproducing the results

```bash
cd research/phase0
python3 analyze.py runs/documenso-2026-05-27/annotation.json \
  ../../ede/grammar/vocabulary.json ../../ede/grammar/mechanisms.json \
  runs/documenso-2026-05-27/matrix.md
```

This rewrites `matrix.md` **byte-identically**. The reported numbers are
re-derived from the annotation rather than transcribed, so a `git diff` after
running it should be empty.

```bash
python3 phase1_falsification.py   # expect: RESULT: PASS
```

## Why the falsification test matters

It encodes the same finding twice — once as the pipeline originally emitted it,
once corrected against source — and passes **only if the two differ in a
load-bearing field rather than merely in prose**. A grammar that could not tell
a wrong finding from its corrected form would be decorative.

It passes: `premise`, `observable`, and `discharge_condition` differ, while
`claim_type`, `site`, `operands`, and `handler_form` are identical, and both
share a content address. The grammar treats them as one defect described wrongly
and then rightly — which is the intended behaviour, and the discharge is what
adjudicates which description is true.

The result forced a schema change: `observable` had to be promoted to its own
load-bearing slot.

## Status

Phase 0 is complete. Phase 1 is the required-slot work list above, and the
checker implementations that `ede/grammar/checkers/` is keyed for. No checkers
exist yet, so nothing here runs against a codebase automatically.
