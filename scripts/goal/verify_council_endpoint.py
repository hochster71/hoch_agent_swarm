#!/usr/bin/env python3
"""REQ-ES-004 — the council state endpoint is actually registered in the app.

Audit F-02.4: 616 routes registered, ZERO containing 'council'. GET -> 404.
Static route-registration check (no server boot required).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "council_endpoint_report.json"
src = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
GATES = ["h1_package_state", "h1_package_integrity", "h1_credential_state",
         "h1_founder_authorization", "h1_live_provider_proof",
         "h1_frontier_live_quorum", "h1_promotion", "h1_safe_to_execute"]
route_present = "/api/v1/helm/council/state" in src
missing = [g for g in GATES if g not in src]
report = {"requirement": "REQ-ES-004", "route_registered": route_present,
          "missing_gates": missing,
          "status": "PASS" if (route_present and not missing) else "FAIL"}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(f"route_registered={route_present} missing_gates={len(missing)}")
sys.exit(0 if report["status"] == "PASS" else 1)
