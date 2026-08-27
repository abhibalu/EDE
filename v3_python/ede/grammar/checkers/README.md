# Checkers

Checker implementations for the obstacle grammar. **Empty by design** — no
checkers are implemented yet. This directory fixes the layout and the keying
convention so that when checkers land they don't fork per project.

## Keying convention

A checker is bound by `(claim_type, stack, layer)`:

- **`claim_type`** — a key from `../vocabulary.json` (e.g. `ERROR_COLLAPSED`).
  Stack-independent. "These two writes don't commit together" is a statement
  about the domain, not about Prisma.
- **`stack`** — one of `ts-prisma`, `php-laravel`, `py-sqlalchemy`. Only the
  concrete binding varies: `prisma.$transaction(cb)` vs `DB::transaction()` vs a
  `session.begin()` context manager.
- **`layer`** — `evidence` or `inference`, per `../mechanisms.json`.
  - `evidence` checkers prove the code fact. Cheap: they run against a static
    checkout of the baseline commit — no running app, no seeded DB, no fault
    injection. **False-positive measurement lives here.**
  - `inference` checkers prove the harm follows. Often expensive: a `WITNESS`
    needs a running app, a `FAULT_WITNESS` needs an injection seam, a
    `MODEL_CHECK` needs the extracted transition system.

## Expected layout (when implemented)

```
checkers/
  ts-prisma/
    error_collapsed.evidence.*      # AST: .catch handler discards the reason
    not_atomic.evidence.*           # AST: writes not inside prisma.$transaction
    ...
  php-laravel/
    not_atomic.evidence.*           # AST: writes outside DB::transaction()
    ...
  py-sqlalchemy/
    ...
```

Port order follows the mechanism split: implement every `evidence` checker for a
stack before any `inference` checker. The evidence layer is what makes rerun a
measurement, and it is the cheap layer to port.
