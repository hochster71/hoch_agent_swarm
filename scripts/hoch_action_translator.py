#!/usr/bin/env python3
"""
HOCH Action Translator — orchestrator prose -> structured, gated action queue.

Bridges the orchestrator's advisory recommendations (operator_next_actions.json, free text)
into the safe executor's structured queue (agent_action_queue.json). It is deliberately
CONSERVATIVE and never fabricates shell from prose:

  * If the orchestrator already flagged the item (requires_michael_approval, or a risk that
    isn't SAFE*), it passes through as approval — never auto-mappable.
  * Otherwise it tries a small allowlist of HIGH-CONFIDENCE keyword->typed-exec mappings
    (readiness check, frontend build, session e2e, pert e2e). Only exact keyword hits map.
  * Anything it can't confidently and safely map defaults to approval (unknown = human).

Output actions are then consumed by scripts/hoch_safe_executor.py, which independently
re-gates everything (whitelist, forbidden-terms, operator hold, dry-run). Two independent
gates: the translator won't emit unsafe execs, and the executor won't run them if it did.

Default: prints the translated queue. Pass --write to persist agent_action_queue.json.
"""
import json
import sys
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "has_live_project_tracker" / "data"
SRC = DATA / "operator_next_actions.json"
OUT = DATA / "agent_action_queue.json"

# (any-of keywords) -> exec factory. Scripts must match the executor's own allowlist prefixes.
SAFE_MAP = [
    (("m1 readiness", "brain m1", "brain readiness", "ollama readiness"),
     lambda: {"type": "run_script", "script": "scripts/verify_brain_m1_readiness.py"}),
    (("frontend build", "rebuild the shell", "build the shell", "build the dashboard",
      "vite build", "npm run build", "rebuild the react", "build the react"),
     lambda: {"type": "frontend_build"}),
    (("session e2e", "e2e to goal", "session_e2e"),
     lambda: {"type": "run_script", "script": "scripts/session_e2e_to_goal.py"}),
    (("pert e2e", "pert build", "pert_e2e"),
     lambda: {"type": "run_script", "script": "scripts/pert_e2e_build.sh"}),
]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _category(exec_spec):
    t = (exec_spec or {}).get("type")
    return {"pytest": "verification", "run_script": "verification",
            "frontend_build": "build"}.get(t, "general")


def map_action(rec):
    """Pure: recommendation dict -> (structured action, reason). No side effects."""
    src_approval = bool(rec.get("requires_michael_approval"))
    risk = str(rec.get("risk", "")).upper()
    text = " ".join(str(rec.get(k, "")) for k in
                    ("title", "reason", "suggested_vscode_task", "expected_evidence")).lower()
    action = {"id": rec.get("id"), "title": rec.get("title"), "source_risk": risk}

    # Orchestrator-flagged risk/approval -> never auto-map.
    if src_approval or (risk and not risk.startswith("SAFE")):
        action.update({"category": "general", "requires_michael_approval": True,
                       "exec": {"type": "advisory", "note": "orchestrator flagged risk/approval"}})
        return action, "approval (orchestrator-flagged)"

    # Conservative safe mapping.
    for keywords, factory in SAFE_MAP:
        if any(k in text for k in keywords):
            ex = factory()
            action.update({"category": _category(ex), "requires_michael_approval": False, "exec": ex})
            return action, f"auto-safe ({ex['type']})"

    # No confident safe mapping -> default to human.
    action.update({"category": "general", "requires_michael_approval": True,
                   "exec": {"type": "advisory", "note": "no confident safe mapping; needs operator"}})
    return action, "approval (unmapped)"


def translate():
    try:
        src = json.loads(SRC.read_text()) if SRC.exists() else {}
    except Exception as e:  # noqa
        print(f"[warn] cannot read {SRC.name}: {e}")
        src = {}
    recs = src.get("queue") or ([src["recommended_next_action"]] if src.get("recommended_next_action") else [])

    actions, summary = [], []
    for rec in recs:
        a, why = map_action(rec)
        actions.append(a)
        summary.append({"id": a["id"], "auto_safe": not a["requires_michael_approval"], "why": why})

    return {"generated_at": _now(), "source": "operator_next_actions.json",
            "translator": "hoch_action_translator", "actions": actions}, summary


if __name__ == "__main__":
    queue, summary = translate()
    write = "--write" in sys.argv
    if write:
        OUT.write_text(json.dumps(queue, indent=2))
    auto = sum(1 for s in summary if s["auto_safe"])
    print(json.dumps({"written": write, "out": str(OUT.relative_to(REPO)) if write else None,
                      "total": len(summary), "auto_safe": auto, "to_approval": len(summary) - auto,
                      "detail": summary}, indent=2))
