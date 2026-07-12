#!/usr/bin/env python3
"""REQ-GOV-006 — no test may substitute a string literal for a file read.

Audit F-21.3: test_22 was found rewritten so BACKEND and UI were hardcoded strings
containing exactly the substrings its asserts searched for. It passed 28/28 while the
backend had none of the gates and the UI file did not exist.
"""
import ast, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "tautology_report.json"
WATCH = ["tests/test_h1b_authorization_enforcement.py", "tests/test_h1d_dispatch.py",
         "tests/test_h1d_spend_gate.py", "tests/test_h1b_founder_decision.py"]
# Module-level names that MUST be sourced from a real file, never a literal.
FILE_BACKED = {"BACKEND", "UI", "SRC", "SOURCE"}
offenders = []
for rel in WATCH:
    p = ROOT / rel
    if not p.exists():
        continue
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in FILE_BACKED:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        offenders.append({"file": rel, "name": t.id, "line": node.lineno,
                                          "defect": "STRING_LITERAL_SUBSTITUTED_FOR_FILE_READ"})
report = {"requirement": "REQ-GOV-006", "tautological_tests": offenders,
          "status": "PASS" if not offenders else "FAIL"}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(f"tautological tests: {len(offenders)}")
sys.exit(0 if not offenders else 1)
