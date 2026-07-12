#!/usr/bin/env python3
"""REQ-GOV-005 — no completion metric may come from a fallback default.

Audit F-02.1: pert_server.py:1313 emitted 90.0 with source=autonomous_cadence_telemetry,
freshness=0.0s, confidence=HIGH whenever the source was missing.
Audit F-02.2: wrap_telemetry_dict stamped now() when a timestamp was absent.

This validator EXITS NON-ZERO while those exist. It is designed to fail today.
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "no_fake_green_report.json"

src = (ROOT / "backend" / "pert_server.py").read_text(encoding="utf-8")
# completion-ish metrics that carry a numeric fallback default
offenders = []
for m in re.finditer(r'compute_gap\.get\(\s*"([a-z_]*(?:percent|completion|confidence|remaining)[a-z_]*)"\s*,\s*([^)]+)\)', src):
    field, default = m.group(1), m.group(2).strip()
    if default not in ("None", "null"):
        offenders.append({"field": field, "fallback_default": default,
                          "line": src[:m.start()].count("\n") + 1})
now_stamp = 'if not last_updated_iso:' in src and 'datetime.now(timezone.utc).isoformat()' in src
report = {
    "requirement": "REQ-GOV-005",
    "fallback_completion_defaults": offenders,
    "missing_timestamp_stamps_now": now_stamp,
    "status": "PASS" if (not offenders and not now_stamp) else "FAIL",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(f"fallback completion defaults: {len(offenders)} | missing-timestamp->now(): {now_stamp}")
sys.exit(0 if report["status"] == "PASS" else 1)
