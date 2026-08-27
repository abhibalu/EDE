#!/usr/bin/env python3
"""Phase 0 corpus decomposition for the 2026-05-27 Documenso run.
Hand-authored annotation of all 92 obstacles under the finalized grammar schema.
Emits phase0-annotation.json (byte-comparable) + phase0-matrix.md (aggregates)."""
import json, collections, os

# discharge mechanism per PRIMARY claim type (fixed table)
MECH = {
    "MISSING_OWNERSHIP_CHECK": "WITNESS", "ERROR_COLLAPSED": "WITNESS",
    "NO_AUDIT": "WITNESS", "UNBOUNDED": "WITNESS",
    "NO_LIFECYCLE_ENFORCEMENT": "WITNESS",
    "NOT_ATOMIC": "FAULT_WITNESS", "OUTSIDE_TX": "FAULT_WITNESS",
    "NO_WRITER": "STATIC_QUERY", "UNREACHABLE": "STATIC_QUERY",
    "UNGUARDED": "STATIC_QUERY", "MISSING_FILTER": "STATIC_QUERY",
    "TOCTOU": "MODEL_CHECK", "DIFFERENTIAL": "DIFFERENTIAL",
    # candidate new types discovered this pass (evidence-level names):
    "MISSING_WRITE": "FAULT_WITNESS",
    # discharge-resistant / no witness statable:
    "NONE": None,
}
# candidate/misfit primaries kept verbatim, flagged, mechanism unknown
CANDIDATE_PRIMARIES = {
    "MUTABLE_CAPTURE_ACROSS_RETRY", "FANOUT_SHORT_CIRCUIT", "ORPHAN_RESOURCE",
    "STALE_CREDENTIAL", "PII_IN_LOGS",
}

# id: (sev, primary, operands, handler_form, scope, premise, defeater, hedge[], sev_rationale, secondaries[], flags[], dup_of)
# premise/defeater: None=absent, "IMPLICIT"=present-but-not-stated-as-rule, text=explicit span
# handler_form: verbatim literal quoted in description, or None (+mechanism_unbacked flag when a mechanism is asserted)
R = {
 "O-AUTH-1": ("HIGH","ERROR_COLLAPSED","forgotPassword,[emailSendFail]",".catch(console.error)",None,None,None,["can"],None,["NO_AUDIT"],[],None),
 "O-AUTH-2": ("MED","ERROR_COLLAPSED","createUser,[personalOrgCreateFail]",".catch(console.error)",None,"breaking the GUARANTEE that every new user has a workspace",None,[],None,["NOT_ATOMIC"],[],None),
 "O-AUTH-3": ("MED","NO_AUDIT","csrfMismatch",None,None,None,None,[],None,[],["comment_acknowledged"],None),
 "O-AUTH-4": ("LOW","UNGUARDED","oauthLink,preserveExistingPassword",None,None,None,None,[],None,[],["vocab_misfit","comment_acknowledged","future_risk"],None),
 "O-AUTH-5": ("LOW","NONE","verifyEmail-sentinel-return",None,None,None,None,["would"],None,[],["discharge_resistant","hypothetical"],None),
 "O-AUTH-6": ("HIGH","MUTABLE_CAPTURE_ACROSS_RETRY","recoveryCodes,prisma.$transaction","outer `let`",None,None,None,["if","may","could"],None,[],["vocab_new_candidate","hedge_x_high"],None),
 "O-AUTH-7": ("LOW","NONE","invalidateSessions-isRevoke-flag-overload",None,None,None,None,[],None,[],["discharge_resistant","overloaded_encoding"],None),
 "O-AUTH-8": ("HIGH","OUTSIDE_TX","invalidateSessions,passwordChangeTx",None,None,"IMPLICIT",None,[],None,[],[],None),
 "O-AUTH-9": ("MED","NO_AUDIT","sessionExpiry",None,None,None,None,[],None,[],[],None),
 "O-AUTH-10": ("CRITICAL","NO_LIFECYCLE_ENFORCEMENT","User.disabled","validateSessionToken does not check User.disabled",None,None,None,["can"],"effectively never-logged-out",["NO_AUDIT"],[],None),
 "O-AUTH-11": ("MED","NOT_ATOMIC","Session.create,UserSecurityAuditLog.create","two separate prisma.create calls",None,"IMPLICIT",None,["if"],None,[],[],None),
 "O-AUTH-12": ("HIGH","UNBOUNDED","sessionLifetime",None,None,None,None,[],"effective session lifetime is unbounded",["NO_AUDIT"],[],None),
 "O-AUTH-13": ("HIGH","TOCTOU","expiryCheck,challengeDelete",None,None,None,"this is good for replay protection, but if the order were reversed the challenge could be reused",["if","could"],None,[],["mixed_claim","defeater_present"],None),

 "O-ENV-1": ("CRITICAL","TOCTOU","haveAllRecipientsSigned,enqueueSeal",None,None,"executed AFTER the transaction commits and outside any lock","UNCAPTURED",["can"],None,[],["defeater_uncaptured","canary_class"],None),
 "O-ENV-2": ("CRITICAL","MISSING_FILTER","deleteMany,statusClause","prisma.envelope.deleteMany({ where: { teamId } })",None,None,None,[],"irreversibly ... There is no recovery path",["NO_AUDIT"],["dup_candidate"],"O-ORG-11"),
 "O-ENV-3": ("HIGH","NOT_ATOMIC","recipient.signingStatus,envelope.status",None,None,"an impossible-looking state",None,[],None,[],[],None),
 "O-ENV-4": ("HIGH","UNGUARDED","delete,isDocumentCompletedGate","isDocumentCompleted(envelope.status)",None,None,None,[],"no recovery ... no trash/restore",[],[],None),
 "O-ENV-5": ("HIGH","UNGUARDED","sealJob,statusGuardAtRunTop",None,None,None,None,["if","could","in principle"],None,[],["hypothetical","hedge_x_high"],None),
 "O-ENV-6": ("MED","TOCTOU","attachmentAdd,sealCommit",None,None,None,None,[],None,[],[],None),
 "O-ENV-7": ("MED","NO_AUDIT","templateEnvelopeMutations",None,None,None,None,[],None,[],[],None),
 "O-ENV-8": ("MED","ERROR_COLLAPSED","EnvelopeItemPdfReplaced,[fieldCoordRefetchFail]","console.error(err)",None,None,None,["can"],None,[],[],None),
 "O-ENV-9": ("LOW","NONE","DOCUMENT_CANCELLED-event-overload",None,None,None,None,[],None,[],["discharge_resistant","overloaded_encoding"],None),

 "O-JOB-1": ("HIGH","NO_WRITER","BackgroundJobTaskStatus,FAILED",None,"repo",None,None,[],None,[],[],None),
 "O-JOB-2": ("LOW","NONE","completedAt-overload-terminal-states",None,None,None,None,[],None,[],["discharge_resistant","overloaded_encoding"],None),
 "O-JOB-3": ("MED","NONE","implicit-where-clause-guard",None,None,None,None,[],None,[],["discharge_resistant","behaviour_correct"],None),
 "O-JOB-4": ("HIGH","OUTSIDE_TX","triggerWebhook,sealTx",None,None,None,None,[],None,[],[],None),
 "O-JOB-5": ("HIGH","OUTSIDE_TX","sendMail,reminderMarkTx",None,None,None,None,["if"],None,[],["hedge_x_high"],None),
 "O-JOB-6": ("MED","NOT_ATOMIC","sendMail,recipient.update(SENT)","two separate io.runTask steps",None,None,None,["can"],None,[],[],None),
 "O-JOB-7": ("MED","FANOUT_SHORT_CIRCUIT","completedEmailFanout","Promise.all",None,None,None,[],None,[],["vocab_new_candidate"],None),
 "O-JOB-8": ("HIGH","ERROR_COLLAPSED","submitJobToEndpoint,[networkFail,non200,slowTarget]","fetch().catch(()=>null)",None,None,None,[],None,[],[],None),
 "O-JOB-9": ("MED","ERROR_COLLAPSED","triggerWebhook,[perWebhookTriggerFail]","'Failed to trigger webhook' Error",None,None,None,[],None,[],[],None),
 "O-JOB-10": ("MED","ERROR_COLLAPSED","executeWebhookCall,[networkTimeout,DNS,TLS,malformed]","responseCode=0",None,None,None,[],None,[],[],None),
 "O-JOB-11": ("LOW","NONE","console.log-only-retry-logging","console.log(...)",None,None,None,[],None,[],["discharge_resistant","observability_quality"],None),

 "O-ORG-1": ("HIGH","ERROR_COLLAPSED","createOrganisation,[stripeCustomerCreateFail]","catch returns undefined",None,None,None,[],None,[],["comment_acknowledged"],None),
 "O-ORG-2": ("CRITICAL","NOT_ATOMIC","addUserToOrganisation,invite.update",None,None,None,None,[],None,[],[],None),
 "O-ORG-3": ("HIGH","OUTSIDE_TX","emailDispatch,dbTx",None,None,None,None,["if"],None,[],[],None),
 "O-ORG-4": ("HIGH","NO_WRITER","OrganisationMemberInviteStatus,DECLINED","status: { not: DECLINED }","surface",None,None,[],None,[],["scope_limited"],None),
 "O-ORG-5": ("MED","NONE","invariant-by-comment-only",None,None,None,None,[],None,[],["discharge_resistant","future_risk","comment_acknowledged"],None),
 "O-ORG-6": ("LOW","NONE","FolderUpdated-event-overload",None,None,None,None,[],None,[],["discharge_resistant","overloaded_encoding"],None),
 "O-ORG-7": ("MED","NONE","pre-read+P2002-redundant","findFirst",None,None,"the user-visible behaviour is correct",["can"],None,[],["discharge_resistant","behaviour_correct","defeater_present"],None),
 "O-ORG-8": ("LOW","NONE","hardcoded-7500ms-timeout","7500 ms",None,None,None,[],None,[],["discharge_resistant","magic_number"],None),
 "O-ORG-9": ("LOW","TOCTOU","ancestorWalk,reparent",None,None,None,None,["can"],None,["perf_Odepth"],[],None),
 "O-ORG-10": ("MED","NO_LIFECYCLE_ENFORCEMENT","DocumentShareLink.expiry","update: {}",None,None,None,[],None,[],[],None),
 "O-ORG-11": ("CRITICAL","MISSING_FILTER","deleteMany,statusClause","prisma.envelope.deleteMany({ where: { teamId } })",None,None,None,[],"silent destructive data loss",["NO_AUDIT"],["dup_candidate"],"O-ENV-2"),
 "O-ORG-12": ("HIGH","MISSING_WRITE","demotePreviousOwner",None,None,None,None,["may","if"],None,[],["vocab_new_candidate","dup_candidate","hedge_x_high"],"O-TRPC-3"),

 "O-PAPI-1": ("HIGH","ERROR_COLLAPSED","v1Handlers,[auth,validation,S3,DB,quota]",None,"package",None,None,[],"observability of failures is destroyed",[],["error_swallow_sibling"],None),
 "O-PAPI-2": ("HIGH","ERROR_COLLAPSED","updateRecipient,[auth,DB,conflict,validation]",".catch(null)",None,"The .catch(null) idiom drops the rejection reason entirely","UNCAPTURED",[],None,[],["canary","mischaracterized_known","defeater_uncaptured","error_swallow_sibling"],None),
 "O-PAPI-3": ("CRITICAL","UNGUARDED","templateRecipientRemap,keyValidation","template.recipients.at(i)",None,None,None,[],None,[],["comment_acknowledged","index_coupling"],None),
 "O-PAPI-4": ("HIGH","DIFFERENTIAL","v1CreateField,serviceCreateField",None,None,None,None,[],None,[],["differential"],None),
 "O-PAPI-5": ("CRITICAL","MISSING_OWNERSHIP_CHECK","documentId,fieldId","deleteDocumentField(fieldId only)",None,None,None,["can"],None,[],["comment_acknowledged"],None),
 "O-PAPI-6": ("HIGH","MISSING_OWNERSHIP_CHECK","documentId,recipientId","deleteEnvelopeRecipient(recipientId only)",None,None,None,[],None,["DATA_CORRUPTION:auditUser.email=team.name"],["multi_defect"],None),
 "O-PAPI-7": ("MED","ERROR_COLLAPSED","uploadEndpoints,[uploadTransportConfig]",None,None,None,None,[],None,[],["error_swallow_sibling","mechanism_unbacked"],None),
 "O-PAPI-8": ("HIGH","ORPHAN_RESOURCE","envelope,uploadConfirmation",None,None,None,None,["can"],None,[],["vocab_new_candidate"],None),
 "O-PAPI-9": ("MED","UNGUARDED","sendDocument,idempotency",None,None,None,None,[],None,[],["vocab_misfit","hidden_side_effect"],None),
 "O-PAPI-10": ("HIGH","NOT_ATOMIC","envelope.create,authOptions.update","follow-up prisma.envelope.update",None,None,None,["if"],"a security-relevant partial-failure state",[],[],None),

 "O-SIGN-1": ("HIGH","UNGUARDED","ccRecipientCreate,signingStateTraversal",None,None,None,None,[],None,[],["vocab_misfit","overloaded_encoding"],None),
 "O-SIGN-2": ("HIGH","TOCTOU","recipientStatusRead,recipientUpdate",None,None,"no compare-and-swap guard",None,["can"],"lost-update race",[],[],None),
 "O-SIGN-3": ("MED","NO_WRITER","Recipient.status,EXPIRED",None,None,None,None,[],None,["NO_AUDIT"],[],None),
 "O-SIGN-4": ("MED","ERROR_COLLAPSED","assistantPrefill,[blockedGuard,actualNotFound]","findFirstOrThrow",None,None,None,[],None,[],[],None),
 "O-SIGN-5": ("LOW","NONE","reminder-cascade-implicit",None,None,None,None,[],None,[],["discharge_resistant","dup_candidate","observability_quality"],"O-N10"),
 "O-SIGN-6": ("MED","NO_AUDIT","FieldUninserted",None,None,None,None,[],None,[],[],None),
 "O-SIGN-7": ("HIGH","OUTSIDE_TX","pdfWhiteout,fieldTx",None,None,None,None,["if"],None,[],[],None),
 "O-SIGN-8": ("LOW","NONE","readonly-field-match-on-meta-hack","HACK comment sign-field-with-token.ts:212",None,None,None,[],None,[],["discharge_resistant","comment_acknowledged"],None),
 "O-SIGN-9": ("MED","TOCTOU","singletonCheck,singletonAssign","// eslint-disable require-atomic-updates",None,None,None,["could"],None,[],[],None),
 "O-SIGN-10": ("HIGH","UNGUARDED","signingTransport,prodCertGuard","./example/cert.p12",None,None,None,["can"],None,[],[],None),
 "O-SIGN-11": ("MED","OUTSIDE_TX","notificationEmail,deleteTx",None,None,None,None,["if"],None,[],[],None),

 "O-TRPC-1": ("HIGH","ERROR_COLLAPSED","verifyEmbeddingPresignToken,[expired,revoked,malformed,transientDB]",".catch(() => null)",None,None,None,[],None,[],["error_swallow_sibling"],None),
 "O-TRPC-2": ("MED","ERROR_COLLAPSED","createEmbeddingPresignToken,[nonAppErrors]","AppError(UNKNOWN_ERROR,...)",None,None,None,[],None,["NO_AUDIT"],["error_swallow_sibling"],None),
 "O-TRPC-3": ("HIGH","MISSING_WRITE","demotePreviousOwner",None,None,None,None,["may"],None,[],["vocab_new_candidate","dup_candidate"],"O-ORG-12"),
 "O-TRPC-4": ("MED","NO_AUDIT","createWebhook",None,None,None,None,[],None,[],["differential_sibling"],None),
 "O-TRPC-5": ("LOW","NONE","resetTwoFactor-inline-router",None,None,None,"Code smell, not a state-machine gap",["would"],"Code smell, not a state-machine gap",[],["discharge_resistant","self_declared_smell","defeater_present"],None),
 "O-TRPC-6": ("HIGH","UNGUARDED","deleteUser,confirmationToken",None,None,None,None,[],"permanently removes a user and all cascaded rows",["NO_AUDIT"],[],None),
 "O-TRPC-7": ("MED","UNGUARDED","embedAuthoring,planFlagCheck","IS_BILLING_ENABLED()",None,None,None,[],None,["NO_AUDIT"],[],None),
 "O-TRPC-8": ("HIGH","NO_LIFECYCLE_ENFORCEMENT","ApiToken.expires",None,"package","Enforcement is entirely deferred to whichever downstream call site invokes getApiTokenByToken","Enforcement is entirely deferred to ... getApiTokenByToken",["may","if"],None,[],["scope_caveat","dup_candidate","defeater_present","hedge_x_high"],"O-N6"),
 "O-TRPC-9": ("MED","UNGUARDED","resendWebhookCall,idempotencyKey",None,None,None,None,[],None,[],["no_idempotency"],None),
 "O-TRPC-10": ("LOW","NONE","dispatcher-resender-schema-coupling",None,None,None,None,[],None,[],["discharge_resistant","comment_acknowledged"],None),
 "O-TRPC-11": ("LOW","NONE","duplicateEnvelope-json-polymorphism",None,None,None,None,[],None,[],["discharge_resistant","type_system_smell"],None),

 "O-N1": ("HIGH","UNGUARDED","v1Mutations,idempotencyKey",None,"surface",None,None,[],None,[],["no_idempotency"],None),
 "O-N2": ("HIGH","NO_LIFECYCLE_ENFORCEMENT","envelope.retention",None,"repo",None,None,[],None,[],["no_retention"],None),
 "O-N3": ("HIGH","NO_LIFECYCLE_ENFORCEMENT","signingKey.rotation",None,None,None,None,["may"],None,[],["hedge_x_high"],None),
 "O-N4": ("MED","UNGUARDED","webhookReceiver,replayProtection",None,None,None,None,[],None,[],["receiver_side_scope"],None),
 "O-N5": ("MED","UNBOUNDED","reminderResend",None,None,None,None,[],None,[],[],None),
 "O-N6": ("HIGH","NO_LIFECYCLE_ENFORCEMENT","ApiToken.expires",None,"repo",None,None,["may"],None,[],["dup_candidate"],"O-TRPC-8"),
 "O-N7": ("MED","NO_LIFECYCLE_ENFORCEMENT","invite.expiry",None,None,None,None,[],None,[],["no_expiry"],None),
 "O-N8": ("MED","NONE","no-dead-letter-admin-tooling",None,None,None,None,[],None,[],["discharge_resistant","ops_gap"],None),
 "O-N9": ("HIGH","MISSING_OWNERSHIP_CHECK","caller.team,template",None,None,None,None,[],None,[],[],None),
 "O-N10": ("LOW","UNGUARDED","reminderCascade,jsonSchemaValidation",None,None,None,None,["may"],None,[],["dup_candidate","angle_differs"],"O-SIGN-5"),
 "O-N11": ("LOW","STALE_CREDENTIAL","ApiToken-not-deleted-on-user-delete",None,None,None,None,[],None,[],["vocab_new_candidate"],None),
 "O-N12": ("MED","NO_AUDIT","folderReparentOnDelete","Envelope.folderId set null via SetNull",None,None,None,[],None,[],[],None),
 "O-N13": ("MED","UNBOUNDED","presignedUrlTTL",None,None,None,None,[],None,["NO_AUDIT"],[],None),
 "O-N14": ("MED","UNBOUNDED","signatureImageSize",None,None,None,None,[],None,[],[],None),
 "O-N15": ("MED","PII_IN_LOGS","logRedaction",None,"repo",None,None,["potentially"],None,[],["vocab_new_candidate"],None),
}

CALIBRATION = {"O-AUTH-1","O-AUTH-11","O-ENV-1","O-ENV-2","O-JOB-1","O-PAPI-5","O-PAPI-2","O-TRPC-8","O-N6","O-TRPC-5"}

# --- build records ---
src = {o["id"]: o for o in json.load(open(os.path.join(os.path.dirname(__file__),"corpus.json")))}
records = []
for rid,(sev,primary,operands,hf,scope,premise,defeater,hedge,sevrat,secs,flags,dup) in R.items():
    flags = list(flags)
    if hf is None and primary not in ("NONE",) and primary in MECH and MECH.get(primary)=="WITNESS" and "mechanism_unbacked" not in flags:
        pass  # not auto-flagging; explicit flags only
    mech = MECH.get(primary, "UNKNOWN") if primary not in CANDIDATE_PRIMARIES else "UNKNOWN"
    rec = {
        "id": rid, "severity": sev, "gapSource": src[rid]["gapSource"],
        "calibration": rid in CALIBRATION,
        "grammar": {
            "primary": primary, "operands": operands, "mechanism": mech,
            "handler_form": hf, "scope": scope,
            "secondaries": secs, "dup_of": dup,
        },
        "slots": {
            "premise": premise, "defeater": defeater,
            "hedge": hedge, "severity_rationale": sevrat,
        },
        "flags": flags,
    }
    records.append(rec)

assert len(records)==92, len(records)

# --- matrix computation ---
prim = collections.Counter(r["grammar"]["primary"] for r in records)
CORE = {"NOT_ATOMIC","OUTSIDE_TX","ERROR_COLLAPSED","NO_WRITER","UNREACHABLE","UNGUARDED",
        "NO_AUDIT","MISSING_OWNERSHIP_CHECK","TOCTOU","NO_LIFECYCLE_ENFORCEMENT","UNBOUNDED"}
PLAN_EXTRA = {"MISSING_FILTER","DIFFERENTIAL"}
core_n = sum(v for k,v in prim.items() if k in CORE)
extra_n = sum(v for k,v in prim.items() if k in PLAN_EXTRA)
none_n = prim.get("NONE",0)
cand_n = sum(v for k,v in prim.items() if k in CANDIDATE_PRIMARIES or k=="MISSING_WRITE")
real = 92 - none_n

premise_present = sum(1 for r in records if r["slots"]["premise"] not in (None,))
premise_explicit = sum(1 for r in records if r["slots"]["premise"] not in (None,"IMPLICIT"))
defeater_present = sum(1 for r in records if r["slots"]["defeater"] not in (None,"UNCAPTURED"))
defeater_uncaptured = sum(1 for r in records if r["slots"]["defeater"]=="UNCAPTURED")
sevrat_present = sum(1 for r in records if r["slots"]["severity_rationale"])
hf_present = sum(1 for r in records if r["grammar"]["handler_form"])
# hedge computed MECHANICALLY from the source description (reproducible), not hand lists
import re
HEDGE_RE = re.compile(r"\b(could|may|would|might|potentially|possibly|in principle|if)\b", re.I)
def hedges_in(rid): return sorted(set(m.group(0).lower() for m in HEDGE_RE.finditer(src[rid]["description"])))
for r in records: r["slots"]["hedge_mechanical"] = hedges_in(r["id"])
hedged = sum(1 for r in records if r["slots"]["hedge_mechanical"])
HI = {"HIGH","CRITICAL"}
hedge_x_high = [r["id"] for r in records if r["slots"]["hedge_mechanical"] and r["severity"] in HI]
# content address = (primary, operands). A predicted dup MERGES only if addresses match.
addr = {r["id"]: (r["grammar"]["primary"], r["grammar"]["operands"]) for r in records}
pred_pairs = sorted({tuple(sorted((r["id"],r["grammar"]["dup_of"]))) for r in records if r["grammar"]["dup_of"]})
clean_merges = [(a,b) for a,b in pred_pairs if addr[a]==addr[b]]
contested = [(a,b) for a,b in pred_pairs if addr[a]!=addr[b]]
dups = clean_merges
sev = collections.Counter(r["severity"] for r in records)

out = {
    "pipelineVersion":"0.1.0","phase":0,"run":"2026-05-27","project":"documenso",
    "source":"docs/pipeline/runs/2026-05-27/03-goals.json",
    "schemaVersion":"grammar-v0-slots7",
    "totals":{"records":92,"real":real,"discharge_resistant":none_n,"distinct_after_dedup":92-len(dups)},
    "records":records,
}
json.dump(out, open(os.path.join(os.path.dirname(__file__),"phase0-annotation.json"),"w"), indent=1)

# --- markdown matrix ---
def bar(n,tot=92): return "█"*round(24*n/tot)
lines=[]
A=lines.append
A("# Phase 0 — Corpus Decomposition")
A(f"\n**Run:** documenso 2026-05-27 · **Source:** `03-goals.json` · **Records:** 92 (77 confirmed + 15 new)\n")
A("## Slot-presence matrix\n")
A("| slot | present | note |")
A("|---|---|---|")
A(f"| location | 92/92 | universal — every record cites a symbol/file |")
A(f"| code_observation | 92/92 | universal |")
A(f"| **premise** | {premise_present}/92 ({premise_explicit} explicit) | **prediction confirmed: absent/implicit in {92-premise_explicit}** |")
A(f"| **defeater** | {defeater_present}/92 (+{defeater_uncaptured} uncaptured) | sparse but diagnostic; both canaries have it UNCAPTURED |")
A(f"| hedge | {hedged}/92 | observed→inferred boundary |")
A(f"| severity_rationale | {sevrat_present}/92 | severity is mostly asserted, not argued |")
A(f"| handler_form | {hf_present}/92 | the literal that discriminates canary from corrected |")
A("\n## Claim-type distribution (primary only)\n")
A("| primary | n | mechanism | |")
A("|---|--:|---|---|")
for k,v in prim.most_common():
    m = MECH.get(k,"UNKNOWN") if k not in CANDIDATE_PRIMARIES else "candidate"
    A(f"| {k} | {v} | {m or '—'} | {bar(v)} |")
A(f"\n**Coverage:** core-11 types = {core_n}/92 · plan extras (MISSING_FILTER, DIFFERENTIAL) = {extra_n} · "
  f"new candidates = {cand_n} · discharge-resistant (NONE) = {none_n}")
A(f"\nExcluding the {none_n} discharge-resistant smells, real obstacles = {real}; "
  f"core-11 covers {core_n}/{real} = {round(100*core_n/real)}%.")
A(f"\n`UNREACHABLE` = 0 in this corpus. `UNGUARDED` and `ERROR_COLLAPSED` = {prim['UNGUARDED']}/{prim['ERROR_COLLAPSED']} (most-loaded; UNGUARDED is the catch-all to scrutinize).")
A("\n## Duplicate collapse (by content address = primary + operands)\n")
A("**Clean merges** (identical content address):")
for a,b in clean_merges:
    A(f"- `{a}` ≡ `{b}`  →  `{addr[a][0]}({addr[a][1]})`")
A("\n**Contested** (plan predicted a merge; grammar keeps them apart — the identity-function test):")
for a,b in contested:
    A(f"- `{a}` ✗ `{b}`  →  `{addr[a][0]}` vs `{addr[b][0]}` — same site, different claim")
A(f"\n{len(clean_merges)} clean merges → 92 records collapse to **{92-len(clean_merges)} distinct**. "
  f"{len(contested)} predicted pair(s) did NOT merge: the identity function is finer than a site-hash, "
  f"which is the intended behaviour — same location, genuinely different claim.")
A("\n## Hedge ∩ HIGH/CRITICAL hotspot (false-positive signature)\n")
A(f"{len(hedge_x_high)} records: {', '.join('`'+i+'`' for i in hedge_x_high)}")
A("\n## Severity mix\n")
A(" · ".join(f"{k}={v}" for k,v in sev.most_common()))
open(os.path.join(os.path.dirname(__file__),"phase0-matrix.md"),"w").write("\n".join(lines))
print("OK — wrote phase0-annotation.json and phase0-matrix.md")
print(f"records=92 real={real} none={none_n} dups={len(dups)} premise_explicit={premise_explicit} hedge_x_high={len(hedge_x_high)}")
print("primary dist:", dict(prim.most_common()))
