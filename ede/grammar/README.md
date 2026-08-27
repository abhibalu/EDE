# `ede/grammar/` — the obstacle claim vocabulary

Data, not code. Nothing in the `ede` package imports this directory, and no
validation layer consults it. It is versioned reference material for a
question the pipeline currently answers in prose.

## The problem it addresses

The four validation layers constrain the *shape* of what the pipeline emits.
None of them says anything about whether an individual finding is **true**.
Node 3 produces obstacles as free text, so "is this real?" stays a judgement
call — and judgement calls cannot be counted, deduplicated, or measured for
false-positive rate.

## Contents

| File | What it defines |
|---|---|
| `vocabulary.json` | 20 claim types (11 `core`, 8 `candidate`, `NONE`), each with operand arity, named operands, and required slots |
| `mechanisms.json` | How each claim type is discharged, split into evidence and inference layers, with per-stack bindings |
| `checkers/` | Empty by design — [see its README](checkers/README.md) |

## How to read a claim type

```json
"ERROR_COLLAPSED": {
  "status": "core",
  "operand_arity": 2,
  "operands": ["site", "causes"],
  "required_slots": ["handler_form"],
  "description": "distinct failure causes collapse to one opaque value..."
}
```

Required slots are not stylistic. Each is the field that discriminates a true
claim from a false one, and the `description` says why. `ERROR_COLLAPSED`
requires `handler_form` because the literal form is the whole discriminator —
`.catch(null)` is a no-op, `.catch(() => null)` is a genuine swallow, and only
the second is a defect. The types that quantify over "nowhere" (`NO_WRITER`,
`UNREACHABLE`, `NO_LIFECYCLE_ENFORCEMENT`) require `scope`, because an unscoped
universal claim cannot be checked at all.

`NONE` is a real member, not a fallback: it marks a finding as
discharge-resistant. Membership is a mechanical test — can a discharge be
stated? — rather than a verdict on whether the finding is interesting.

## The two-layer discharge model

`mechanisms.json` splits what a discharge must prove:

- **`evidence_mechanism`** proves the *code fact*. Cheap and replayable against
  a baseline commit — no running app, no seeded database, no fault injection.
  One of `AST`, `STATIC_QUERY`, `RUNTIME`, `MODEL_CHECK`.
- **`inference_mechanism`** proves the *harm follows*. Often needs a runtime.
  One of `WITNESS`, `FAULT_WITNESS`, `STATIC_QUERY`, `MODEL_CHECK`,
  `DIFFERENTIAL`, `NONE`.

Keeping them apart puts false-positive measurement at the evidence layer, which
is what makes a rerun a measurement rather than a repeat of an opinion.

Claim types are stack-independent; only the concrete binding varies, keyed
under `stacks` for `ts-prisma`, `php-laravel`, and `py-sqlalchemy`. The
`candidate` types carry `null` mechanisms until the falsification test admits
them.

## Versioning

`vocabularyVersion` is frozen so coverage numbers stay comparable across
corpora. Bump it on any change to a type set or a `required_slots` list —
otherwise a coverage figure from one run cannot be compared with another.

## Related

- [`research/`](../../research/README.md) — the 92-obstacle corpus this vocabulary was validated against, and the falsification test
- Root [`README.md`](../../README.md) — how this relates to the pipeline's own formal grammar
