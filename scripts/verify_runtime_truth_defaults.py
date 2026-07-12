#!/usr/bin/env python3
"""REQ-GOV-005 — runtime truth default elimination scanner.

Fails CLOSED on any of the prohibited patterns. This is the gate: REQ-GOV-005 may pass
only when this returns zero violations.

PROHIBITED (ratified):
  P1  a fallback default inside a telemetry wrapper -> compute_gap.get("k", 90.0)
  P2  a `fallback=` kwarg on wrap_telemetry_dict
  P3  now() substituted for a MISSING source/observation timestamp
  P4  a hardcoded completion/confidence literal presented as a measurement
  P5  a truth wrapper that can return fresh=True / age 0 without a source timestamp

Scope: backend/pert_server.py, backend/runtime_truth.py, backend/main.py.
Also usable as a seeded-regression harness: reintroduce any pattern and this must fail.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "coordination" / "goal" / "runtime_truth_defaults_report.json"

TARGETS = ["backend/pert_server.py", "backend/main.py", "backend/runtime_truth.py"]

# P4: numbers/strings that were previously fabricated and passed off as measurements.
FABRICATED_LITERALS = [
    r'"9[05]%\s*Confidence',
    r"'9[05]%\s*Confidence",
    r'goal_completion_percent\s*=\s*9[05]',
    r'completion_percent"\s*:\s*(?:90|95|100)\b',
]

# telemetry-ish fields where a default is a lie
FAIL_CLOSED_DEFAULTS = {"UNKNOWN", "MISSING", "STALE", "ERROR", "UNVERIFIED",
                        "PENDING", "BLOCKED", "NONE", "NOT_PROVISIONED", "NOT_RUN"}

METRIC_HINT = re.compile(
    r"(percent|completion|confidence|remaining|freshness|readiness|utilization|"
    r"minutes|score|coverage|health|status)", re.I)


def scan_file(rel: str) -> list[dict]:
    p = ROOT / rel
    if not p.exists():
        return [{"file": rel, "pattern": "FILE_MISSING", "detail": "target absent",
                 "line": 0}]
    src = p.read_text(encoding="utf-8")
    violations: list[dict] = []

    # ---- P2: fallback= kwarg anywhere in a telemetry wrapper call --------------
    for m in re.finditer(r"wrap_telemetry_dict\([^)]*\bfallback\s*=", src, re.S):
        violations.append({
            "file": rel, "pattern": "P2_FALLBACK_KWARG",
            "line": src[:m.start()].count("\n") + 1,
            "detail": "wrap_telemetry_dict() may not accept a fallback default",
        })

    # ---- P1: a default inside .get() for a metric-ish key ----------------------
    for m in re.finditer(
            r'\.get\(\s*["\']([\w.]+)["\']\s*,\s*(?!None\b)([^)\n]+?)\s*\)', src):
        key, default = m.group(1), m.group(2).strip()
        if not METRIC_HINT.search(key):
            continue
        # FAIL-CLOSED defaults are permitted and encouraged: an empty container carries
        # no claim, and an explicit truth state IS the honest answer. What is prohibited
        # is a default that ASSERTS SUCCESS -- a number, or an optimistic status string.
        if default in ("{}", "[]", "()", '""', "''"):
            continue
        if default.strip('"\'').upper() in FAIL_CLOSED_DEFAULTS:
            continue
        line = src[:m.start()].count("\n") + 1
        violations.append({
            "file": rel, "pattern": "P1_METRIC_FALLBACK_DEFAULT", "line": line,
            "detail": f'{key} defaults to {default} -- a missing source must yield MISSING, not a value',
        })

    # ---- P3: now() substituted for a missing source timestamp ------------------
    for m in re.finditer(
            r"if\s+not\s+(\w*(?:updated|observed|timestamp|ts)\w*)\s*:\s*\n\s*\1\s*=\s*"
            r"[^\n]*(?:datetime\.now|utcnow|time\.time)", src):
        violations.append({
            "file": rel, "pattern": "P3_FABRICATED_TIMESTAMP",
            "line": src[:m.start()].count("\n") + 1,
            "detail": f"{m.group(1)} is stamped with now() when the source has none",
        })

    # ---- P4: fabricated statistical / completion literals ----------------------
    for pat in FABRICATED_LITERALS:
        for m in re.finditer(pat, src):
            violations.append({
                "file": rel, "pattern": "P4_FABRICATED_LITERAL",
                "line": src[:m.start()].count("\n") + 1,
                "detail": f"hardcoded measurement-looking literal: {m.group(0)[:48]}",
            })

    return violations


def check_truth_contract() -> list[dict]:
    """P5: the truth primitive must be structurally incapable of faking freshness."""
    v: list[dict] = []
    sys.path.insert(0, str(ROOT))
    try:
        from backend.runtime_truth import primitives as rt
    except Exception as e:
        return [{"file": "backend/runtime_truth.py", "pattern": "P5_IMPORT_FAILED",
                 "line": 0, "detail": str(e)}]

    # missing timestamp -> the ratified shape, exactly
    f = rt.freshness(None)
    if not (f["freshness"] == "UNKNOWN" and f["fresh"] is False
            and f["age_seconds"] is None and f["timestamp_status"] == "MISSING"):
        v.append({"file": "backend/runtime_truth.py", "pattern": "P5_FRESHNESS_CONTRACT",
                  "line": 0, "detail": f"missing timestamp produced {f}"})

    # missing value -> MISSING, never a number
    t = rt.truth(source="s")
    if not (t["value"] is None and t["state"] == "MISSING"
            and t["confidence"] == "NONE" and t["age_seconds"] is None):
        v.append({"file": "backend/runtime_truth.py", "pattern": "P5_TRUTH_CONTRACT",
                  "line": 0, "detail": f"missing value produced {t}"})

    # the wrapper must not accept a fallback that changes the answer
    import inspect
    sig = inspect.signature(rt.truth)
    if "fallback" in sig.parameters:
        v.append({"file": "backend/runtime_truth.py", "pattern": "P5_FALLBACK_PARAM",
                  "line": 0, "detail": "truth() must not expose a fallback parameter"})
    return v


def main() -> int:
    violations: list[dict] = []
    for rel in TARGETS:
        violations.extend(scan_file(rel))
    violations.extend(check_truth_contract())

    by_pattern: dict[str, int] = {}
    for x in violations:
        by_pattern[x["pattern"]] = by_pattern.get(x["pattern"], 0) + 1

    report = {
        "requirement": "REQ-GOV-005",
        "scanned": TARGETS,
        "violations": violations,
        "violation_count": len(violations),
        "by_pattern": by_pattern,
        "status": "PASS" if not violations else "FAIL",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(report, indent=2, sort_keys=True) + "\n"
    OUT.write_text(body, encoding="utf-8")
    print(f"REQ-GOV-005 runtime-truth scan: {len(violations)} violations {by_pattern or ''}")
    for x in violations[:12]:
        print(f"  {x['pattern']:28} {x['file']}:{x['line']}  {x['detail'][:60]}")
    print(f"report sha256: {hashlib.sha256(body.encode()).hexdigest()}")
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
