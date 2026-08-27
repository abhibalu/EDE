#!/usr/bin/env python3
"""One-off: extract the R annotation dict from phase0_build.py verbatim and emit
runs/documenso-2026-05-27/annotation.json in the self-contained shape analyze.py
consumes. No re-annotation — same records, same values. Derived fields (mechanism,
hedge_mechanical) are intentionally NOT stored; analyze.py computes them from
mechanisms.json and the raw description."""
import json, os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))

# load R + CALIBRATION from the original script without duplicating the literal
spec = importlib.util.spec_from_file_location("phase0_build", os.path.join(HERE, "phase0_build.py"))
pb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pb)  # side effects write phase0-annotation.json/matrix.md into HERE; harmless/idempotent
R, CALIBRATION = pb.R, pb.CALIBRATION

corpus = {o["id"]: o for o in json.load(open(os.path.join(HERE, "corpus.json")))}

records = []
for rid, (sev, primary, operands, hf, scope, premise, defeater, hedge, sevrat, secs, flags, dup) in R.items():
    records.append({
        "id": rid,
        "severity": sev,
        "gapSource": corpus[rid]["gapSource"],
        "description": corpus[rid]["description"],
        "calibration": rid in CALIBRATION,
        "grammar": {
            "primary": primary,
            "operands": operands,
            "handler_form": hf,
            "scope": scope,
            "secondaries": secs,
            "dup_of": dup,
        },
        "slots": {
            "premise": premise,
            "defeater": defeater,
            "hedge": hedge,               # hand-marked salient hedges (kept for provenance)
            "severity_rationale": sevrat,
        },
        "flags": flags,
    })

out = {
    "pipelineVersion": "0.1.0",
    "phase": 0,
    "project": "documenso",
    "run": "2026-05-27",
    "stack": "ts-prisma",
    "schemaVersion": "grammar-v0-slots7",
    "vocabularyVersion": "v0-2026-05-27",
    "source": "docs/pipeline/runs/2026-05-27/03-goals.json",
    "sourceRecordCount": 92,
    "records": records,
}

dest_dir = os.path.join(HERE, "runs", "documenso-2026-05-27")
os.makedirs(dest_dir, exist_ok=True)
json.dump(out, open(os.path.join(dest_dir, "annotation.json"), "w"), indent=1)
print(f"wrote {len(records)} records -> runs/documenso-2026-05-27/annotation.json")
