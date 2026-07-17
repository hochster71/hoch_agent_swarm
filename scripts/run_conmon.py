#!/usr/bin/env python3
"""HELM Continuous Monitoring runner (ConMon · NIST SP 800-137).

Runs the control-posture assessment and writes a timestamped evidence snapshot to
coordination/security/conmon_status.json, plus a drift line vs the previous snapshot.
Designed to run on a schedule (launchd/cron). Per EDR-0005 it EMITS EVIDENCE — it does
NOT create git commits. No fake green: posture is whatever assess() computes.

Usage: python3 scripts/run_conmon.py   (schedule via deploy/com.hoch.helm-conmon.plist)
"""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # allow `import backend.*` when run standalone
OUT = ROOT / "coordination" / "security" / "conmon_status.json"
HIST = ROOT / "coordination" / "security" / "conmon_history.jsonl"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run() -> dict:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    from backend.security.helm_conmon import assess
    a = assess()
    snap = {
        "schema": "HELM_CONMON_STATUS_v1",
        "ran_at": _now(),
        "framework": a.get("framework"),
        "conmon_standard": a.get("conmon_standard"),
        "posture_percent": a.get("posture_percent"),
        "controls_assessed": a.get("controls_assessed"),
        "implemented": a.get("implemented"),
        "not_implemented": a.get("not_implemented"),
        "unknown": a.get("unknown"),
        "open_findings": a.get("open_findings"),
        "high_findings": a.get("high_findings"),
    }
    # drift vs previous
    if prev:
        dp = (snap.get("posture_percent") or 0) - (prev.get("posture_percent") or 0)
        snap["drift"] = {
            "posture_delta": round(dp, 2),
            "high_findings_delta": (snap.get("high_findings") or 0) - (prev.get("high_findings") or 0),
            "since": prev.get("ran_at"),
        }
    OUT.write_text(json.dumps(snap, indent=2) + "\n")
    with open(HIST, "a") as f:
        f.write(json.dumps({"ran_at": snap["ran_at"], "posture_percent": snap["posture_percent"],
                            "high_findings": snap["high_findings"]}) + "\n")
    return snap


if __name__ == "__main__":
    s = run()
    d = s.get("drift", {})
    print(f"ConMon: posture {s['posture_percent']}% · {s['controls_assessed']} controls · "
          f"high={s['high_findings']} · drift {d.get('posture_delta','—')} → {OUT}")
