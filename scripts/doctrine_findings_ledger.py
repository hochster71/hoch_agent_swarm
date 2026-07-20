#!/usr/bin/env python3
"""doctrine_findings_ledger.py — append-only, hash-chained ledger of every Auditor finding.

HELM-GOV | extends: Evidence Doctrine + AU-9 hash-chain pattern | doctrine: Governance-before-Capability
         | edr: EDR-0006 §Verification | why: Founder directive — preserve EVERY Auditor finding
         | tamper-evidently; never delete a finding, only mark it resolved with corrective action +
         | evidence. Success = zero remaining findings, each eliminated with evidence (not a PASS bit).

Each record is cryptographically linked (prev_hash -> record_hash) so history cannot be rewritten.
Records are one of:
  FINDING     a defect the Auditor raised (id, source verdict path, severity, description)
  RESOLUTION  a corrective action for a finding (finding_id, action, evidence_paths, status)
Status of a finding = the status of its latest RESOLUTION record (OPEN until one exists).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "coordination" / "security" / "doctrine_findings_ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _last_hash() -> str:
    if not LEDGER.exists():
        return "GENESIS"
    lines = [l for l in LEDGER.read_text().splitlines() if l.strip()]
    return json.loads(lines[-1]).get("record_hash", "GENESIS") if lines else "GENESIS"


def append(record: dict) -> dict:
    prev = _last_hash()
    rec = {**record, "at": _now(), "prev_hash": prev}
    rec["record_hash"] = "sha256:" + hashlib.sha256(
        json.dumps(rec, sort_keys=True).encode()).hexdigest()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def verify_chain() -> tuple[bool, str]:
    """Recompute the hash chain; any tamper breaks it."""
    if not LEDGER.exists():
        return True, "empty"
    prev = "GENESIS"
    for i, ln in enumerate([l for l in LEDGER.read_text().splitlines() if l.strip()]):
        rec = json.loads(ln)
        if rec.get("prev_hash") != prev:
            return False, f"chain break at record {i}: prev_hash mismatch"
        body = {k: v for k, v in rec.items() if k != "record_hash"}
        expect = "sha256:" + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        if expect != rec.get("record_hash"):
            return False, f"chain break at record {i}: record_hash mismatch"
        prev = rec["record_hash"]
    return True, "intact"


def status_report() -> dict:
    """Current status of every finding = its latest RESOLUTION (OPEN if none)."""
    findings, resolutions = {}, {}
    if LEDGER.exists():
        for ln in [l for l in LEDGER.read_text().splitlines() if l.strip()]:
            rec = json.loads(ln)
            if rec.get("kind") == "FINDING":
                findings[rec["finding_id"]] = rec
            elif rec.get("kind") == "RESOLUTION":
                resolutions[rec["finding_id"]] = rec
    out = []
    for fid, f in findings.items():
        r = resolutions.get(fid)
        out.append({"finding_id": fid, "severity": f.get("severity"), "source": f.get("source"),
                    "description": f.get("description", "")[:90],
                    "status": (r or {}).get("status", "OPEN"),
                    "corrective_action": (r or {}).get("action", "")})
    open_n = sum(1 for x in out if x["status"] != "RESOLVED")
    return {"total": len(out), "open": open_n, "resolved": len(out) - open_n, "findings": out}


if __name__ == "__main__":
    ok, msg = verify_chain()
    rep = status_report()
    print(f"findings: {rep['total']}  resolved: {rep['resolved']}  OPEN: {rep['open']}  | chain: {msg}")
    for f in rep["findings"]:
        print(f"  [{f['status']:8s}] {f['finding_id']:8s} {f['severity']:9s} {f['description']}")
    sys.exit(0 if ok else 2)
