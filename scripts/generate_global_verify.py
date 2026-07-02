#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "has_live_project_tracker" / "data"
EVIDENCE = ROOT / "docs" / "evidence" / "runtime"
DATA.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

now = datetime.now(timezone.utc).isoformat()

checks_to_run = [
    ("scope_lock", ["python3", "scripts/verify_has_hasf_scope_lock.py"]),
    ("local_runtime", ["python3", "scripts/check_local_has_runtime.py"]),
    ("frontier_gate", ["python3", "scripts/frontier_escalation_gate.py"]),
    ("fresh_pert", ["python3", "scripts/fresh_has_hasf_gap_pert_audit.py"]),
    ("visual_doctrine", ["python3", "scripts/verify_visual_authority_doctrine.py"]),
    ("workspace_hygiene", ["python3", "scripts/verify_workspace_visual_hygiene.py"]),
]

checks = []
overall = "PASS"

for check_id, cmd in checks_to_run:
    if not (ROOT / cmd[1]).exists():
        checks.append({
            "id": check_id,
            "command": " ".join(cmd),
            "ok": False,
            "returncode": None,
            "status": "NOT_PROVEN",
            "error": f"missing script {cmd[1]}",
        })
        overall = "DEGRADED"
        continue

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=90,
        )
        ok = result.returncode == 0
        if not ok:
            overall = "DEGRADED"
        checks.append({
            "id": check_id,
            "command": " ".join(cmd),
            "ok": ok,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-1500:],
            "stderr_tail": result.stderr[-1500:],
        })
    except Exception as exc:
        overall = "DEGRADED"
        checks.append({
            "id": check_id,
            "command": " ".join(cmd),
            "ok": False,
            "returncode": None,
            "error": str(exc),
        })

payload = {
    "telemetry_id": "global_verify",
    "generated_at": now,
    "last_verified_at": now,
    "owner_agent": "Global Verify Agent",
    "source_producer": "scripts/generate_global_verify.py",
    "freshness_sla_minutes": 30,
    "stale_state": "FRESH",
    "status": overall,
    "cost_to_refresh_estimate_usd": 0.0,
    "approval_required": False,
    "evidence_path": "docs/evidence/runtime/global_verify_latest.md",
    "next_action": "Continue scheduled telemetry refresh." if overall == "PASS" else "Inspect degraded verification checks.",
    "checks": checks,
}

(DATA / "global_verify.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

(EVIDENCE / "global_verify_latest.md").write_text(
    "# Global Verify Latest\n\n"
    f"- generated_at: `{now}`\n"
    f"- status: `{overall}`\n"
    f"- checks: `{len(checks)}`\n"
    f"- cost_to_refresh_estimate_usd: `0.0`\n",
    encoding="utf-8",
)

print(f"GLOBAL_VERIFY: {overall}")
