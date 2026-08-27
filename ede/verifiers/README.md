# `ede/verifiers/` — L4, claims vs. disk

`constraints.py` validates that the JSON is internally consistent. This package
validates that it is *about the repository*.

The distinction is the reason these live apart. L1 through L3 can all pass on an
artifact whose every file reference was invented, because nothing in the
document contradicts anything else in the document. A fluent, coherent,
entirely fabricated set of references is exactly what those layers are built to
certify. Only a check that leaves the document can catch it.

## Contents

| File | Lines | What it holds |
|---|---:|---|
| `paths.py` | 274 | Five verifiers plus the shared `_check` helper |
| `__init__.py` | 27 | Re-exports |

| Verifier | Node | Probes |
|---|---|---|
| `verify_recon_paths` | 0 | registry area dirs, architecture dirs, `schemaLocation`, service `configLocation`, dispatch dirs, `keyFiles` |
| `verify_events_paths` | 1 | scan area dirs, `filesScanned`, `filesSkipped`, event locations, hot-spot locations |
| `verify_aggregates_paths` | 2 | aggregate `keyFiles`, state locations, transition `codeLocation`, gap `codeLocation` |
| `verify_spec_paths` | 4 | `fileIndex` entries |
| `verify_fragment_paths` | 1,2,3 | the same fields at the sub-agent boundary |

Node 3 has no verifier because it has no path-typed fields. That is a property
of its schema, not a gap.

## Two design points worth knowing

**Every verifier takes `repo_root`.** It has to: the predicate "this path
exists" is meaningless without an interpretation, and the filesystem is the
interpretation. The same artifact checked against two commits can legitimately
produce different findings. No other layer needs such a parameter, because no
other layer looks outside the document.

**Findings are `WARN` and the command exits 0.** This reads as a severity
choice and is really a soundness one. An L2 violation is a proof about the
document that does not expire; a missing path is an observation about the world
at one moment, and a file may have been moved after a correct extraction.
Promoting it to a hard error would claim a certainty the check cannot supply.

`verify_fragment_paths` is the highest-value probe: it catches an invented path
while it can still be attributed to the sub-agent that produced it, before
assembly folds it into the node output.

## Related

- `ede verify-paths --repo <target>` — the CLI entry point
- `ede validate-fragment --repo <target>` — fragment-level probing
- [`docs/formal-theory.md`](../../docs/formal-theory.md) §14 — why L4 sits outside the formal-language framing entirely
- [`docs/constraint-rules.md`](../../docs/constraint-rules.md) — Layer 4 rule table
