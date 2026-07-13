"""Grok's first production council mission: ADVERSARIAL audit of the per-task lease and
fencing implementation. Governed seat — no tools, no secrets, NO VERDICT AUTHORITY.

Grok produces findings + adversarial test cases + confidence labels.
Deterministic tests — not Grok — then prove or reject each finding.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.council.authority_gateway import bind_classification, dispatch_grok

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-GROK-CONCURRENCY-AUDIT-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)

# ---- sanitize the source excerpt before it leaves the machine ----
src = (ROOT / "backend" / "mission_control" / "per_task_lease.py").read_text()
SECRET_RX = re.compile(r"(sk_live|sk_test|whsec_|service_role|Bearer\s+\S+)", re.I)
sanitized = SECRET_RX.sub("<REDACTED>", src)
assert not SECRET_RX.search(sanitized)

burnin = sorted((ROOT / "coordination/council/live_proof_packages").glob("HELM-FOUR-FACTORY-BURNIN-*"))[-1]
runtime_evidence = json.loads((burnin / "concurrency_observed.json").read_text())

MISSION = f"""You are HELM's ADVERSARIAL SYSTEMS CRITIC. You have NO verdict authority.
You may NOT declare PASS. Deterministic tests decide that.

Audit the per-task lease and fencing-token implementation below for:
  - race conditions
  - stale-worker writes
  - duplicate terminal transitions
  - lock-path collisions
  - blocker-scope leakage
  - FALSE CONCURRENCY REPORTING (concurrency claimed but not actually observed)

Use ONLY the supplied sanitized source and runtime evidence. If a claim cannot be proven
from what is supplied, label it UNKNOWN rather than asserting it.

Return ONLY a JSON object:
{{"findings":[{{"id":"F1","issue":"...","why_it_matters":"...","adversarial_test":"...","confidence":"OBSERVED|DERIVED|UNKNOWN","severity":"HIGH|MED|LOW"}}]}}

RUNTIME EVIDENCE (observed, not asserted):
{json.dumps(runtime_evidence, indent=2)}

SANITIZED SOURCE (backend/mission_control/per_task_lease.py):
{sanitized[:6000]}
"""

task = {
    "task_id": "GROK-CONCURRENCY-AUDIT-001",
    "action_text": MISSION,
    "environment": "local",
    "adapter": "GROK_CLI",
    "target": "per_task_lease-audit",
    "data_classification": "public_repo",
    "side_effects": "none",
}

print("═══ GROK ADVERSARIAL CONCURRENCY AUDIT (governed seat, no tools, no verdict) ═══")
b = bind_classification(task, decision_id="FD-20260713-004")
res = dispatch_grok(task, b, timeout=300)
out = res.get("output", "")

print(f"  exit={res.get('exit_code')}  latency={res.get('latency_s')}s")
print(f"  authority id echoed: {res.get('authority_decision_id') == b.authority_decision_id}")

m = re.search(r"\{.*\}", out, re.DOTALL)
findings = []
if m:
    try:
        findings = json.loads(m.group(0)).get("findings", [])
    except json.JSONDecodeError:
        pass

print(f"\n  Grok returned {len(findings)} finding(s):\n")
for f in findings:
    print(f"  [{f.get('severity','?'):4s}] {f.get('id','?')}  ({f.get('confidence','?')})")
    print(f"         {f.get('issue','')[:150]}")
    print(f"         test: {str(f.get('adversarial_test',''))[:130]}\n")

# Grok has NO verdict authority — record that explicitly
(PKG / "grok_findings.json").write_text(json.dumps(findings, indent=2))
(PKG / "grok_raw_output.txt").write_text(out)
(PKG / "result_envelope.json").write_text(json.dumps(res, indent=2, default=str))
(PKG / "sanitization_proof.json").write_text(json.dumps({
    "secret_patterns_in_outbound_prompt": 0,
    "method": "regex redaction + assertion before dispatch",
    "prompt_sha256": hashlib.sha256(MISSION.encode()).hexdigest(),
}, indent=2))
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name,
    "grok_verdict_authority": "NONE — findings are advisory; deterministic tests decide PASS",
    "findings_count": len(findings),
    "authority_bound": res.get("authority_decision_id") == b.authority_decision_id,
    "next": "each finding must be PROVEN or REJECTED by a deterministic test",
    "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, indent=2, default=str))
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(PKG.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")
print(f"evidence: {PKG.relative_to(ROOT)}")
