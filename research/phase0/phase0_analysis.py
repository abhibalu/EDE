#!/usr/bin/env python3
"""Follow-up analyses on the Phase 0 annotation:
  (2) Does UNGUARDED over-index on absent premise? (test the level-error hypothesis)
  (3) Re-test the 16 discharge-resistant 'smells' by ATTEMPTING to state a discharge."""
import json, os, collections
here=os.path.dirname(__file__)
recs={r["id"]:r for r in json.load(open(os.path.join(here,"phase0-annotation.json")))["records"]}

# ---- (2) UNGUARDED level-error test ----
def premise_absent(r): return r["slots"]["premise"] is None
def hf_present(r): return bool(r["grammar"]["handler_form"])
N=len(recs)
base_premise_absent = sum(premise_absent(r) for r in recs.values())
base_hf = sum(hf_present(r) for r in recs.values())
ug=[r for r in recs.values() if r["grammar"]["primary"]=="UNGUARDED"]
ec=[r for r in recs.values() if r["grammar"]["primary"]=="ERROR_COLLAPSED"]
print("=== (2) UNGUARDED level-error test ===")
print(f"corpus baseline: premise-absent {base_premise_absent}/{N}={base_premise_absent/N:.0%} · handler_form {base_hf}/{N}={base_hf/N:.0%}")
print(f"UNGUARDED (n={len(ug)}): premise-absent {sum(premise_absent(r) for r in ug)}/{len(ug)} · handler_form {sum(hf_present(r) for r in ug)}/{len(ug)}")
print(f"ERROR_COLLAPSED (n={len(ec)}): premise-absent {sum(premise_absent(r) for r in ec)}/{len(ec)} · handler_form {sum(hf_present(r) for r in ec)}/{len(ec)}")
print("operand second-term for UNGUARDED (harm-named = names the ABSENT remedy, not present evidence):")
for r in ug:
    op=r["grammar"]["operands"]; print(f"   {r['id']:<9} {op}")

# ---- (3) Mechanical re-test of the 16 NONE records ----
# For each: can a WITNESS / STATIC_QUERY / DIFFERENTIAL be *stated*? If yes -> not a smell.
RETEST = {
 "O-AUTH-5": ("STATIC_QUERY","repo","query: call sites of verifyEmail that don't branch on the sentinel return","COMES_BACK"),
 "O-AUTH-7": (None,None,"'audit analysis brittle' — no wrong output; two events are distinguishable via isRevoke","RESISTANT"),
 "O-ENV-9":  ("DIFFERENTIAL",None,"same DOCUMENT_CANCELLED webhook fires for never-sent-draft vs in-flight-cancel — diff the two paths","COMES_BACK"),
 "O-JOB-2":  (None,None,"completedAt set on FAILED too — but status distinguishes; no wrong behaviour (plan predicted death)","RESISTANT"),
 "O-JOB-3":  (None,None,"WHERE status=PENDING guard is correct; 'fragile reasoning' is a preference","RESISTANT"),
 "O-JOB-11": ("STATIC_QUERY","file","query: retry path emits no structured log/metric — but a console.log DOES exist","BORDERLINE"),
 "O-ORG-5":  (None,None,"code narrows to data:{name}; current behaviour correct, risk is a future contributor","RESISTANT"),
 "O-ORG-6":  ("STATIC_QUERY","file","query: FolderUpdated payload carries no changed-dimension discriminator","BORDERLINE"),
 "O-ORG-7":  (None,None,"self-defeated: 'user-visible behaviour is correct' (defeater present in text)","RESISTANT"),
 "O-ORG-8":  (None,None,"fixed 7500ms timeout works; 'not configurable' is a preference","RESISTANT"),
 "O-SIGN-5": (None,None,"observability of which cascade level supplied config; no wrong output","RESISTANT"),
 "O-SIGN-8": ("WITNESS",None,"construct a read-only field whose default defeats the match-on-meta heuristic; assert mis-sign","BORDERLINE"),
 "O-TRPC-5": (None,None,"self-declared 'code smell, not a state-machine gap' (defeater present)","RESISTANT"),
 "O-TRPC-10":(None,None,"dispatcher/resender schema-coupling; future-change risk, no current failure","RESISTANT"),
 "O-TRPC-11":(None,None,"JSON-shaped polymorphism; type-system smell, no current failure","RESISTANT"),
 "O-N8":     ("STATIC_QUERY","repo","query: no admin route lists WebhookCall rows with status=FAILED (dead-letter absence)","COMES_BACK"),
}
print("\n=== (3) Re-test of the 16 discharge-resistant records ===")
verdict=collections.Counter(v[3] for v in RETEST.values())
for rid,(mech,scope,stmt,verd) in RETEST.items():
    tag={"COMES_BACK":"↩ REAL","BORDERLINE":"~ borderline","RESISTANT":"✂ dies"}[verd]
    print(f"  {rid:<10} {tag:<13} {(mech or '—'):<13} {stmt}")
print("\nverdict:", dict(verdict))
comes=[k for k,v in RETEST.items() if v[3]=="COMES_BACK"]
bord =[k for k,v in RETEST.items() if v[3]=="BORDERLINE"]
print(f"firm recoveries: {comes}")
print(f"borderline: {bord}")
print(f"=> real-obstacle count moves from 76 to {76+len(comes)} firm (+{len(bord)} borderline), smell floor 16 -> {16-len(comes)-len(bord)}..{16-len(comes)}")

json.dump({"unguarded_test":{"baseline_premise_absent_pct":round(base_premise_absent/N,3),
           "unguarded_premise_absent":[sum(premise_absent(r) for r in ug),len(ug)],
           "error_collapsed_premise_absent":[sum(premise_absent(r) for r in ec),len(ec)]},
           "smell_retest":{rid:{"mechanism":m,"scope":s,"discharge_statement":st,"verdict":v} for rid,(m,s,st,v) in RETEST.items()},
           "recoveries_firm":comes,"recoveries_borderline":bord},
          open(os.path.join(here,"phase0-followups.json"),"w"), indent=1)
