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


# HELM-GOV | extends: N8 ConMon (this module) | doctrine: Governance-before-Capability
#          | edr: EDR-0006-R7 | why: governance is MONITORED, not asserted — coverage is re-derived
#          | from the live event bus every cycle and a POA&M is raised below target (maps to CA-7).
EVENTS_LEDGER = ROOT / "coordination" / "events" / "helm_events.jsonl"
ADOPTION_RECORD = ROOT / "coordination" / "governance" / "engineering_doctrine_adoption.json"
GOVERNANCE_COVERAGE_TARGET = 1.0  # AC-1: 100% of NEW material decisions carry a valid Proof Record
# Coverage is measured by EVENT SEMANTICS, not a producer allowlist (Auditor finding F-B2: a producer
# allowlist can hide ungoverned material work). ANY event whose type is a governance decision / material
# state advancement MUST carry a gate-valid Proof Record. New types are caught by the prefix rule.
_GOVERNANCE_EVENT_TYPES = frozenset({
    "COUNCIL_DISPATCH", "COUNCIL_VERDICT", "COUNCIL_VERIFY_DONE", "COUNCIL_VERIFY_BLOCKED",
    "AUDIT_RESULT", "COUNCIL_BUILD", "MISSION_TRANSACTION_COMMITTED", "KNOWLEDGE_INGESTED",
})
_GOVERNANCE_EVENT_PREFIXES = ("COUNCIL_", "GOAL_NODE_")  # decisions + material state advancement


def _is_governance_event(ev_type: str) -> bool:
    return ev_type in _GOVERNANCE_EVENT_TYPES or any(ev_type.startswith(p) for p in _GOVERNANCE_EVENT_PREFIXES)


GOVERNED_RUNTIME_LIVE = ROOT / "coordination" / "governance" / "governed_runtime_live.json"


def _adoption_cutoff() -> str:
    """The instant from which the LIVE runtime is expected to be governed. This is the LATER of:
      - doctrine adoption (`engineering_doctrine_adoption.json`), and
      - governed-runtime-live (`governed_runtime_live.json`) — the controlled daemon restart after
        which the running code emits Proof Records.
    Council decisions emitted BEFORE this by stale (ungoverned) code are legacy (Phase-2
    classification), not fresh governance failures. Fail-open to '' (count everything) if absent."""
    cutoffs = []
    for f, key in ((ADOPTION_RECORD, "adopted_at"), (GOVERNED_RUNTIME_LIVE, "governed_runtime_live_at")):
        try:
            cutoffs.append(json.loads(f.read_text(encoding="utf-8")).get(key, ""))
        except Exception:
            pass
    return max([c for c in cutoffs if c], default="")


def governance_coverage(sample: int = 1000) -> Dict[str, Any]:
    """Re-derive governance coverage from the last `sample` events. Honest + fail-open:

      carry_rate  = of NEW material decisions (>= adoption) from governed producers, fraction
                    carrying a Proof Record
      governed_rate = of those carrying one, fraction classified GOVERNED
    A carry_rate below target is a FINDING (POA&M) — not a rounding error. No events ⇒ UNKNOWN.
    Legacy (pre-adoption) events are excluded — they are Phase-2 classification work, not failures.
    """
    if not EVENTS_LEDGER.exists():
        return {"state": UNKNOWN, "reason": "no event ledger yet", "material": 0}
    # RE-VALIDATE through the single gate — never trust the event's self-asserted governance_state
    # (Auditor finding B1). "carrying" = carries a SCHEMA-VALID Proof Record; "governed" = the GATE
    # (govern_decision) independently classifies it GOVERNED from its fields, not from a written string.
    from backend.helm_runtime.extensions.constitutional_gate import govern_decision
    from backend.helm_runtime.governance_manifest import validate as _validate

    cutoff = _adoption_cutoff()
    lines = [l for l in EVENTS_LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    material = carrying = governed = legacy_excluded = 0
    for ln in lines[-sample:]:
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not _is_governance_event(str(ev.get("type", ""))):
            continue  # only governance-decision / state-advancement events count (by semantics, not producer)
        if cutoff and str(ev.get("timestamp", "")) < cutoff:
            legacy_excluded += 1
            continue  # pre-adoption legacy decision — Phase-2 classification, not a Phase-1 failure
        material += 1
        # Dual-encoding read (A7 remediation): historical top-level (drifted-core era) OR
        # payload["proof_record"] (composed extension). CONFLICTING encodings fail closed —
        # the event counts as NOT carrying a record (an ambiguous proof proves nothing) and
        # is therefore an explicit coverage finding, never an optimistic merge.
        _pr_top = ev.get("proof_record")
        _pr_pl = (ev.get("payload") or {}).get("proof_record")
        if _pr_top is not None and _pr_pl is not None and _pr_top != _pr_pl:
            pr = None  # INTEGRITY: conflicting proof encodings
        else:
            pr = _pr_top if _pr_top is not None else _pr_pl
        if isinstance(pr, dict) and _validate(pr)[0]:      # schema-valid record, not just any dict
            carrying += 1
            if govern_decision(pr).governance_state == "GOVERNED":  # GATE re-validates; ignores self-asserted field
                governed += 1
    if material == 0:
        return {"state": UNKNOWN, "reason": "no NEW (post-adoption) governed-producer decisions yet",
                "material": 0, "legacy_excluded": legacy_excluded, "cutoff": cutoff}
    carry_rate = round(carrying / material, 4)
    governed_rate = round(governed / carrying, 4) if carrying else 0.0
    below = carry_rate < GOVERNANCE_COVERAGE_TARGET
    return {
        "state": NOT_IMPLEMENTED if below else IMPLEMENTED,
        "material_decisions": material,
        "carrying_proof_record": carrying,
        "governed": governed,
        "carry_rate": carry_rate,
        "governed_rate": governed_rate,
        "target": GOVERNANCE_COVERAGE_TARGET,
        "legacy_excluded": legacy_excluded,
        "cutoff": cutoff,
        "sample_window": min(sample, len(lines)),
        "doctrine": "EDR-0006-R7: every NEW material decision must carry a valid Proof Record",
    }


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
    # Sample posture only — never claim full 800-53 catalog coverage (audit R-03).
    sample_pct = round(100.0 * len(impl) / total, 1) if total else 0.0

    # EDR-0006-R7: continuous governance proof, re-derived from the live event bus this cycle.
    gov = governance_coverage()
    if gov.get("state") == NOT_IMPLEMENTED:
        poam.append({
            "poam_id": "POAM-GOV-COVERAGE",
            "control_id": "CA-7", "title": "Governance coverage below target",
            "severity": "HIGH",
            "weakness": (f"carry_rate {gov.get('carry_rate')} < target {gov.get('target')}: "
                         f"{gov.get('material_decisions')} governed-producer decisions, "
                         f"{gov.get('carrying_proof_record')} carry a Proof Record"),
            "remediation": "ensure every material decision emits a Proof Record via govern_decision",
        })

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
        "posture_percent": sample_pct,
        "posture_percent_scope": "SAMPLED_CONTROLS_ONLY",
        "full_nist_800_53_coverage": False,
        "catalog_scope_note": (
            f"posture_percent is {sample_pct}% of {total} continuously assessed HELM controls, "
            "NOT percent of the full NIST SP 800-53 Rev. 5 catalog. Do not cite as ATO posture."
        ),
        "open_findings": len(poam),
        "high_findings": len([p for p in poam if p["severity"] == "HIGH"]),
        "controls": results,
        "poam": poam,
        "governance_coverage": gov,  # EDR-0006-R7 continuous proof
        "doctrine": ("posture is RE-DERIVED from live evidence every cycle; a control that "
                     "cannot be proven right now is a FINDING, not a green square; "
                     "sample percent is never full-catalog coverage"),
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
        "governance_carry_rate": gov.get("carry_rate"),   # EDR-0006-R7/AC-4 trend across cycles
        "governance_state": gov.get("state"),
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
