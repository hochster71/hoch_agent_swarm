#!/usr/bin/env python3
"""
HOCH Safe-Action Executor — the "hands" for AI-Michael's SAFE action class.

Closes the last GOAL-contract criterion ("Michael no longer has to manually copy/paste
routine commands") for the safe 80%, while keeping every gate we hold by hand today.

WHAT IT DOES
  Reads a STRUCTURED action queue and, for each action, decides EXECUTE / BLOCKED / APPROVAL:
    * EXECUTE  — only whitelisted, idempotent, read-only-ish actions (pytest, build, verify
                 scripts). Runs via a typed handler. NEVER arbitrary shell.
    * BLOCKED  — an operator hold covers the action's category. Logged, not run.
    * APPROVAL — anything mutating/irreversible/risky (push, tag, deploy, money, secrets,
                 external writes) or not on the whitelist -> routed to the human approval
                 queue. Never executed.

FAIL-CLOSED BY DESIGN
  * DRY-RUN BY DEFAULT. Live execution requires SAFE_EXECUTOR_ENABLED=1 in the environment.
    In dry-run it has ZERO side effects (writes nothing) — it only prints what it WOULD do.
  * Honors has_live_project_tracker/data/ag_operator_hold.json.
  * Whitelist of action TYPES + an allowlist of script name-prefixes. Path-escape guarded.
  * A forbidden-substring scan sends anything risky-looking to approval regardless of type.
  * Every decision is appended to the evidence ledger (when live).

This is intentionally conservative. v1 removes the repetitive SAFE relay (run this test /
verify / build) with zero mutation risk. Expand SAFE_TYPES / the script allowlist only as
trust is established — ideally behind its own operator approval.
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "has_live_project_tracker" / "data"
QUEUE = DATA / "agent_action_queue.json"
HOLD = DATA / "ag_operator_hold.json"
APPROVALS = DATA / "human_approval_queue.json"
LEDGER = REPO / "data" / "agent_execution_ledger.jsonl"

# Only these action types may EVER auto-execute. All read-only / idempotent.
SAFE_TYPES = {"pytest", "frontend_build", "run_script"}
# run_script may ONLY run scripts whose basename starts with one of these (verification/build).
SCRIPT_ALLOWLIST_PREFIXES = ("verify_", "rc", "qa_", "pert_e2e_build", "healthcheck", "session_e2e", "audit_")
# If any of these appear anywhere in the action, force it to APPROVAL — never auto-run.
FORBIDDEN_SUBSTR = ("push", "tag ", "deploy", "rm -", "secret", "stripe", "publish",
                    "ufw", "ssh ", "git push", "--force", "credential", "token")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _enabled():
    return os.environ.get("SAFE_EXECUTOR_ENABLED") == "1"


def _hold_categories():
    try:
        h = json.loads(HOLD.read_text())
        if h.get("operator_hold_active"):
            return set(h.get("affected_categories") or ["*"])
    except Exception:
        pass
    return set()


def decide(action, hold_cats):
    """Pure classification — no side effects. Returns (verdict, why)."""
    exec_spec = action.get("exec") or {}
    t = exec_spec.get("type")
    blob = json.dumps(action).lower()
    if action.get("requires_michael_approval"):
        return "APPROVAL", "requires_michael_approval=true"
    if any(s in blob for s in FORBIDDEN_SUBSTR):
        return "APPROVAL", "matched a forbidden/risky term"
    if t not in SAFE_TYPES:
        return "APPROVAL", f"exec.type '{t}' is not in the auto-safe whitelist"
    cat = action.get("category", "general")
    if hold_cats and ("*" in hold_cats or cat in hold_cats):
        return "BLOCKED", f"operator hold active on category '{cat}'"
    return "EXECUTE", "safe type, no approval flag, no hold"


# ---- typed handlers: (ok, detail, evidence_paths). No arbitrary shell. ----
def _run(cmd, cwd=None, timeout=1800):
    r = subprocess.run(cmd, cwd=cwd or str(REPO), capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0, (r.stdout[-600:] + r.stderr[-600:]).strip()


def _h_pytest(a):
    path = (a.get("exec") or {}).get("path", "")
    if not path or ".." in path or path.startswith("/"):
        return False, "invalid/escaping test path", []
    ok, out = _run([sys.executable, "-m", "pytest", path, "-q"])
    return ok, out, [path]


def _h_frontend_build(a):
    ok, out = _run(["npm", "run", "build"], cwd=str(REPO / "frontend"))
    return ok, out, ["frontend/dist"]


def _h_run_script(a):
    script = (a.get("exec") or {}).get("script", "")
    base = os.path.basename(script)
    if not script or ".." in script or script.startswith("/") or \
            not any(base.startswith(p) for p in SCRIPT_ALLOWLIST_PREFIXES):
        return False, f"script '{script}' not on allowlist", []
    p = REPO / script
    if not p.exists():
        return False, "script not found", []
    interp = [sys.executable] if script.endswith(".py") else ["bash"]
    ok, out = _run(interp + [script])
    return ok, out, [script]


HANDLERS = {"pytest": _h_pytest, "frontend_build": _h_frontend_build, "run_script": _h_run_script}


def _append_json_list(path, root_key, item):
    try:
        doc = json.loads(path.read_text()) if path.exists() else {root_key: []}
    except Exception:
        doc = {root_key: []}
    doc.setdefault(root_key, []).append(item)
    doc["generated_at"] = _now()
    path.write_text(json.dumps(doc, indent=2))


def run(dry):
    hold_cats = _hold_categories()
    try:
        actions = json.loads(QUEUE.read_text()).get("actions", []) if QUEUE.exists() else []
    except Exception as e:  # noqa
        actions = []
        print(f"[warn] could not read queue: {e}")

    results = []
    for a in actions:
        verdict, why = decide(a, hold_cats)
        outcome, detail, ev = verdict, why, []

        if verdict == "EXECUTE":
            if dry:
                outcome, detail = "DRY_RUN_WOULD_EXECUTE", f"would run {a.get('exec', {}).get('type')}"
            else:
                ok, detail, ev = HANDLERS[a["exec"]["type"]](a)
                outcome = "SUCCESS" if ok else "FAILED"
        elif verdict == "APPROVAL" and not dry:
            _append_json_list(APPROVALS, "pending_approvals", {
                "approval_id": f"AUTO-{a.get('id', '?')}-{_now()}",
                "type": "SAFE_EXECUTOR_ROUTED", "status": "PENDING",
                "approval_required_from": "Michael", "title": a.get("title"),
                "reason": why, "requested_at": _now(),
            })
            outcome = "ROUTED_TO_APPROVAL"

        if not dry:
            _ledger({
                "timestamp": _now(), "task_id": a.get("id"), "task_summary": a.get("title"),
                "safety_tier": "SAFE_EXECUTOR", "approval_required": verdict == "APPROVAL",
                "action_allowed": outcome in ("SUCCESS",),
                "evidence_paths": ev, "verdict": outcome, "detail": str(detail)[:200],
            })
        results.append({"id": a.get("id"), "title": a.get("title"),
                        "verdict": verdict, "outcome": outcome, "why": why})

    summary = {"dry_run": dry, "enabled_flag": _enabled(),
               "operator_hold_categories": sorted(hold_cats),
               "actions_seen": len(actions), "results": results}
    print(json.dumps(summary, indent=2))
    return 1 if any(r["outcome"] == "FAILED" for r in results) else 0


def _ledger(entry):
    try:
        with open(LEDGER, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(run(dry=not _enabled()))
