#!/usr/bin/env python3
"""
Independent second-pass audit of session_e2e_to_goal.py output.

Does NOT trust the runner's booleans. It re-derives three ground-truth facts
from source, checks the result is fresh, and — most importantly — detects
fake-green: overall_status must equal (hard_failed == 0) computed from the
checks array itself, and hard_passed+hard_failed must equal hard_total.

Writes: docs/evidence/moonshot/session_e2e_audit_<UTC>.md
Exit 0 only if the runner's result is present, fresh, self-consistent, and its
green claim is independently corroborated. Else exit 1.
"""
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULT = REPO / "has_live_project_tracker" / "data" / "session_e2e_result.json"
HTML = REPO / "frontend" / "has_brain_moonshot.html"
PERT_GAP = REPO / "has_live_project_tracker" / "data" / "fresh_pert_gap_analysis.json"
GAP_DOC_DIR = REPO / "docs" / "evidence" / "moonshot"

now = datetime.now(timezone.utc)
TS = now.strftime("%Y%m%dT%H%M%SZ")
OUT = GAP_DOC_DIR / f"session_e2e_audit_{TS}.md"
FRESH_MAX_S = 900  # result must be < 15 min old

findings = []


def a(cid, ok, detail):
    findings.append({"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail})
    return ok


# 1. result present + parseable
try:
    res = json.loads(RESULT.read_text(encoding="utf-8"))
    a("A1-result-present", True, f"{RESULT.name} parsed")
except Exception as e:  # noqa
    a("A1-result-present", False, f"cannot read result: {e}")
    res = None

if res:
    # 2. freshness
    try:
        gen = datetime.fromisoformat(res["generated_at"])
        age = (now - gen).total_seconds()
        a("A2-fresh", 0 <= age <= FRESH_MAX_S, f"result age {int(age)}s (limit {FRESH_MAX_S}s)")
    except Exception as e:  # noqa
        a("A2-fresh", False, f"bad generated_at: {e}")

    # 3. self-consistency: counts add up
    checks = res.get("checks", [])
    hard = [c for c in checks if c.get("kind") == "HARD"]
    hp = sum(c["status"] == "PASS" for c in hard)
    hf = sum(c["status"] == "FAIL" for c in hard)
    a("A3-counts", hp == res.get("hard_passed") and hf == res.get("hard_failed")
      and len(hard) == res.get("hard_total") and (hp + hf) == len(hard),
      f"recount passed={hp} failed={hf} total={len(hard)} vs claimed "
      f"{res.get('hard_passed')}/{res.get('hard_failed')}/{res.get('hard_total')}")

    # 4. fake-green detector: overall must equal (no hard failures)
    derived = "PASS" if hf == 0 else "FAIL"
    a("A4-no-fake-green", derived == res.get("overall_status"),
      f"overall claimed={res.get('overall_status')}, derived-from-checks={derived}")

# ---- independent re-derivation from source (don't trust runner) ----
html = HTML.read_text(encoding="utf-8") if HTML.exists() else ""

# R1: JS syntax, re-run node --check ourselves
m = re.search(r"<script>(.*?)</script>", html, re.S)
js = m.group(1) if m else ""
ok = False
det = "no script/node"
if js:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=30)
        ok = r.returncode == 0
        det = "node --check clean (independent)" if ok else (r.stderr.strip()[:160] or "syntax error")
    except Exception as e:  # noqa
        ok, det = False, f"{type(e).__name__}: {e}"
a("R1-js-independent", ok, det)

# R2: panel CSS present independently
a("R2-panel-independent", ".panel h3" in html and (".card,.panel{" in html or ".panel{" in html),
  "'.panel' styling re-verified from source")

# R3: PERT TE recompute independently
try:
    ps = json.loads(PERT_GAP.read_text(encoding="utf-8"))["pert_summary"]
    te = round((ps["optimistic_minutes"] + 4 * ps["most_likely_minutes"] + ps["pessimistic_minutes"]) / 6, 2)
    a("R3-pert-independent", abs(te - ps["expected_minutes"]) <= 1.0,
      f"independent TE={te} vs stored {ps['expected_minutes']}")
except Exception as e:  # noqa
    a("R3-pert-independent", False, f"cannot recompute: {e}")

# ---- verdict ----
failed = [f for f in findings if f["status"] == "FAIL"]
verdict = "PASS" if res and not failed else "FAIL"

lines = [f"# Session E2E — Independent Audit — {verdict}", "",
         f"- Audited (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}",
         f"- Target: `{RESULT.relative_to(REPO)}`"
         + (f" (runner said **{res.get('overall_status')}**)" if res else " (MISSING)"),
         "", "| Finding | Status | Detail |", "|---|---|---|"]
for f in findings:
    lines.append(f"| {f['id']} | {f['status']} | {f['detail']} |")
lines += ["", "> Independent pass: re-derives JS syntax, panel CSS, and PERT TE from source, "
          "and cross-checks the runner's green claim against its own checks array (fake-green guard)."]
GAP_DOC_DIR.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"SESSION E2E AUDIT: {verdict}")
for f in findings:
    print(f"  {'✓' if f['status']=='PASS' else '✗'} {f['id']}: {f['detail']}")
print(f"audit evidence: {OUT.relative_to(REPO)}")
sys.exit(0 if verdict == "PASS" else 1)
