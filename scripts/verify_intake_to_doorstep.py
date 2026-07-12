#!/usr/bin/env python3
"""REQ-TO-003 — validate the newest DOORSTEP package end to end. Fails closed."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PKGS = ROOT / "coordination" / "council" / "live_proof_packages"
OUT = ROOT / "coordination" / "goal" / "intake_to_doorstep.json"

cands = sorted(PKGS.glob("REQ-TO-003-INTAKE-TO-DOORSTEP-*"))
if not cands:
    print("no TO-003 package"); OUT.write_text(json.dumps({"status":"FAIL","reason":"NO_PACKAGE"})+"\n"); sys.exit(1)
pkg = cands[-1]

REQUIRED = ["mission_manifest.json","intake_envelope.json","validated_plan.json",
            "route_decision.json","execution_manifest.json","execution_results.json",
            "verification_results.json","acceptance_results.json","artifact_inventory.json",
            "artifact_digests.json","founder_actions.json","runtime_truth.json",
            "validation.json","SHA256SUMS","orchestrator_state.json","doorstep.json"]
errs = [f"MISSING:{r}" for r in REQUIRED if not (pkg/r).exists()]

# every recorded digest must still match the bytes on disk
digests = json.loads((pkg/"artifact_digests.json").read_text()) if (pkg/"artifact_digests.json").exists() else {}
for name, h in digests.items():
    f = pkg/name
    if not f.exists():
        errs.append(f"DIGEST_TARGET_MISSING:{name}"); continue
    if hashlib.sha256(f.read_bytes()).hexdigest() != h:
        errs.append(f"DIGEST_MISMATCH:{name}")

st = json.loads((pkg/"orchestrator_state.json").read_text()) if (pkg/"orchestrator_state.json").exists() else {}
m = st.get("manual_intervention_metrics", {})
stages = {"INTAKE","PLAN","ROUTE","EXECUTE","VERIFY","PACKAGE","DOORSTEP"}
proven = 0
tr = [t["to"] for t in st.get("transitions", []) if t["verdict"] == "ADMITTED"]
for want, stage in [("INTAKE_VALIDATED","INTAKE"),("PLAN_VALIDATED","PLAN"),
                    ("ROUTE_AUTHORIZED","ROUTE"),("EXECUTION_COMPLETE","EXECUTE"),
                    ("VERIFICATION_PASS","VERIFY"),("PACKAGE_VALIDATED","PACKAGE"),
                    ("DOORSTEP_READY","DOORSTEP")]:
    if want in tr: proven += 1
    else: errs.append(f"STAGE_NOT_PROVEN:{stage}")

if st.get("state") != "DOORSTEP_READY": errs.append(f"NOT_DOORSTEP_READY:{st.get('state')}")
for k in ("manual_prompt_copy_count","manual_result_copy_count","manual_stage_transition_count"):
    if m.get(k, 1) != 0: errs.append(f"FOUNDER_TRANSPORT:{k}={m.get(k)}")

ver = json.loads((pkg/"verification_results.json").read_text()) if (pkg/"verification_results.json").exists() else {}
if not ver.get("independent"): errs.append("VERIFICATION_NOT_INDEPENDENT")
if ver.get("result") != "VERIFICATION_PASS": errs.append(f"VERIFICATION:{ver.get('result')}")

report = {"requirement":"REQ-TO-003","package":str(pkg.relative_to(ROOT)),
          "stages": {"proven": proven, "of": 7},
          "manual_intervention_metrics": m,
          "errors": errs, "status": "PASS" if not errs else "FAIL"}
OUT.parent.mkdir(parents=True, exist_ok=True)
body = json.dumps(report, indent=2, sort_keys=True) + "\n"
OUT.write_text(body)
print(f"stages proven: {proven}/7 | errors: {len(errs)}")
for e in errs[:8]: print("  ", e)
print("report sha256:", hashlib.sha256(body.encode()).hexdigest())
sys.exit(0 if not errs else 1)
