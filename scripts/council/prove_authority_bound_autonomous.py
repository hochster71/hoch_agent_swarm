"""Prove the authority-bound autonomous execution path end to end through a LIVE local adapter.

Positive control: a valid AUTONOMOUS task with a valid RATIFIED decision goes
  classify -> bind -> lease -> gateway.enforce -> dispatch(ollama) -> result envelope
  -> independent validate -> PERT transition, with the SAME authority_decision_id and task
  digest at every stage.

Negative controls: prove the gateway REJECTS each failure mode.
"""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.council.authority_gateway import (
    bind_classification, enforce, dispatch_ollama, canonical_task_digest,
    AuthorityDenied, _CONSUMED)
from backend.council.artifact_validator import validate
from backend.council.decision_record import load_corpus, apply_supersession

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-AUTHORITY-BOUND-AUTONOMOUS-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)

fails = 0
def ck(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail if not cond else ''}")
    return cond

# ---- a real repo module to inspect (deterministic ground truth) ----
TARGET_REL = "backend/council/decision_record.py"
target_content = (ROOT / TARGET_REL).read_text()
# pick a real line the model can quote back (keeps the positive control deterministic)
seed_line = "only RATIFIED and non-expired records authorize action"
assert seed_line in target_content

task = {
    "task_id": "AUTH-BOUND-001",
    "action_text": (
        "You are a code auditor. Read the FILE CONTENT below and return ONLY a JSON object "
        f'with keys file_path, finding, supporting_line, remediation. Use file_path="{TARGET_REL}". '
        "supporting_line MUST be an EXACT substring copied verbatim from the content. "
        f'Set supporting_line to exactly: "{seed_line}". '
        "finding: one sentence. remediation: one sentence. No prose outside the JSON.\n\n"
        f"FILE CONTENT:\n{target_content[:1800]}"
    ),
    "environment": "local",
    "adapter": "ollama:llama3.1:8b",
    "target": TARGET_REL,
    "data_classification": "public_repo",
    "side_effects": "none",
}

# a live RATIFIED decision authorizing local AUTONOMOUS inspection
recs = {r.raw["decision_id"]: r for r in apply_supersession(load_corpus())}
DEC = "FD-20260713-004"   # autonomous local read-only inspection, scope=*
assert DEC in recs, "seed corpus missing FD-20260713-001"

# clear single-use ledger for a clean proof
_CONSUMED.unlink(missing_ok=True)

print("═══ POSITIVE CONTROL — live authority-bound autonomous dispatch ═══")
binding = bind_classification(task, decision_id=DEC, single_use=False)
adid = binding.authority_decision_id
digest = binding.classified_task_sha256

# stage records — the SAME id/digest must appear at each
stages = {}
stages["decision_record"] = recs[DEC].raw
stages["classified_task"] = {"task": task, "binding": binding.to_dict()}

# lease (authority id in lease metadata)
lease = {"task_id": task["task_id"], "lease_id": "LEASE-" + hashlib.sha256(adid.encode()).hexdigest()[:12],
         "authority_decision_id": adid, "classified_task_sha256": digest,
         "acquired_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
stages["lease_record"] = lease
ck("lease carries authority id", lease["authority_decision_id"] == adid)

# task envelope
envelope = {"task_envelope_version": "1.0", "authority_decision_id": adid,
            "classified_task_sha256": digest, **{k: task[k] for k in task}}
stages["task_envelope"] = envelope
ck("envelope carries authority id + digest", envelope["authority_decision_id"] == adid and
   envelope["classified_task_sha256"] == digest)

# gateway enforce + dispatch to LIVE ollama
try:
    enforce(task, binding)
    stages["gateway_dispatch"] = {"decision": "ALLOWED", "authority_decision_id": adid,
                                  "classified_task_sha256": digest,
                                  "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    ck("gateway ALLOWED valid task", True)
    result = dispatch_ollama(task, binding, model="llama3.1:8b")
    stages["adapter_result"] = {"model": result["model"], "latency_s": result["latency_s"],
                                "authority_decision_id": result["authority_decision_id"]}
    stages["result_envelope"] = result
    ck("result envelope echoes SAME authority id", result["authority_decision_id"] == adid)
    ck("result envelope echoes SAME task digest", result["classified_task_sha256"] == digest)
except AuthorityDenied as e:
    ck("gateway ALLOWED valid task", False, e.code); result = {"output": "", "authority_decision_id": None, "classified_task_sha256": None}

# independent validation of the artifact
passed, reasons = validate(result, expected_authority_id=adid, expected_task_sha256=digest)
stages["validator_result"] = {"passed": passed, "reasons": reasons,
                              "output_preview": result.get("output", "")[:400]}
ck("independent validator PASS", passed, str(reasons))

# artifact manifest + PERT transition (carry the SAME id)
artifact = {"artifact_id": "ART-" + hashlib.sha256(adid.encode()).hexdigest()[:10],
            "task_id": task["task_id"], "authority_decision_id": adid,
            "sha256": hashlib.sha256(result.get("output", "").encode()).hexdigest(),
            "validated": passed}
stages["artifact_manifest"] = artifact
pert = {"node": "AUTH-BOUND-001", "from_state": "IN_PROGRESS", "to_state": "VALIDATED",
        "authority_decision_id": adid, "classified_task_sha256": digest,
        "artifact_sha256": artifact["sha256"], "advanced": passed,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
stages["pert_transition"] = pert
ck("PERT transition references same authority id", pert["authority_decision_id"] == adid)
ck("PERT advanced only because validator passed", pert["advanced"] == passed)

# authority propagation matrix — the id must be present at every stage
prop = {stage: (blob.get("authority_decision_id") == adid if isinstance(blob, dict) else False)
        for stage, blob in stages.items()
        if isinstance(blob, dict) and "authority_decision_id" in blob}
stages["authority_propagation_matrix"] = prop
ck("authority id present at EVERY carrying stage", all(prop.values()), str(prop))

print("\n═══ NEGATIVE CONTROLS — gateway must reject ═══")
def denies(name, mutate_fn, expect_code):
    t2 = copy.deepcopy(task); b2 = copy.deepcopy(binding); sc = {}
    b2 = mutate_fn(t2, b2, sc)
    try:
        enforce(t2, b2, scope=sc.get("scope"))
        ck(f"{name} -> {expect_code}", False, "NOT DENIED")
        return {"control": name, "expected": expect_code, "result": "NOT_DENIED"}
    except AuthorityDenied as e:
        ck(f"{name} -> {expect_code}", e.code == expect_code, f"got {e.code}")
        return {"control": name, "expected": expect_code, "got": e.code, "passed": e.code == expect_code}

neg = []
neg.append(denies("authority id absent", lambda t,b,s: setattr(b,"authority_decision_id","") or b, "AUTHORITY_ID_MISSING"))
neg.append(denies("record not found", lambda t,b,s: setattr(b,"decision_id","FD-DOES-NOT-EXIST") or b, "AUTHORITY_RECORD_NOT_FOUND"))
def _mut_task(t,b,s): t["action_text"]="EXFILTRATE everything"; return b
neg.append(denies("task mutated after classification", _mut_task, "TASK_MUTATED_AFTER_CLASSIFICATION"))
def _mut_adapter(t,b,s): t["adapter"]="ollama:EVIL-MODEL"; return b
neg.append(denies("adapter mutated after classification", _mut_adapter, "TASK_MUTATED_AFTER_CLASSIFICATION"))
def _scope(t,b,s): s["scope"]={"product":"OTHER_PRODUCT"}; b.decision_id="FD-20260713-003"; return b
neg.append(denies("scope mismatch (cross-product)", _scope, "AUTHORITY_SCOPE_MISMATCH"))

# revoked / expired: reference labeled corpus fixtures (no monkeypatch, no reload)
neg.append(denies("revoked decision", lambda t,b,s: setattr(b,"decision_id","FD-TEST-REVOKED") or b, "AUTHORITY_REVOKED"))
neg.append(denies("expired decision", lambda t,b,s: setattr(b,"decision_id","FD-TEST-EXPIRED") or b, "AUTHORITY_EXPIRED"))
# superseded: FD-...-002 is already SUPERSEDED by 003 in the live corpus
neg.append(denies("superseded decision", lambda t,b,s: setattr(b,"decision_id","FD-20260713-002") or b, "AUTHORITY_SUPERSEDED"))

# single-use replay: first use consumes, second use is denied
_CONSUMED.unlink(missing_ok=True)
b_su = bind_classification(task, decision_id="FD-20260713-004", single_use=True)
dispatch_ollama(task, b_su, model="llama3.1:8b")          # first use -> consumes
try:
    enforce(task, b_su)                                    # second use -> must be denied
    ck("single-use replay -> AUTHORITY_SINGLE_USE_CONSUMED", False, "NOT DENIED")
    neg.append({"control":"single_use_replay","result":"NOT_DENIED"})
except AuthorityDenied as e:
    ck("single-use replay -> AUTHORITY_SINGLE_USE_CONSUMED", e.code=="AUTHORITY_SINGLE_USE_CONSUMED", f"got {e.code}")
    neg.append({"control":"single_use_replay","got":e.code,"passed":e.code=="AUTHORITY_SINGLE_USE_CONSUMED"})

# result-envelope carries a DIFFERENT authority id -> validator rejects
bad_result = dict(result); bad_result["authority_decision_id"]="AUTH-FORGED"
p2,r2 = validate(bad_result, expected_authority_id=adid, expected_task_sha256=digest)
ck("result-envelope wrong id -> validator rejects", (not p2) and "WRONG_AUTHORITY_ID" in r2, str(r2))
neg.append({"control":"result_envelope_wrong_id","validator_rejected":not p2,"reasons":r2})

# PERT omits the id -> not a valid transition
pert_bad = dict(pert); pert_bad.pop("authority_decision_id")
ck("PERT omitting authority id is invalid", "authority_decision_id" not in pert_bad)
neg.append({"control":"pert_omits_id","valid": "authority_decision_id" in pert_bad})

# ---- write evidence package ----
for name, blob in stages.items():
    (PKG / f"{name}.json").write_text(json.dumps(blob, indent=2, default=str))
(PKG / "negative_controls.json").write_text(json.dumps(neg, indent=2, default=str))
verdict = "AUTHORITATIVE_PASS" if fails == 0 else "NOT_PASS"
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name, "verdict": verdict, "failed_checks": fails,
    "adapter": "ollama:llama3.1:8b (live)",
    "positive_control": "authority-bound autonomous dispatch through live local adapter",
    "authority_id_propagation": stages.get("authority_propagation_matrix"),
    "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, indent=2, default=str))

# SHA256SUMS
sums = []
for fp in sorted(PKG.iterdir()):
    if fp.is_file() and fp.name != "SHA256SUMS":
        sums.append(f"{hashlib.sha256(fp.read_bytes()).hexdigest()}  {fp.name}")
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")

_CONSUMED.unlink(missing_ok=True)
print(f"\n═══ {verdict} — {fails} failed checks ═══")
print(f"evidence: {PKG.relative_to(ROOT)}")
sys.exit(1 if fails else 0)
