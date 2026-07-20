#!/usr/bin/env python3
"""verify_promotion_manifest.py — the ONLY component that may emit GO.

Evaluates HELM_PROMOTION_EVIDENCE_MANIFEST.json against the promotion invariant,
deterministically and mechanically. No narrative input, no judgment, no overrides.

    Promotion Authority =
        Completion Matrix satisfied
    AND Promotion Evidence Manifest complete
    AND all required evidence bound to the candidate revision
    AND no required field UNKNOWN
    AND no required field STALE
    AND founder approvals resolved where applicable
    Else HOLD

Exit 0 = GO (and writes overall_decision=GO + promotion_timestamp into a NEW dated
copy — the input manifest is never edited). Any other condition = HOLD, exit 2,
with every failing reason listed. A verifier crash is HOLD (fail-closed), exit 3.

Usage:  python3 scripts/goal/verify_promotion_manifest.py [path-to-manifest]
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "coordination" / "goal" / "HELM_PROMOTION_EVIDENCE_MANIFEST.json"

RESOLVED_GATE_STATES = {"GRANTED", "APPROVED", "EXERCISED_OK", "NOT_APPLICABLE",
                        "NOT_APPLICABLE_UNTIL_APPLE_APPROVED", "ACCEPTED", "RATIFIED"}


def _get(manifest: dict, dotted: str):
    cur = manifest
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _check_field(name: str, f, reasons: list) -> None:
    if not isinstance(f, dict):
        reasons.append(f"{name}: not a structured evidence field")
        return
    if f.get("value") in (None, "", "UNKNOWN"):
        reasons.append(f"{name}: value UNKNOWN/null")
    if f.get("verified") is not True:
        reasons.append(f"{name}: not verified")
    if not f.get("source"):
        reasons.append(f"{name}: no source recorded")
    if f.get("bound_to_candidate") is not True:
        reasons.append(f"{name}: not bound to candidate revision (STALE by binding rule)")
    ap = f.get("artifact_path")
    if ap and not (ROOT / ap).exists():
        reasons.append(f"{name}: artifact_path missing on disk: {ap}")


def _verify_commit_exists(sha: str, reasons: list) -> None:
    try:
        r = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                           cwd=str(ROOT), capture_output=True, timeout=15)
        if r.returncode != 0:
            reasons.append(f"candidate.commit: {sha[:12]} not present in local git object store")
    except Exception as e:
        reasons.append(f"candidate.commit: git verification failed ({type(e).__name__}) — fail closed")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    m = json.loads(path.read_text())
    reasons: list = []

    # 1. required fields complete + verified + bound
    for dotted in m.get("required_for_go", []):
        _check_field(dotted, _get(m, dotted), reasons)

    # 2. candidate commit independently exists in git
    commit_field = _get(m, "candidate.commit") or {}
    if isinstance(commit_field, dict) and commit_field.get("value"):
        _verify_commit_exists(str(commit_field["value"]), reasons)

    # 3. cross-binding: every evidence field claiming binding must name the SAME candidate
    #    (binding is asserted per-field; a field bound to a different SHA is STALE)
    #    -- enforced structurally by bound_to_candidate + the populating procedure;
    #    verifier re-checks any field that records a commit_sha explicitly:
    cand = (commit_field.get("value") if isinstance(commit_field, dict) else None)
    for name, f in (m.get("evidence") or {}).items():
        if isinstance(f, dict) and f.get("commit_sha") and cand and f["commit_sha"] != cand:
            reasons.append(f"evidence.{name}: commit_sha {str(f['commit_sha'])[:12]} != candidate {str(cand)[:12]} (STALE)")

    # 4. founder gates resolved where applicable
    for gate, state in (m.get("founder_gates") or {}).items():
        if str(state) not in RESOLVED_GATE_STATES:
            reasons.append(f"founder_gates.{gate}: {state} (unresolved)")

    # 5. decision
    if reasons:
        print(json.dumps({"decision": "HOLD", "reasons": reasons,
                          "rule": m.get("promotion_invariant")}, indent=2))
        return 2

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out = dict(m)
    out["overall_decision"] = "GO"
    out["promotion_timestamp"] = now
    out["decision_provenance"] = f"verify_promotion_manifest.py at {now} — all invariant clauses satisfied"
    dated = path.with_name(f"HELM_PROMOTION_DECISION_{now[:19].replace(':','')}.json")
    dated.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"decision": "GO", "written": str(dated.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:  # verifier crash = HOLD, fail closed
        print(json.dumps({"decision": "HOLD", "reasons": [f"VERIFIER_ERROR: {type(e).__name__}: {e}"]}, indent=2))
        raise SystemExit(3)
