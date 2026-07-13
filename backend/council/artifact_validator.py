"""artifact_validator.py — independent validation of a dispatched defect-report artifact.

The validator is INDEPENDENT of the model: it re-checks every claim against ground truth
(the real repo file) and the authority binding. It rejects:
    * empty output
    * malformed / non-JSON output
    * a file path that does not exist
    * a supporting line that does not actually appear in the cited file (unsupported claim)
    * a missing finding or remediation (missing evidence)
    * a result whose authority_decision_id != the expected one (wrong authority id)
    * a result whose classified_task_sha256 != the expected digest (mutated task)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    # tolerate ```json fences and leading prose — grab the first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def validate(result_envelope: dict, *, expected_authority_id: str,
             expected_task_sha256: str) -> tuple[bool, list[str]]:
    """Returns (passed, reasons). PASS only when every check holds."""
    reasons: list[str] = []

    # authority binding first — a wrong id or mutated digest fails regardless of content
    if result_envelope.get("authority_decision_id") != expected_authority_id:
        reasons.append("WRONG_AUTHORITY_ID")
    if result_envelope.get("classified_task_sha256") != expected_task_sha256:
        reasons.append("TASK_DIGEST_MISMATCH")

    out = result_envelope.get("output", "")
    if not out or not out.strip():
        reasons.append("EMPTY_OUTPUT")
        return False, reasons

    rep = _extract_json(out)
    if rep is None:
        reasons.append("MALFORMED_OUTPUT_NOT_JSON")
        return False, reasons

    for fld in ("file_path", "finding", "supporting_line", "remediation"):
        if not rep.get(fld) or not str(rep[fld]).strip():
            reasons.append(f"MISSING_FIELD:{fld}")

    fp = rep.get("file_path", "")
    if fp:
        target = (ROOT / fp).resolve()
        # path must exist AND stay inside the repo (no traversal)
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            reasons.append("NONEXISTENT_OR_OUT_OF_TREE_PATH")
        else:
            # the supporting line must ACTUALLY appear in the cited file
            line = str(rep.get("supporting_line", "")).strip()
            content = target.read_text(errors="ignore")
            norm = re.sub(r"\s+", " ", line)
            if norm and norm not in re.sub(r"\s+", " ", content):
                reasons.append("UNSUPPORTED_CLAIM_LINE_NOT_IN_FILE")

    return (len(reasons) == 0), reasons
