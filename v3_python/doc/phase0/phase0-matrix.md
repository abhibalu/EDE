# Phase 0 — Corpus Decomposition

**Run:** documenso 2026-05-27 · **Source:** `03-goals.json` · **Records:** 92 (77 confirmed + 15 new)

## Slot-presence matrix

| slot | present | note |
|---|---|---|
| location | 92/92 | universal — every record cites a symbol/file |
| code_observation | 92/92 | universal |
| **premise** | 8/92 (6 explicit) | **prediction confirmed: absent/implicit in 86** |
| **defeater** | 4/92 (+2 uncaptured) | sparse but diagnostic; both canaries have it UNCAPTURED |
| hedge | 21/92 | observed→inferred boundary |
| severity_rationale | 10/92 | severity is mostly asserted, not argued |
| handler_form | 33/92 | the literal that discriminates canary from corrected |

## Claim-type distribution (primary only)

| primary | n | mechanism | |
|---|--:|---|---|
| NONE | 16 | — | ████ |
| ERROR_COLLAPSED | 13 | WITNESS | ███ |
| UNGUARDED | 13 | STATIC_QUERY | ███ |
| NO_LIFECYCLE_ENFORCEMENT | 7 | WITNESS | ██ |
| NO_AUDIT | 6 | WITNESS | ██ |
| OUTSIDE_TX | 6 | FAULT_WITNESS | ██ |
| TOCTOU | 6 | MODEL_CHECK | ██ |
| NOT_ATOMIC | 5 | FAULT_WITNESS | █ |
| UNBOUNDED | 4 | WITNESS | █ |
| NO_WRITER | 3 | STATIC_QUERY | █ |
| MISSING_OWNERSHIP_CHECK | 3 | WITNESS | █ |
| MISSING_FILTER | 2 | STATIC_QUERY | █ |
| MISSING_WRITE | 2 | FAULT_WITNESS | █ |
| MUTABLE_CAPTURE_ACROSS_RETRY | 1 | candidate |  |
| FANOUT_SHORT_CIRCUIT | 1 | candidate |  |
| DIFFERENTIAL | 1 | DIFFERENTIAL |  |
| ORPHAN_RESOURCE | 1 | candidate |  |
| STALE_CREDENTIAL | 1 | candidate |  |
| PII_IN_LOGS | 1 | candidate |  |

**Coverage:** core-11 types = 66/92 · plan extras (MISSING_FILTER, DIFFERENTIAL) = 3 · new candidates = 7 · discharge-resistant (NONE) = 16

Excluding the 16 discharge-resistant smells, real obstacles = 76; core-11 covers 66/76 = 87%.

`UNREACHABLE` = 0 in this corpus. `UNGUARDED` and `ERROR_COLLAPSED` = 13/13 (most-loaded; UNGUARDED is the catch-all to scrutinize).

## Duplicate collapse (by content address = primary + operands)

**Clean merges** (identical content address):
- `O-ENV-2` ≡ `O-ORG-11`  →  `MISSING_FILTER(deleteMany,statusClause)`
- `O-N6` ≡ `O-TRPC-8`  →  `NO_LIFECYCLE_ENFORCEMENT(ApiToken.expires)`
- `O-ORG-12` ≡ `O-TRPC-3`  →  `MISSING_WRITE(demotePreviousOwner)`

**Contested** (plan predicted a merge; grammar keeps them apart — the identity-function test):
- `O-N10` ✗ `O-SIGN-5`  →  `UNGUARDED` vs `NONE` — same site, different claim

3 clean merges → 92 records collapse to **89 distinct**. 1 predicted pair(s) did NOT merge: the identity function is finer than a site-hash, which is the intended behaviour — same location, genuinely different claim.

## Hedge ∩ HIGH/CRITICAL hotspot (false-positive signature)

13 records: `O-AUTH-6`, `O-AUTH-13`, `O-ENV-5`, `O-JOB-5`, `O-ORG-3`, `O-ORG-12`, `O-PAPI-8`, `O-PAPI-10`, `O-SIGN-7`, `O-TRPC-3`, `O-TRPC-8`, `O-N3`, `O-N6`

## Severity mix

HIGH=35 · MED=34 · LOW=16 · CRITICAL=7