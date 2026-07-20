#!/usr/bin/env python3
"""governance_health.py — constitutional health metrics (EDR-0010 §Evidence).

Founder rule, 2026-07-20: report constitutional health, not raw assertion counts.
A test total is an activity measure; these are integrity measures.

DENOMINATOR INTEGRITY
---------------------
A pass rate is gameable by adding trivial passing tests, exactly as the north-star 100%
was reachable by excluding founder-gated requirements from its denominator. So every
rate here is emitted WITH its denominator and its scope. A percentage without those is
not reported.

UNKNOWN PROPAGATES
------------------
Metrics that cannot currently be evaluated return None with a reason — never 0, never a
default. Promotion Eligibility in particular depends on evidence freshness, which
W1-002_PRECLAIM established is forged repo-wide; it therefore reports UNKNOWN until
REQ-ES-004 lands. A readiness metric that renders a number while its own inputs are
untrustworthy is the defect this file exists to avoid.

Usage:
    python3 scripts/governance_health.py           # table
    python3 scripts/governance_health.py --json    # machine-readable
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EDR_DIR = ROOT / "docs" / "helm" / "edr"
GOV_TEST = ROOT / "tests" / "unit" / "test_governance_preclaim.py"

CONSTITUTIONAL = [
    "HELM_CONSTITUTION", "HELM_DESIGN_CONSTITUTION", "COUNCIL_RUNTIME_CHARTER",
    "HELM_CANONICAL_RUNTIME", "CONTROL_SURFACE_MAP",
]

# Assertion suites grouped by the governance layer they defend.
LAYERS = {
    "constitutional": ["tests/unit/test_governance_preclaim.py"],
    "evidence_truth": ["tests/unit/test_mission_envelope.py",
                       "tests/unit/test_collectors.py"],
    "delivery": ["tests/unit/test_integration_state.py"],
    "trust_boundary": ["tests/unit/test_kimi_redaction_gaps.py"],
    "provenance_wip": ["tests/unit/test_w1_002a_collector_provenance.py",
                       "tests/unit/test_w1_002b_endpoint_provenance.py",
                       "tests/unit/test_w1_002c_verifier_burndown_provenance.py"],
}


# Two ways mtime becomes produced-time. The first version of this detector caught only
# the arithmetic form and MISSED the conversion form — so it reported 22 offenders while
# collectors.py held two it could not see. A detector with a blind spot is the same
# defect class it detects; both forms are matched now.
_MTIME_ARITHMETIC = ("time.time()", "now()", "fresh", "age", "utcfromtimestamp")
_MTIME_CONVERSION = ("fromtimestamp", "datetime.")


def _is_mtime_as_produced_time(line: str) -> bool:
    """True when a line turns filesystem mtime into a timestamp or an age.

    Excluded by design (per the founder classification rule): mtime used for cache
    invalidation, sorting, or clearly-labelled file metadata.
    """
    if "st_mtime" not in line:
        return False
    if "mtime-metadata-ok" in line:
        # Explicit, greppable waiver. Auditable: `rg "mtime-metadata-ok"` lists
        # every place a filesystem timestamp is knowingly kept as metadata.
        return False
    if "_file_mtime" in line or "file_modified_at" in line:
        return False  # explicitly labelled metadata, not produced-time
    return (any(k in line for k in _MTIME_ARITHMETIC)
            or any(k in line for k in _MTIME_CONVERSION))


def _metric(value: Any, denominator: Optional[str] = None, scope: str = "",
            reason: str = "") -> Dict[str, Any]:
    """A metric is a value plus what it was measured against. Never a bare number."""
    return {"value": value, "denominator": denominator, "scope": scope,
            "reason": reason, "known": value is not None}


def _edrs():
    return sorted(EDR_DIR.glob("EDR-*.md")) if EDR_DIR.exists() else []


def _pytest(paths: list) -> Optional[Dict[str, int]]:
    existing = [p for p in paths if (ROOT / p).exists()]
    if not existing:
        return None
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", *existing, "-q",
                            "--no-header", "-p", "no:cacheprovider"],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
    except Exception:
        return None
    out = r.stdout + r.stderr
    got = {}
    for tok in ("passed", "failed", "xfailed", "skipped", "error"):
        m = re.search(rf"(\d+) {tok}", out)
        got[tok] = int(m.group(1)) if m else 0
    return got


# --- the six metrics ----------------------------------------------------------

def governance_verification_pass_rate() -> Dict[str, Any]:
    res = _pytest(LAYERS["constitutional"])
    if res is None:
        return _metric(None, reason="governance suite not present")
    total = res["passed"] + res["failed"] + res["xfailed"]
    if total == 0:
        return _metric(None, reason="no governance assertions executed")
    return _metric(
        round(100.0 * res["passed"] / total, 1),
        denominator=f"{res['passed']}/{total} (xfail counted as not-passing)",
        scope="constitutional layer only",
        reason=f"{res['failed']} failing, {res['xfailed']} grandfathered",
    )


def grandfathered_debt_count() -> Dict[str, Any]:
    if not GOV_TEST.exists():
        return _metric(None, reason="governance test absent")
    src = GOV_TEST.read_text(encoding="utf-8")
    m = re.search(r"GRANDFATHERED\s*=\s*\{(.*?)\}", src, re.S)
    if not m:
        return _metric(None, reason="GRANDFATHERED set not found")
    n = len([x for x in re.findall(r'"([^"]+\.md)"', m.group(1))])
    return _metric(n, denominator=f"{len(_edrs())} EDRs",
                   scope="pre-claim debt", reason="must decrease monotonically")


def duplicate_identifier_count() -> Dict[str, Any]:
    by_id = defaultdict(list)
    for p in _edrs():
        mm = re.match(r"(EDR-\d+)", p.name)
        by_id[mm.group(1) if mm else p.stem].append(p.name)
    dupes = {k: v for k, v in by_id.items() if len(v) > 1}
    return _metric(len(dupes), denominator=f"{len(by_id)} distinct IDs",
                   scope="traceability",
                   reason="; ".join(f"{k}: {', '.join(v)}" for k, v in dupes.items())
                   or "all identifiers resolve uniquely")


def constitution_citation_coverage() -> Dict[str, Any]:
    edrs = _edrs()
    if not edrs:
        return _metric(None, reason="no EDRs found")
    cited = [p for p in edrs
             if any(c in p.read_text(encoding="utf-8") for c in CONSTITUTIONAL)]
    return _metric(round(100.0 * len(cited) / len(edrs), 1),
                   denominator=f"{len(cited)}/{len(edrs)} EDRs",
                   scope="amendment discipline",
                   reason="uncited records assume repository state")


def assertion_coverage_by_layer() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for layer, paths in LAYERS.items():
        res = _pytest(paths)
        if res is None:
            out[layer] = {"known": False, "reason": "suite absent"}
            continue
        out[layer] = {
            "known": True, "passed": res["passed"], "failed": res["failed"],
            "xfailed": res["xfailed"],
            "intent": ("red-by-design: defines unbuilt work"
                       if layer == "provenance_wip" else "must stay green"),
        }
    return _metric(out, denominator="7 suites", scope="verification completeness")


def promotion_eligibility() -> Dict[str, Any]:
    """UNKNOWN by construction until evidence freshness is trustworthy.

    Champion/challenger comparison is meaningless when either candidate's evidence can
    appear newer via a filesystem touch. Reporting a readiness number here would be the
    exact substitution EDR-0010 prohibits.
    """
    offenders = 0
    for rel in ("backend/helm_live_api.py", "scripts/verify_runtime_truth_freshness.py",
                "scripts/goal/goal_engine.py", "scripts/goal/verify_champion_gates.py",
                "backend/helm_runtime/collectors.py"):
        p = ROOT / rel
        if not p.exists():
            continue
        offenders += sum(1 for ln in p.read_text(encoding="utf-8").splitlines()
                         if _is_mtime_as_produced_time(ln))
    if offenders:
        return _metric(
            None, denominator=f"{offenders} mtime-as-produced-time sites remain",
            scope="P0 freshness paths",
            reason="promotion depends on freshness; freshness is forgeable until "
                   "W1-002a-c and REQ-ES-004 land. UNKNOWN, not zero, not ready.",
        )
    return _metric("ELIGIBLE_PENDING_AUDIT", denominator="0 offending sites",
                   scope="P0 freshness paths",
                   reason="freshness paths clean; Auditor verification still required")


def collect() -> Dict[str, Any]:
    return {
        "schema": "HELM_GOVERNANCE_HEALTH_v1",
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": {
            "governance_verification_pass_rate": governance_verification_pass_rate(),
            "grandfathered_debt_count": grandfathered_debt_count(),
            "duplicate_identifier_count": duplicate_identifier_count(),
            "constitution_citation_coverage": constitution_citation_coverage(),
            "assertion_coverage_by_layer": assertion_coverage_by_layer(),
            "promotion_eligibility": promotion_eligibility(),
        },
    }


def main() -> int:
    d = collect()
    if "--json" in sys.argv:
        print(json.dumps(d, indent=2))
        return 0
    print(f"HELM CONSTITUTIONAL HEALTH — {d['computed_at']}")
    print("=" * 74)
    for name, m in d["metrics"].items():
        if name == "assertion_coverage_by_layer":
            print(f"\n{name}")
            for layer, v in m["value"].items():
                if not v.get("known"):
                    print(f"    {layer:<18} UNKNOWN — {v['reason']}")
                else:
                    print(f"    {layer:<18} {v['passed']:>3}P {v['failed']:>3}F "
                          f"{v['xfailed']:>2}X   {v['intent']}")
            continue
        val = m["value"] if m["known"] else "UNKNOWN"
        print(f"\n{name}\n    value: {val}")
        if m.get("denominator"):
            print(f"    of:    {m['denominator']}")
        if m.get("reason"):
            print(f"    note:  {m['reason']}")
    print("\n" + "=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
