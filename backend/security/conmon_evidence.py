"""HELM ConMon — evidence bundle emitter (NIST SP 800-53 Rev. 5 / SP 800-137).

The ConMon engine (`helm_conmon.assess`) re-derives control posture from live evidence
and writes machine state under `coordination/security/`. THIS module is the assessor-facing
evidence side: every cycle it emits a fresh, timestamped, human-readable evidence bundle
under `docs/evidence/conmon/` — the artifact an auditor actually opens.

WHAT IT WRITES (per cycle)
--------------------------
  docs/evidence/conmon/conmon_posture_<ts>.json   full posture snapshot (as assessed)
  docs/evidence/conmon/conmon_posture_<ts>.md     control-by-control posture report
  docs/evidence/conmon/latest.json                pointer to the newest bundle
  docs/evidence/conmon/NIST_800-53_REV5_CONTROL_MAP.md   current control→assessor map

The control map is REGENERATED every cycle straight from the live catalog, so the Rev. 5
mappings in the evidence tree can never drift away from the mappings the engine actually
runs. No fake green: this module only serializes what `assess()` observed — it never
upgrades a status or invents a mapping the engine did not evaluate.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "evidence" / "conmon"

_STATUS_MARK = {
    "IMPLEMENTED": "PASS",
    "NOT_IMPLEMENTED": "GAP",
    "UNKNOWN": "UNK",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(iso: str) -> str:
    """Compact, filesystem-safe stamp derived from an ISO timestamp.

    Falls back to wall-clock now if the assessed_at string is missing/unparseable, so an
    evidence file always gets a unique, sortable name.
    """
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})", iso or "")
    if m:
        return "".join(m.groups()) [:8] + "T" + "".join(m.groups())[8:] + "Z"
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_controls() -> List[Dict[str, Any]]:
    """Live control catalog — the source of truth for current Rev. 5 mappings."""
    from backend.security.helm_control_catalog import CONTROLS
    return CONTROLS


def _control_map_md(posture: Dict[str, Any]) -> str:
    """Regenerate the NIST 800-53 Rev. 5 control-mapping table from the live catalog.

    Statuses come from THIS cycle's posture so the map doubles as a coverage snapshot.
    """
    by_id = {c["control_id"]: c for c in posture.get("controls", [])}
    lines = [
        "# HELM — NIST SP 800-53 Rev. 5 Control Mapping (ConMon)",
        "",
        "> Regenerated every ConMon cycle from `backend/security/helm_control_catalog.py`.",
        "> Each control carries an EXECUTABLE assessor; status below is this cycle's live result.",
        "",
        f"- Framework: **{posture.get('framework', 'NIST SP 800-53 Rev. 5')}**",
        f"- ConMon standard: **{posture.get('conmon_standard', 'NIST SP 800-137')}**",
        f"- Target system: **{posture.get('target_system', 'HELM / Hoch Agent Swarm')}**",
        f"- Assessed at: **{posture.get('assessed_at', '—')}**",
        f"- Controls continuously assessed: **{posture.get('controls_assessed', 0)}**",
        "",
        "| Control | Family | Title | Severity | This cycle |",
        "|---|---|---|---|---|",
    ]
    for c in _load_controls():
        cid = c["id"]
        row = by_id.get(cid, {})
        status = row.get("status", "UNKNOWN")
        sev = row.get("severity", "—")
        mark = _STATUS_MARK.get(status, "UNK")
        lines.append(
            f"| {cid} | {c['family']} | {c['title']} | {sev} | {mark} ({status}) |"
        )
    lines.append("")
    lines.append(
        "_Scope note: this is a continuously-assessed SAMPLE of Rev. 5, not full-catalog "
        "coverage. Sample posture is never cited as ATO posture._"
    )
    lines.append("")
    return "\n".join(lines)


def _posture_md(posture: Dict[str, Any], bundle_ts: str) -> str:
    controls = posture.get("controls", [])
    poam = posture.get("poam", [])
    lines = [
        "# HELM ConMon — Control Posture Evidence",
        "",
        f"- **Bundle**: `conmon_posture_{bundle_ts}`",
        f"- **Framework**: {posture.get('framework', 'NIST SP 800-53 Rev. 5')}",
        f"- **ConMon standard**: {posture.get('conmon_standard', 'NIST SP 800-137')}",
        f"- **Assessed at**: {posture.get('assessed_at', '—')}",
        f"- **Posture**: {posture.get('posture_percent', 0.0)}% "
        f"({posture.get('implemented', 0)}/{posture.get('controls_assessed', 0)} implemented, "
        f"scope: {posture.get('posture_percent_scope', 'SAMPLED_CONTROLS_ONLY')})",
        f"- **Open findings**: {posture.get('open_findings', 0)} "
        f"(HIGH: {posture.get('high_findings', 0)})",
        "",
        "## Controls (re-derived from live evidence this cycle)",
        "",
        "| Control | Title | Status | Severity | Evidence |",
        "|---|---|---|---|---|",
    ]
    for c in controls:
        ev = str(c.get("evidence", "")).replace("|", "\\|")[:90]
        lines.append(
            f"| {c.get('control_id')} | {str(c.get('title',''))[:40]} | "
            f"{_STATUS_MARK.get(c.get('status'),'UNK')} ({c.get('status')}) | "
            f"{c.get('severity','—')} | {ev} |"
        )
    lines += ["", "## POA&M — open findings", ""]
    if poam:
        lines += ["| POA&M | Control | Severity | Weakness |", "|---|---|---|---|"]
        for p in poam:
            wk = str(p.get("weakness", "")).replace("|", "\\|")[:80]
            lines.append(
                f"| {p.get('poam_id')} | {p.get('control_id')} | {p.get('severity')} | {wk} |"
            )
    else:
        lines.append("_No open findings this cycle._")
    lines += [
        "",
        "## Doctrine",
        "",
        f"{posture.get('doctrine', '')}",
        "",
        "_No fake green: every status above is what an executable assessor OBSERVED at "
        "assessment time. UNKNOWN contributes zero to posture — absence of evidence is a "
        "finding, not partial credit._",
        "",
    ]
    return "\n".join(lines)


def emit_evidence(
    posture: Optional[Dict[str, Any]] = None,
    evidence_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Write a fresh ConMon evidence bundle under docs/evidence/conmon/.

    Args:
        posture: the dict returned by `helm_conmon.assess()`. If None, the most recent
                 posture written to `coordination/security/helm_control_posture.json`
                 is loaded (so this can be called standalone after a cycle).
        evidence_dir: override output dir (used by tests). Defaults to docs/evidence/conmon.

    Returns a manifest dict describing the files written.
    """
    if posture is None:
        from backend.security.helm_conmon import POSTURE
        if not POSTURE.exists():
            raise FileNotFoundError(
                f"no posture to emit; run helm_conmon.assess() first ({POSTURE})"
            )
        posture = json.loads(POSTURE.read_text())

    out = Path(evidence_dir) if evidence_dir else EVIDENCE_DIR
    out.mkdir(parents=True, exist_ok=True)

    ts = _stamp(posture.get("assessed_at", ""))
    json_path = out / f"conmon_posture_{ts}.json"
    md_path = out / f"conmon_posture_{ts}.md"
    map_path = out / "NIST_800-53_REV5_CONTROL_MAP.md"
    latest_path = out / "latest.json"

    json_path.write_text(json.dumps(posture, indent=2) + "\n")
    md_path.write_text(_posture_md(posture, ts))
    map_path.write_text(_control_map_md(posture))

    manifest = {
        "schema": "HELM_CONMON_EVIDENCE_BUNDLE_v1",
        "generated_at": _now_iso(),
        "assessed_at": posture.get("assessed_at"),
        "framework": posture.get("framework"),
        "conmon_standard": posture.get("conmon_standard"),
        "posture_percent": posture.get("posture_percent"),
        "posture_percent_scope": posture.get("posture_percent_scope"),
        "controls_assessed": posture.get("controls_assessed"),
        "implemented": posture.get("implemented"),
        "open_findings": posture.get("open_findings"),
        "high_findings": posture.get("high_findings"),
        "bundle": {
            "posture_json": str(json_path.relative_to(ROOT)) if json_path.is_relative_to(ROOT) else f"docs/evidence/conmon/{json_path.name}",
            "posture_md": str(md_path.relative_to(ROOT)) if md_path.is_relative_to(ROOT) else f"docs/evidence/conmon/{md_path.name}",
            "control_map_md": str(map_path.relative_to(ROOT)) if map_path.is_relative_to(ROOT) else f"docs/evidence/conmon/{map_path.name}",
        },
    }
    latest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    m = emit_evidence()
    print(f"ConMon evidence bundle → {EVIDENCE_DIR}")
    print(f"  posture {m['posture_percent']}%  high={m['high_findings']}  "
          f"({m['implemented']}/{m['controls_assessed']} implemented)")
    for k, v in m["bundle"].items():
        print(f"  {k:16s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
