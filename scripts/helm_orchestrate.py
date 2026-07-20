#!/usr/bin/env python3
"""HELM orchestration — bring ChatGPT (the Orchestrator role) into the brain.

HELM dispatches the Orchestrator role (bound to openai/gpt-5.6) to decompose a goal
into a plan. Same governed door as the auditor: fail-closed unless HELM_DISPATCH_ENABLED
+ OPENAI_API_KEY are present. The plan is written as evidence — HELM decides, ChatGPT advises.

Usage:  set -a; . ~/.helm/helm.env; set +a
        python3 scripts/helm_orchestrate.py "decompose GOAL_HELM into the next 5 tasks"
"""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "coordination" / "goal" / "orchestration"


def build_prompt(ask: str) -> str:
    goal = (ROOT / "coordination" / "goal" / "helm_goal.json")
    pert = (ROOT / "coordination" / "goal" / "helm_pert.json")
    ctx = ""
    for p in (goal, pert):
        if p.exists():
            ctx += f"\n=== {p.name} ===\n" + p.read_text()[:4000]
    return (
        "You are the HELM Orchestrator (Chief of Staff). You PLAN and sequence; you do "
        "not approve, audit, or write production code. Given HELM's GOAL and PERT below, "
        f"produce a concrete, ordered plan for this request:\n\n  {ask}\n\n"
        "Output: a short ordered task list, each with the responsible ROLE (builder/auditor/"
        "orchestrator/founder), its dependency, and why. Flag any founder-gated items.\n"
        + ctx
    )


def main() -> int:
    ask = " ".join(sys.argv[1:]) or "Decompose GOAL_HELM into the next 5 ordered tasks with owners."
    from backend.dispatch import dispatch
    from backend.helm_runtime.dispatch_gateway import DispatchNotEnabledError
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        r = dispatch(role="orchestrator", capability="planning", prompt=build_prompt(ask))
    except DispatchNotEnabledError as e:
        print(f"[fail-closed] Orchestrator (ChatGPT) not enabled: {e}")
        print("  Founder enables once: add OPENAI_API_KEY to ~/.helm/helm.env + HELM_DISPATCH_ENABLED=1")
        return 3
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"plan_{ts}.md"
    f.write_text(f"# Orchestrator plan ({r.get('provider')}/{r.get('model')}) {ts}\n\n"
                 f"**Ask:** {ask}\n\n{r.get('text','')}\n", encoding="utf-8")
    print(f"HELM tasked the Orchestrator ({r.get('provider')}/{r.get('model')}). Plan → {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
