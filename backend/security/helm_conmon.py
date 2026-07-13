"""HELM ConMon — NIST SP 800-137 Continuous Monitoring, run against HELM ITSELF.

This is GOVFRAME-003 (the ConMon agent) turned inward.

It executes every control assessor in the catalog against LIVE evidence, computes a
control posture, and emits a POA&M (Plan of Action & Milestones) for every gap.

WHAT MAKES THIS DIFFERENT FROM A COMPLIANCE DASHBOARD
-----------------------------------------------------
Most compliance dashboards read a spreadsheet of self-attestations and render green
squares. That is a fabricated PASS with a nicer font. This one RE-DERIVES posture from
the running system every single cycle:

  * AU-9  is IMPLEMENTED only if the hash chains actually verify, right now.
  * SC-7  is IMPLEMENTED only if the AST egress scanner actually passes, right now.
  * CM-3  goes NOT_IMPLEMENTED the moment uncommitted code appears -- because evidence
          cannot bind to a commit that does not contain the code under test.
  * CP-10 is IMPLEMENTED only if a real SIGKILL recovery was observed with a monotonic
          fencing token.

A control that cannot be proven is a FINDING, not a rounding error. The posture score
counts ONLY controls whose assessor observed the evidence. UNKNOWN contributes zero --
exactly like the goal engine.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CONMON_DIR = ROOT / "coordination" / "security"
POSTURE = CONMON_DIR / "helm_control_posture.json"
CONMON_LEDGER = CONMON_DIR / "conmon_ledger.jsonl"

IMPLEMENTED = "IMPLEMENTED"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
UNKNOWN = "UNKNOWN"

SEVERITY = {  # a missing control is not equally bad everywhere
    "SC-7": "HIGH", "AU-9": "HIGH", "IA-2": "HIGH", "AC-3": "HIGH", "AC-6": "HIGH",
    "CM-3": "MODERATE", "CP-10": "MODERATE", "SI-4": "MODERATE", "AU-2": "MODERATE",
    "RA-5": "MODERATE", "SA-11": "MODERATE", "CA-7": "MODERATE", "SR-3": "MODERATE",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def assess() -> Dict[str, Any]:
    from backend.security.helm_control_catalog import CONTROLS

    results: List[Dict[str, Any]] = []
    for c in CONTROLS:
        try:
            r = c["fn"]()
        except Exception as e:  # an assessor that crashes is UNKNOWN, never satisfied
            r = {"status": UNKNOWN, "evidence": "assessor raised", "detail": str(e)[:140]}
        results.append({
            "control_id": c["id"], "family": c["family"], "title": c["title"],
            "status": r["status"], "evidence": r["evidence"], "detail": r.get("detail", ""),
            "severity": SEVERITY.get(c["id"], "MODERATE"),
            "assessed_at": _now(),
        })

    impl = [r for r in results if r["status"] == IMPLEMENTED]
    gaps = [r for r in results if r["status"] == NOT_IMPLEMENTED]
    unk = [r for r in results if r["status"] == UNKNOWN]

    # POA&M: every gap becomes a tracked, dated item. This is the deliverable an
    # assessor actually asks for.
    poam = [{
        "poam_id": f"POAM-{r['control_id']}",
        "control_id": r["control_id"], "title": r["title"],
        "weakness": r["evidence"], "detail": r["detail"],
        "severity": r["severity"],
        "status": "OPEN",
        "identified_at": r["assessed_at"],
        "source": "HELM ConMon (NIST SP 800-137) — automated, evidence-derived",
    } for r in gaps + unk]

    total = len(results)
    posture = {
        "schema": "HELM_CONTROL_POSTURE_v1",
        "framework": "NIST SP 800-53 Rev. 5",
        "conmon_standard": "NIST SP 800-137",
        "assessed_at": _now(),
        "target_system": "HELM / Hoch Agent Swarm",
        "controls_assessed": total,
        "implemented": len(impl),
        "not_implemented": len(gaps),
        "unknown": len(unk),
        # UNKNOWN contributes ZERO. Absence of evidence is never partial credit.
        "posture_percent": round(100.0 * len(impl) / total, 1) if total else 0.0,
        "open_findings": len(poam),
        "high_findings": len([p for p in poam if p["severity"] == "HIGH"]),
        "controls": results,
        "poam": poam,
        "doctrine": ("posture is RE-DERIVED from live evidence every cycle; a control that "
                     "cannot be proven right now is a FINDING, not a green square"),
    }

    CONMON_DIR.mkdir(parents=True, exist_ok=True)
    POSTURE.write_text(json.dumps(posture, indent=2) + "\n")

    # hash-chained ConMon history — you can prove what your posture was on any date
    prev = "GENESIS"
    if CONMON_LEDGER.exists():
        lines = [l for l in CONMON_LEDGER.read_text().splitlines() if l.strip()]
        if lines:
            prev = json.loads(lines[-1]).get("entry_hash", "GENESIS")
    entry = {
        "ts": posture["assessed_at"],
        "posture_percent": posture["posture_percent"],
        "implemented": posture["implemented"],
        "open_findings": posture["open_findings"],
        "high_findings": posture["high_findings"],
        "gaps": [g["control_id"] for g in gaps + unk],
        "prev_hash": prev,
    }
    entry["entry_hash"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True).encode()).hexdigest()
    with open(CONMON_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

    return posture


def main() -> int:
    p = assess()
    print(f"HELM ConMon — NIST 800-53 Rev.5 posture (assessed live)\n")
    for c in p["controls"]:
        mark = {"IMPLEMENTED": "PASS", "NOT_IMPLEMENTED": "GAP ", "UNKNOWN": "UNK "}[c["status"]]
        print(f"  [{mark}] {c['control_id']:6s} {c['title'][:44]:46s} {c['evidence'][:44]}")
    print(f"\n  posture      : {p['posture_percent']}%  ({p['implemented']}/{p['controls_assessed']} implemented)")
    print(f"  open findings: {p['open_findings']}  (HIGH: {p['high_findings']})")
    for x in p["poam"]:
        print(f"    {x['poam_id']:12s} {x['severity']:8s} {x['weakness'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
