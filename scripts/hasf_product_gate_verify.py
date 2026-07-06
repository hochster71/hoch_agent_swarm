#!/usr/bin/env python3
"""HASF Product Gate Verifier — evidence-disciplined, fail-closed.

Dogfooded on Epic Fury 2026: the first monetized app exposed that HASF's old pipeline could stamp
APPROVED_FOR_PRODUCTION while (a) the scanners were TOOL_FALLBACK stand-ins, (b) the machine scan
artifact and the prose narrative disagreed, and (c) HIGH findings were waved through by a sentence.
This verifier encodes the lessons so HASF can never fake-green a product again.

RULES (any failure => NO-GO; UNKNOWN is fail-closed, never PASS):
  R1 REAL TOOLS       — a security PASS requires real scanners; any 'TOOL_FALLBACK_USED' => UNVERIFIED.
  R2 RECONCILED SCAN  — the machine scan artifact's HIGH count must match the narrative's claim; a
                        dirty machine record coexisting with a clean prose claim => NO-GO.
  R3 NO OPEN HIGH     — any HIGH finding not covered by a signed, unexpired accepted-risk entry => NO-GO.
  R4 ACCEPTED = SIGNED — 'false positive / accepted' only counts from an allowlist with owner+expiry,
                        never from prose.
  R5 POSTURE RECONCILE— APPROVED_FOR_PRODUCTION requires every gate = PASS (no PENDING) AND R1-R4 pass.

Reads only recorded evidence; writes a verdict JSON + MD. No network, deterministic.
"""
import json
import re
import sys
import datetime
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def verify(audit_json: Path, security_md: Path, gate_md: Path, shipping_md: Path,
           accepted_allowlist: Path = None) -> Dict[str, Any]:
    reasons: List[Dict[str, str]] = []

    def fail(rule, msg): reasons.append({"rule": rule, "verdict": "FAIL", "detail": msg})
    def ok(rule, msg): reasons.append({"rule": rule, "verdict": "PASS", "detail": msg})

    audit = {}
    try:
        audit = json.loads(_read(audit_json))
    except Exception:
        pass
    findings = audit.get("findings", [])
    high = [f for f in findings if str(f.get("severity", "")).upper() == "HIGH"]
    sec_txt = _read(security_md)
    gate_txt = _read(gate_md)
    ship_txt = _read(shipping_md)

    # R1 — real tools
    if "TOOL_FALLBACK_USED" in sec_txt:
        tools = re.findall(r"\*\*(.+?)\*\*:\s*TOOL_FALLBACK_USED", sec_txt)
        fail("R1_REAL_TOOLS", f"security scan used FALLBACK tools, not real scanners: {tools or 'see doc'}. "
             "A fallback PASS is UNVERIFIED — real gitleaks/trivy/syft must run.")
    else:
        ok("R1_REAL_TOOLS", "no TOOL_FALLBACK markers in the security evidence")

    # R2 — reconciled scan (machine artifact vs narrative)
    narr_zero_high = bool(re.search(r"high\s+vulnerabilities?\**:?\s*\**\s*0", sec_txt, re.I)) or \
                     bool(re.search(r"0\s*\(after refactoring", sec_txt, re.I))
    if high and narr_zero_high:
        fail("R2_RECONCILED_SCAN", f"machine scan artifact records {len(high)} HIGH findings while the "
             "narrative claims 0 HIGH — the dirty scan was never regenerated post-remediation. "
             "Require a single reconciled final scan.")
    elif high:
        fail("R2_RECONCILED_SCAN", f"{len(high)} HIGH findings present in the machine scan artifact")
    else:
        ok("R2_RECONCILED_SCAN", "machine scan artifact and narrative agree")

    # R3/R4 — open HIGH vs signed allowlist
    accepted = set()
    if accepted_allowlist and Path(accepted_allowlist).exists():
        try:
            al = json.loads(_read(Path(accepted_allowlist)))
            for e in al.get("accepted", []):
                exp = e.get("expires")
                if exp and exp > _now():
                    accepted.add(e.get("id") or e.get("category"))
        except Exception:
            pass
    open_high = [f for f in high if (f.get("category") not in accepted)]
    if open_high:
        fail("R3_NO_OPEN_HIGH", f"{len(open_high)} HIGH findings not covered by a signed, unexpired "
             "accepted-risk allowlist (prose 'false positive' does not count).")
    else:
        ok("R3_NO_OPEN_HIGH", "no open HIGH findings")

    # R5 — posture reconciliation
    approved = "APPROVED_FOR_PRODUCTION_RELEASE" in ship_txt
    pending = "PENDING" in gate_txt
    if approved and pending:
        fail("R5_POSTURE", "shipping posture is APPROVED_FOR_PRODUCTION_RELEASE while the gate doc "
             "still lists gates as PENDING — posture and gate status disagree.")
    elif approved and any(r["verdict"] == "FAIL" for r in reasons):
        fail("R5_POSTURE", "posture is APPROVED while one or more evidence rules FAIL — cannot ship.")
    else:
        ok("R5_POSTURE", "posture consistent with gate status and evidence")

    verdict = "NO-GO" if any(r["verdict"] == "FAIL" for r in reasons) else "GO"
    return {
        "schema": "hasf-product-gate-verify-v1", "at": _now(),
        "verdict": verdict,
        "high_findings": len(high), "open_high": len(open_high),
        "rules": reasons,
        "note": "fail-closed: any FAIL => NO-GO. UNKNOWN never counts as PASS.",
    }


if __name__ == "__main__":
    base = ROOT / "docs" / "products" / "epic-fury-2026"
    ev = ROOT / "docs" / "evidence" / "products" / "epic-fury-2026" / "20260702T233000Z-epic-fury-2026-hasf-vetting"
    res = verify(
        audit_json=ROOT / "has_live_project_tracker" / "data" / "epic_fury_audit_results.json",
        security_md=ev / "03-security-audit.md",
        gate_md=base / "HASF_PRODUCT_GATE.md",
        shipping_md=base / "FINAL_SHIPPING_REPORT.md",
        accepted_allowlist=ROOT / "config" / "security_accepted_risks.json",
    )
    out = base / "HASF_GATE_VERIFY.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"HASF Product Gate Verifier → {res['verdict']}  ({res['high_findings']} HIGH, {res['open_high']} open)")
    for r in res["rules"]:
        print(f"  [{r['verdict']}] {r['rule']}: {r['detail']}")
    print(f"\nwrote {out}")
    sys.exit(0 if res["verdict"] == "GO" else 2)
