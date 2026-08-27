#!/usr/bin/env python3
"""Phase 1 grammar falsification test.
Hand-encode PAPI-G2 in its WRONG (pipeline-emitted) and CORRECTED (ground-truth) forms.
The grammar PASSES iff the two records differ in a LOAD-BEARING field, not just prose.
Also: content address must treat them as the SAME finding (same defect, same site) so
that rerun-as-measurement maps N+1 onto N; the DISCHARGE is what adjudicates which is right."""
import json, os, hashlib

LOAD_BEARING = ["claim_type","site","operands","handler_form","premise","observable","discharge_condition"]
QUARANTINED  = ["narrative","severity_rationale","confidence"]

# --- The same source line in both: packages/api ... updateRecipient -> updateEnvelopeRecipients().catch(null)
WRONG = {  # what the pipeline emitted as O-PAPI-2
  "claim_type":"ERROR_COLLAPSED",
  "site":"api/v1:updateRecipient/updateEnvelopeRecipients",
  "operands":{"site":"updateRecipient","causes":["auth","conflict","db","validation"]},
  "handler_form":".catch(null)",
  "premise":".catch(null) attaches null as the onRejected handler, swallowing the rejection and dropping its reason",
  "observable":"HTTP 404 'Recipient not found'",
  "discharge_condition":"WITNESS: stub updateEnvelopeRecipients to reject; assert response is 404 that masks the true cause",
  # quarantined:
  "narrative":"updateRecipient swallows errors via .catch(null) then reports 404 for any failure cause",
  "severity_rationale":"HIGH — all failure causes collapse to one opaque client response",
  "confidence":"inferred",
}
CORRECTED = {  # ground truth (source-verified)
  "claim_type":"ERROR_COLLAPSED",
  "site":"api/v1:updateRecipient/updateEnvelopeRecipients",
  "operands":{"site":"updateRecipient","causes":["auth","conflict","db","validation"]},
  "handler_form":".catch(null)",  # SAME literal — it is the actual source
  "premise":"per Promise semantics a non-function passed to .catch attaches NO rejection handler; the rejection PROPAGATES uncaught to the tRPC error middleware",
  "observable":"HTTP 401 (middleware maps the uncaught rejection to an auth error)",
  "discharge_condition":"WITNESS: stub updateEnvelopeRecipients to reject; assert response is 401, NOT 404",
  "narrative":"the .catch(null) is a no-op typo for .catch(()=>null); failures surface as 401 via middleware, not a masked 404",
  "severity_rationale":"HIGH — real defect (auth-shaped error for non-auth failures) but the emitted mechanism is inverted",
  "confidence":"observed",
}

def canon(v): return json.dumps(v, sort_keys=True)
def content_address(rec):
    # interim identity: hash over (claim_type, normalized symbol, sorted operands)
    key = canon([rec["claim_type"], rec["site"], rec["operands"]])
    return hashlib.sha256(key.encode()).hexdigest()[:12]

lb_diff = [f for f in LOAD_BEARING if canon(WRONG[f])!=canon(CORRECTED[f])]
q_diff  = [f for f in QUARANTINED  if canon(WRONG[f])!=canon(CORRECTED[f])]
same_addr = content_address(WRONG)==content_address(CORRECTED)
PASS = len(lb_diff) > 0

out = {
  "test":"phase1-grammar-falsification","case":"PAPI-G2",
  "result":"PASS" if PASS else "FAIL",
  "load_bearing_fields_that_differ": lb_diff,
  "load_bearing_fields_identical":[f for f in LOAD_BEARING if f not in lb_diff],
  "quarantined_fields_that_differ": q_diff,
  "content_address_wrong": content_address(WRONG),
  "content_address_corrected": content_address(CORRECTED),
  "same_finding_by_content_address": same_addr,
  "records":{"wrong":WRONG,"corrected":CORRECTED},
  "findings":[
    "Grammar PASSES: wrong and corrected differ in load-bearing fields (%s), not merely prose." % ", ".join(lb_diff),
    "handler_form is IDENTICAL in both — the source literal is ground truth; it does NOT discriminate wrong-vs-corrected.",
    "The discriminators are premise and observable. => observable must be promoted to its OWN load-bearing slot (Phase 0 folded it into consequence_claim).",
    "Content address is %s in both: the grammar treats them as the SAME finding. Correct — one defect, described wrongly then rightly." % ("IDENTICAL" if same_addr else "DIFFERENT"),
    "Therefore the DISCHARGE (401 vs 404 witness) is the adjudicator of which premise is true — the test is the identity function, exactly as the thesis claims.",
  ],
}
here=os.path.dirname(__file__)
json.dump(out, open(os.path.join(here,"phase1-falsification.json"),"w"), indent=1)
print("RESULT:", out["result"])
print("load-bearing differ:", lb_diff)
print("load-bearing identical:", out["load_bearing_fields_identical"])
print("same content address:", same_addr, "(", out["content_address_wrong"], ")")
