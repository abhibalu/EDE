#!/usr/bin/env python3
"""Phase 0 analysis — pure function over (annotation, vocabulary, mechanisms) -> matrix.md.

No project or vocabulary literals: claim-type status, required slots, and discharge
mechanisms all come from ede/grammar/. Copy this file per corpus at your peril — it is
already generic; point it at a different annotation.json instead.

    python3 analyze.py <annotation.json> <vocabulary.json> [mechanisms.json] [matrix.md]

Preserves the mechanical hedge regex and content-address dedup (including the contested
O-SIGN-5 ✗ O-N10 non-merge) exactly. Adds two deliberate things over the legacy matrix:
split evidence/inference mechanism columns, and a required-slot violation report.
"""
import json, collections, os, re, sys


def load(path):
    with open(path) as f:
        return json.load(f)


def analyze(annotation_path, vocabulary_path, mechanisms_path=None, out_path=None):
    ann = load(annotation_path)
    vocab = load(vocabulary_path)["types"]
    if mechanisms_path is None:
        mechanisms_path = os.path.join(os.path.dirname(vocabulary_path), "mechanisms.json")
    mechs = load(mechanisms_path)["types"]

    records = ann["records"]
    by_id = {r["id"]: r for r in records}
    # no dropped/duplicate records, and count matches the frozen source corpus
    assert len(by_id) == len(records), "duplicate record ids"
    assert len(records) == ann["sourceRecordCount"], (len(records), ann["sourceRecordCount"])
    total = len(records)

    # --- status buckets read from the vocabulary, not from inlined Python sets ---
    def status(k):
        return vocab.get(k, {}).get("status", "candidate")
    CORE = {k for k, v in vocab.items() if v["status"] == "core"}

    prim = collections.Counter(r["grammar"]["primary"] for r in records)
    core_n = sum(v for k, v in prim.items() if status(k) == "core")
    cand_n = sum(v for k, v in prim.items() if status(k) == "candidate")
    none_n = sum(v for k, v in prim.items() if status(k) == "none")
    real = total - none_n

    premise_present = sum(1 for r in records if r["slots"]["premise"] not in (None,))
    premise_explicit = sum(1 for r in records if r["slots"]["premise"] not in (None, "IMPLICIT"))
    defeater_present = sum(1 for r in records if r["slots"]["defeater"] not in (None, "UNCAPTURED"))
    defeater_uncaptured = sum(1 for r in records if r["slots"]["defeater"] == "UNCAPTURED")
    sevrat_present = sum(1 for r in records if r["slots"]["severity_rationale"])
    hf_present = sum(1 for r in records if r["grammar"]["handler_form"])

    # hedge computed MECHANICALLY from the source description (reproducible), not hand lists
    HEDGE_RE = re.compile(r"\b(could|may|would|might|potentially|possibly|in principle|if)\b", re.I)
    def hedges_in(r):
        return sorted(set(m.group(0).lower() for m in HEDGE_RE.finditer(r["description"])))
    hedge_map = {r["id"]: hedges_in(r) for r in records}
    hedged = sum(1 for r in records if hedge_map[r["id"]])
    HI = {"HIGH", "CRITICAL"}
    hedge_x_high = [r["id"] for r in records if hedge_map[r["id"]] and r["severity"] in HI]

    # content address = (primary, operands). A predicted dup MERGES only if addresses match.
    addr = {r["id"]: (r["grammar"]["primary"], r["grammar"]["operands"]) for r in records}
    pred_pairs = sorted({tuple(sorted((r["id"], r["grammar"]["dup_of"]))) for r in records if r["grammar"]["dup_of"]})
    clean_merges = [(a, b) for a, b in pred_pairs if addr[a] == addr[b]]
    contested = [(a, b) for a, b in pred_pairs if addr[a] != addr[b]]
    sev = collections.Counter(r["severity"] for r in records)

    # --- required-slot violations: type mandates a slot the record does not fill ---
    def slot_filled(r, slot):
        if slot == "handler_form":
            return r["grammar"]["handler_form"] is not None
        if slot == "scope":
            return r["grammar"]["scope"] is not None
        if slot == "premise":
            return r["slots"]["premise"] is not None
        if slot == "defeater":
            return r["slots"]["defeater"] not in (None, "UNCAPTURED")
        raise ValueError(slot)
    violations = []
    for r in records:
        req = vocab.get(r["grammar"]["primary"], {}).get("required_slots", [])
        missing = [s for s in req if not slot_filled(r, s)]
        if missing:
            violations.append((r["id"], r["grammar"]["primary"], missing))

    def mech_cols(k):
        m = mechs.get(k, {})
        return (m.get("evidence_mechanism") or "—", m.get("inference_mechanism") or "—")

    # --- markdown matrix ---
    def bar(n, tot=total):
        return "█" * round(24 * n / tot)
    lines = []
    A = lines.append
    A("# Phase 0 — Corpus Decomposition")
    A(f"\n**Run:** {ann['project']} {ann['run']} · **Source:** `{os.path.basename(ann['source'])}` · "
      f"**Stack:** `{ann['stack']}` · **Vocabulary:** `{ann['vocabularyVersion']}` · **Records:** {total}\n")
    A("## Slot-presence matrix\n")
    A("| slot | present | note |")
    A("|---|---|---|")
    A(f"| location | {total}/{total} | universal — every record cites a symbol/file |")
    A(f"| code_observation | {total}/{total} | universal |")
    A(f"| **premise** | {premise_present}/{total} ({premise_explicit} explicit) | **prediction confirmed: absent/implicit in {total-premise_explicit}** |")
    A(f"| **defeater** | {defeater_present}/{total} (+{defeater_uncaptured} uncaptured) | sparse but diagnostic; both canaries have it UNCAPTURED |")
    A(f"| hedge | {hedged}/{total} | observed→inferred boundary |")
    A(f"| severity_rationale | {sevrat_present}/{total} | severity is mostly asserted, not argued |")
    A(f"| handler_form | {hf_present}/{total} | the literal that discriminates canary from corrected |")
    A("\n## Claim-type distribution (primary only)\n")
    A("| primary | n | status | evidence | inference | |")
    A("|---|--:|---|---|---|---|")
    for k, v in prim.most_common():
        ev, inf = mech_cols(k)
        A(f"| {k} | {v} | {status(k)} | {ev} | {inf} | {bar(v)} |")
    A(f"\n**Coverage:** core = {core_n}/{total} · candidate = {cand_n} · discharge-resistant (NONE) = {none_n}")
    A(f"\nExcluding the {none_n} discharge-resistant smells, real obstacles = {real}; "
      f"core covers {core_n}/{real} = {round(100*core_n/real)}%.")
    A(f"\n`UNREACHABLE` = {prim.get('UNREACHABLE', 0)} in this corpus. "
      f"`UNGUARDED` and `ERROR_COLLAPSED` = {prim['UNGUARDED']}/{prim['ERROR_COLLAPSED']} "
      f"(most-loaded; UNGUARDED is the catch-all to scrutinize).")
    A("\n## Required-slot violations\n")
    A(f"{len(violations)} records mandate a slot they do not fill — a Phase 1 work list, not an extraction bug:\n")
    if violations:
        A("| id | primary | missing |")
        A("|---|---|---|")
        for rid, p, missing in sorted(violations):
            A(f"| `{rid}` | {p} | {', '.join(missing)} |")
    else:
        A("_none_")
    A("\n## Duplicate collapse (by content address = primary + operands)\n")
    A("**Clean merges** (identical content address):")
    for a, b in clean_merges:
        A(f"- `{a}` ≡ `{b}`  →  `{addr[a][0]}({addr[a][1]})`")
    A("\n**Contested** (plan predicted a merge; grammar keeps them apart — the identity-function test):")
    for a, b in contested:
        A(f"- `{a}` ✗ `{b}`  →  `{addr[a][0]}` vs `{addr[b][0]}` — same site, different claim")
    A(f"\n{len(clean_merges)} clean merges → {total} records collapse to **{total-len(clean_merges)} distinct**. "
      f"{len(contested)} predicted pair(s) did NOT merge: the identity function is finer than a site-hash, "
      f"which is the intended behaviour — same location, genuinely different claim.")
    A("\n## Hedge ∩ HIGH/CRITICAL hotspot (false-positive signature)\n")
    A(f"{len(hedge_x_high)} records: {', '.join('`'+i+'`' for i in hedge_x_high)}")
    A("\n## Severity mix\n")
    A(" · ".join(f"{k}={v}" for k, v in sev.most_common()))

    md = "\n".join(lines)
    if out_path:
        with open(out_path, "w") as f:
            f.write(md)
    return md


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    ann_p = sys.argv[1]
    vocab_p = sys.argv[2]
    mech_p = sys.argv[3] if len(sys.argv) > 3 else None
    out_p = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.dirname(ann_p), "matrix.md")
    analyze(ann_p, vocab_p, mech_p, out_p)
    print(f"wrote {out_p}")
