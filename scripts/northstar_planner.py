#!/usr/bin/env python3
"""NORTHSTAR PLANNER — the piece that ends copy-paste.

Takes ONE northstar goal and decomposes it into a phased task DAG
(Research → Design → Develop → Verify → Package → Launch), refilling the
hoch_loop queue as phases complete. Deterministic template skeleton first
(always works, $0, offline); optional LLM enrichment when a brain is keyed.

SAFETY (fail-closed, matches HAS doctrine):
  - Research/Design/Verify/Package tasks are SAFE (produce docs/plans only).
  - Develop tasks are marked difficulty=hard + require code mode (staged until enabled).
  - Launch/money/legal/submit tasks are FOUNDER_GATED -> staged at the doorstep, never executed.
  - Bounded: emits one phase's tasks per refill (no runaway generation).
  - Never edits the control plane, the guard, or itself (enforced by baseline_guard + DENY_WRITE).
"""
from __future__ import annotations
import datetime, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "has_live_project_tracker/data/hoch_loop_queue.json"
NORTHSTAR = ROOT / "has_live_project_tracker/data/northstar.json"

PHASES = ["RESEARCH", "DESIGN", "DEVELOP", "VERIFY", "PACKAGE", "LAUNCH"]

# per-phase task skeleton: (suffix, task_class, difficulty, founder_gated, builds_doc, template)
PHASE_TASKS = {
    "RESEARCH": [
        ("market", "research", "medium", False, True,
         "Research the market, users, and competitors for: {g}. Write findings + top opportunities."),
        ("requirements", "research", "medium", False, True,
         "Define the requirements and success criteria for: {g}. List must-haves, nice-to-haves, risks."),
    ],
    "DESIGN": [
        ("architecture", "design", "medium", False, True,
         "Design the architecture/approach for: {g}. Components, data flow, tradeoffs, chosen stack."),
        ("plan", "design", "medium", False, True,
         "Write the build plan for: {g}. Milestones, task breakdown, acceptance criteria per milestone."),
    ],
    "DEVELOP": [
        ("build-1", "code", "hard", False, False,
         "Implement the first build slice for: {g}, per the design. Must compile and pass its acceptance check."),
        ("build-2", "code", "hard", False, False,
         "Implement the next build slice for: {g}. Must compile and pass its acceptance check."),
    ],
    "VERIFY": [
        ("verify", "verify", "medium", False, True,
         "Verify the build for: {g}. Run available checks/tests, record real pass/fail evidence."),
    ],
    "PACKAGE": [
        ("package", "analysis", "medium", False, True,
         "Package the deliverable for: {g}. Write release notes, README, and a launch checklist."),
    ],
    "LAUNCH": [
        ("launch", "release", "hard", True, True,
         "FOUNDER GATE: submit/publish/monetize for: {g}. Prepare everything to the door; founder executes."),
    ],
}


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _slug(s):
    words = re.sub(r"[^a-z0-9]+", " ", s.lower()).split()
    out = []
    for w in words:                      # build up to ~28 chars on WORD boundaries (no mid-word cut)
        if len("-".join(out + [w])) > 28:
            break
        out.append(w)
    return "-".join(out) or "northstar"


def _load(p, d):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def _save(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, indent=2))


def _phase_tasks(goal, phase, slug):
    out = []
    for suffix, tclass, diff, gated, builds_doc, tmpl in PHASE_TASKS[phase]:
        tid = f"ns-{slug}-{phase.lower()}-{suffix}"
        doc = f"docs/generated/northstar/{slug}/{phase.lower()}_{suffix}.md"
        task = {
            "task_id": tid,
            "task_name": f"[{phase}] {suffix} — {goal[:48]}",
            "task_class": tclass,
            "difficulty": diff,
            "description": tmpl.format(g=goal) + (f" Write the result to {doc}." if builds_doc else ""),
            "status": "PENDING",
            "northstar": slug,
            "phase": phase,
        }
        # Doc tasks verify via the DEFAULT gate (a real artifact on disk + summary) rather than an
        # exact path — weak local models vary the filename, and we don't want that to fail a
        # genuinely-produced research/design doc. Code tasks (DEVELOP) carry their own gate in code mode.
        if gated:
            task["founder_gated"] = True
            task["policy_category"] = "blocked_release"
        out.append(task)
    return out


def refill(max_phases=1):
    """Emit the next incomplete phase's tasks into the queue. Returns a summary dict."""
    ns = _load(NORTHSTAR, {})
    goal = ns.get("goal")
    if not goal:
        return {"ok": False, "reason": "no northstar goal set in northstar.json"}
    slug = ns.get("slug") or _slug(goal)
    ns["slug"] = slug
    phase = ns.get("current_phase") or "RESEARCH"
    if phase == "DONE":
        return {"ok": True, "phase": "DONE", "added": 0, "note": "northstar complete"}

    q = _load(QUEUE, [])
    have = {t.get("task_id") for t in q}
    # if this phase's tasks are all present and completed, advance
    phase_ids = [t["task_id"] for t in _phase_tasks(goal, phase, slug)]
    present = [t for t in q if t.get("task_id") in phase_ids]
    if present and all(t.get("status") in ("completed", "STAGED_FOR_FOUNDER") for t in present):
        nxt = PHASES.index(phase) + 1
        phase = PHASES[nxt] if nxt < len(PHASES) else "DONE"
        ns["current_phase"] = phase
        _save(NORTHSTAR, ns)
        if phase == "DONE":
            return {"ok": True, "phase": "DONE", "added": 0, "note": "all phases complete"}

    added = 0
    for t in _phase_tasks(goal, phase, slug):
        if t["task_id"] not in have:
            q.append(t)
            added += 1
    _save(QUEUE, q)
    ns["current_phase"] = phase
    ns["updated"] = _now()
    hist = ns.setdefault("history", [])
    hist.append({"ts": _now(), "phase": phase, "added": added})
    _save(NORTHSTAR, ns)
    return {"ok": True, "phase": phase, "added": added, "goal": goal, "slug": slug}


def status():
    ns = _load(NORTHSTAR, {})
    q = _load(QUEUE, [])
    mine = [t for t in q if t.get("northstar") == ns.get("slug")]
    done = len([t for t in mine if t.get("status") == "completed"])
    staged = len([t for t in mine if t.get("status") == "STAGED_FOR_FOUNDER"])
    pend = len([t for t in mine if t.get("status") == "PENDING"])
    return {"goal": ns.get("goal"), "phase": ns.get("current_phase"),
            "tasks": len(mine), "done": done, "staged_at_door": staged, "pending": pend}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "refill"
    if cmd == "set" and len(sys.argv) > 2:
        goal = " ".join(sys.argv[2:])
        _save(NORTHSTAR, {"goal": goal, "slug": _slug(goal), "current_phase": "RESEARCH",
                          "created": _now()})
        print("northstar set:", goal)
    elif cmd == "status":
        print(json.dumps(status(), indent=2))
    else:
        print(json.dumps(refill(), indent=2))
