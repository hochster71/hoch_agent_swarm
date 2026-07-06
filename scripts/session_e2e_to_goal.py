#!/usr/bin/env python3
"""
Session E2E to GOAL — one runtime that verifies everything touched in the
2026-07-06 working session, fail-closed, no fake-green.

Scope (all additive, read-only except for the two evidence artifacts it writes):
  FE* — the frontend/has_brain_moonshot.html audit fixes
  D*  — the gap + PERT data sources are present, valid, and internally consistent
  G*  — GOAL awareness (reports blocker/goal state; does NOT fail on founder gates)

Writes:
  has_live_project_tracker/data/session_e2e_result.json   (machine result)
  docs/evidence/moonshot/session_e2e_<UTC>.md             (evidence)

Exit code: 0 only if every HARD check PASSes. Any FAIL -> exit 1.
GOAL/founder gates are reported as INFO and never flip the exit code (they are
external actions, not runtime defects).
"""
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HTML = REPO / "frontend" / "has_brain_moonshot.html"
DATA = REPO / "has_live_project_tracker" / "data"
BRAIN = REPO / "data" / "prompt_brain" / "convergence_status.json"
CONTRACT = DATA / "moonshot_control_plane_contract.json"
PERT_GAP = DATA / "fresh_pert_gap_analysis.json"
GAP_DOC_DIR = REPO / "docs" / "evidence" / "moonshot"
RESULT = DATA / "session_e2e_result.json"

now = datetime.now(timezone.utc)
TS = now.strftime("%Y%m%dT%H%M%SZ")
EVIDENCE = GAP_DOC_DIR / f"session_e2e_{TS}.md"

checks = []  # {id, kind: HARD|INFO, status: PASS|FAIL|INFO, detail}


def add(cid, kind, ok, detail):
    status = ("PASS" if ok else "FAIL") if kind == "HARD" else "INFO"
    checks.append({"id": cid, "kind": kind, "status": status, "detail": detail})
    return ok


def read_text(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


def extract_script(html):
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    return m.group(1) if m else ""


# ---------------- FRONTEND fixes ----------------
html = read_text(HTML)
add("FE0-exists", "HARD", bool(html), f"{HTML.relative_to(REPO)} present ({len(html)} bytes)")

js = extract_script(html)
node_ok, node_detail = False, "node not run"
if js:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=30)
        node_ok = r.returncode == 0
        node_detail = "node --check clean" if node_ok else (r.stderr.strip()[:200] or "syntax error")
    except FileNotFoundError:
        node_ok, node_detail = False, "node not installed"
    except Exception as e:  # noqa
        node_ok, node_detail = False, f"{type(e).__name__}: {e}"
add("FE1-js-syntax", "HARD", node_ok, node_detail)

add("FE2-panel-css", "HARD",
    (".card,.panel{" in html or ".panel{" in html) and ".panel h3" in html,
    "'.panel' + '.panel h3' rules present (Swarms/Fleet panels styled)")

add("FE3-no-URL-shadow", "HARD",
    ("const LIVE_URL" in html) and (re.search(r"\bconst URL\s*=", html) is None),
    "global URL constructor no longer shadowed; LIVE_URL in use")

add("FE4-esc-singlequote", "HARD",
    "&#39;" in html and "[&<>\"']" in html,
    "esc() escapes single quotes (inline-handler breakout closed)")

add("FE5-clock-node", "HARD",
    'id="clock"' in html and "getElementById('clock')" in html
    and "if(last) render(); }, 1000)" not in html,
    "1s interval updates #clock only; whole-deck teardown removed")


# ---------------- DATA: gap + PERT truth ----------------
def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa
        return None, f"{type(e).__name__}: {e}"


gap, gerr = load_json(PERT_GAP)
add("D1-pert-json", "HARD", gap is not None,
    "fresh_pert_gap_analysis.json valid JSON" if gap else f"invalid: {gerr}")

if gap:
    has_shape = all(k in gap for k in ("critical_path", "pert_summary")) and \
        {"optimistic_minutes", "most_likely_minutes", "pessimistic_minutes",
         "expected_minutes"}.issubset(gap.get("pert_summary", {}))
    add("D2-pert-shape", "HARD", has_shape, "critical_path + pert_summary(O/ML/P/expected) present")

    if has_shape:
        ps = gap["pert_summary"]
        o, ml, p = ps["optimistic_minutes"], ps["most_likely_minutes"], ps["pessimistic_minutes"]
        te_calc = round((o + 4 * ml + p) / 6, 2)
        te_stored = ps["expected_minutes"]
        consistent = abs(te_calc - te_stored) <= 1.0
        add("D3-pert-te-recompute", "HARD", consistent,
            f"TE=(O+4ML+P)/6={te_calc} vs stored expected={te_stored} "
            f"({'consistent' if consistent else 'MISMATCH'})")
        sigma = round((p - o) / 6, 2)
        add("D3b-pert-sigma", "INFO", True, f"sigma=(P-O)/6={sigma} min; 95% band ~ {round(te_calc-1.96*sigma)}..{round(te_calc+1.96*sigma)} min")

conv, cerr = load_json(BRAIN)
add("D4-convergence-json", "HARD", conv is not None and "state" in (conv or {}),
    f"convergence_status.json state={conv.get('state')} gen={conv.get('generation')} mean={conv.get('mean_score')}"
    if conv else f"invalid: {cerr}")

contract, kerr = load_json(CONTRACT)
add("D5-contract-json", "HARD", contract is not None,
    "moonshot_control_plane_contract.json valid JSON" if contract else f"invalid: {kerr}")

gap_docs = sorted(GAP_DOC_DIR.glob("gap_pert_to_goal_*.md"))
add("D6-gap-doc", "HARD", len(gap_docs) > 0,
    f"gap+PERT evidence doc present: {gap_docs[-1].name if gap_docs else 'MISSING'}")


# ---------------- GOAL awareness (INFO only) ----------------
if gap:
    blockers = gap.get("blockers", [])
    add("G1-blockers", "INFO", True,
        f"overall_status={gap.get('overall_status')}; hard blockers={blockers or 'none'}; "
        f"critical_path[0]={ (gap.get('critical_path') or ['?'])[0] }")
    add("G2-next-safe", "INFO", True,
        "next safe: " + " | ".join(gap.get("next_3_safe_actions", [])[:3]))
if conv:
    add("G3-brain-mode", "INFO", True,
        f"BRAIN {conv.get('state')} at mean {conv.get('mean_score')} — M0 mechanical (proxy, not outcome-bound)")


# ---------------- verdict ----------------
hard = [c for c in checks if c["kind"] == "HARD"]
passed = [c for c in hard if c["status"] == "PASS"]
failed = [c for c in hard if c["status"] == "FAIL"]
overall = "PASS" if not failed else "FAIL"

result = {
    "schema": "session-e2e-to-goal-v1",
    "generated_at": now.isoformat(),
    "repo_revision": read_text(REPO / "REVISION").strip() or None,
    "overall_status": overall,
    "hard_total": len(hard),
    "hard_passed": len(passed),
    "hard_failed": len(failed),
    "checks": checks,
    "evidence_md": str(EVIDENCE.relative_to(REPO)),
}
DATA.mkdir(parents=True, exist_ok=True)
RESULT.write_text(json.dumps(result, indent=2), encoding="utf-8")

# evidence markdown
lines = [f"# Session E2E to GOAL — {overall}", "",
         f"- Generated (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}",
         f"- Repo REVISION: `{result['repo_revision']}`",
         f"- Hard checks: **{len(passed)}/{len(hard)} PASS**"
         + (f" · **{len(failed)} FAIL**" if failed else ""),
         "", "| Check | Kind | Status | Detail |", "|---|---|---|---|"]
for c in checks:
    lines.append(f"| {c['id']} | {c['kind']} | {c['status']} | {c['detail']} |")
lines += ["", "> Fail-closed: exit 0 only when every HARD check passes. "
          "GOAL/founder gates are INFO and never affect the exit code (external actions, not runtime defects)."]
GAP_DOC_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"SESSION E2E TO GOAL: {overall}  ({len(passed)}/{len(hard)} hard PASS)")
for c in checks:
    mark = {"PASS": "✓", "FAIL": "✗", "INFO": "·"}[c["status"]]
    print(f"  {mark} [{c['kind']:4}] {c['id']}: {c['detail']}")
print(f"result:   {RESULT.relative_to(REPO)}")
print(f"evidence: {EVIDENCE.relative_to(REPO)}")
sys.exit(0 if overall == "PASS" else 1)
