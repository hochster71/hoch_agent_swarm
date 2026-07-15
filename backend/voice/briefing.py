"""Evidence-backed executive briefings and voice command execution.

Doctrine: every quantitative claim is observed or explicitly UNKNOWN.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.voice.commands import COMMAND_REGISTRY, resolve_command
from backend.voice.policy import (
    audit_log_path,
    is_doorstep_verb,
    load_voice_policy,
    mode_allowed,
    staging_dir,
)
from backend.voice.sanitizer import sanitize_for_speech

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "UNKNOWN"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _label(value: Any, *, observed: bool, freshness: Optional[float] = None) -> str:
    p = load_voice_policy()
    budget = float(p.get("freshness_budget_seconds") or 300)
    if not observed or value is None:
        return "UNKNOWN"
    if isinstance(value, dict) and value.get("state") == UNKNOWN:
        return "UNKNOWN"
    if freshness is not None and freshness > budget:
        return "STALE"
    return "LIVE"


def _as_unknown(reason: str) -> Dict[str, str]:
    return {"state": UNKNOWN, "reason": reason}


def _observe_sources() -> Dict[str, Any]:
    """Pull live HELM truth surfaces. Fail-closed to UNKNOWN per source."""
    sources: Dict[str, Any] = {
        "observed_at": _now(),
        "runtime": _as_unknown("not collected"),
        "factories": _as_unknown("not collected"),
        "authority": _as_unknown("not collected"),
        "tasks": _as_unknown("not collected"),
        "agents": _as_unknown("not collected"),
        "security": _as_unknown("not collected"),
        "events": _as_unknown("not collected"),
        "census": _as_unknown("not collected"),
        "orchestrator": _as_unknown("not collected"),
        "approvals_file": _as_unknown("not collected"),
        "bus_doorstep": _as_unknown("not collected"),
        "goal": _as_unknown("not collected"),
        "repo": _as_unknown("not collected"),
    }
    freshness: Dict[str, Optional[float]] = {}

    try:
        from backend.truth.runtime_source import concurrency_truth, POINTER
        import time

        sources["runtime"] = concurrency_truth(configured_capacity=4)
        freshness["runtime"] = (
            float(time.time() - POINTER.stat().st_mtime) if POINTER.exists() else None
        )
    except Exception as e:
        sources["runtime"] = _as_unknown(f"runtime unreadable: {e}")
        freshness["runtime"] = None

    try:
        from backend.truth.integrity import canonical_factories, FACTORY_REGISTRY
        import time

        sources["factories"] = canonical_factories()
        freshness["factories"] = (
            float(time.time() - FACTORY_REGISTRY.stat().st_mtime)
            if FACTORY_REGISTRY.exists()
            else None
        )
    except Exception as e:
        sources["factories"] = _as_unknown(f"factories unreadable: {e}")
        freshness["factories"] = None

    try:
        from backend.council.founder_gate import pending, verify_chain

        chain_ok, chain_msg = verify_chain()
        sources["authority"] = {
            "pending_escalations": pending(),
            "chain_intact": chain_ok,
            "chain_message": chain_msg,
        }
        freshness["authority"] = 0.0
    except Exception as e:
        sources["authority"] = _as_unknown(f"authority unreadable: {e}")
        freshness["authority"] = None

    try:
        import backend.helm_live_api as helm

        sources["tasks"] = helm.live_tasks()
        sources["events"] = helm.live_events()
        sources["security"] = helm.live_security()
        sources["census"] = helm.live_census()
        freshness["tasks"] = 0.0
        freshness["events"] = 0.0
        freshness["security"] = 0.0
        freshness["census"] = 0.0
    except Exception as e:
        sources["tasks"] = _as_unknown(f"tasks unreadable: {e}")
        sources["events"] = _as_unknown(f"events unreadable: {e}")
        sources["security"] = _as_unknown(f"security unreadable: {e}")
        sources["census"] = _as_unknown(f"census unreadable: {e}")

    try:
        from backend.orchestrator.founder_orchestrator import decide

        sources["orchestrator"] = decide()
        freshness["orchestrator"] = 0.0
    except Exception as e:
        sources["orchestrator"] = _as_unknown(f"orchestrator unreadable: {e}")
        freshness["orchestrator"] = None

    # artifacts/approvals/queue.json
    try:
        qpath = ROOT / "artifacts" / "approvals" / "queue.json"
        if qpath.exists():
            data = json.loads(qpath.read_text(encoding="utf-8"))
            approvals = data.get("approvals") or []
            pending_a = [a for a in approvals if str(a.get("status", "")).upper() == "PENDING"]
            sources["approvals_file"] = {
                "pending_count": len(pending_a),
                "pending": pending_a[:20],
                "total": len(approvals),
            }
            freshness["approvals_file"] = 0.0
        else:
            sources["approvals_file"] = {
                "pending_count": 0,
                "pending": [],
                "total": 0,
                "note": "queue file absent — treated as empty, not invented pending",
            }
            freshness["approvals_file"] = 0.0
    except Exception as e:
        sources["approvals_file"] = _as_unknown(f"approvals unreadable: {e}")
        freshness["approvals_file"] = None

    # coordination bus doorstep
    try:
        bus_path = ROOT / "coordination" / "coordination_bus.json"
        if bus_path.exists():
            bus = json.loads(bus_path.read_text(encoding="utf-8"))
            door = []
            lanes = bus.get("lanes") or {}
            for lane_name, lane in lanes.items():
                if isinstance(lane, dict):
                    for item in lane.get("doorstep_for_founder") or []:
                        door.append({"lane": lane_name, "item": item})
            import time as _t
            sources["bus_doorstep"] = {"count": len(door), "items": door[:20]}
            # Freshness computed from the file mtime like every other source — NOT
            # hardcoded fresh. A stale bus must be flagged STALE, never spoken as current.
            freshness["bus_doorstep"] = float(_t.time() - bus_path.stat().st_mtime)
        else:
            sources["bus_doorstep"] = _as_unknown("coordination bus missing")
            freshness["bus_doorstep"] = None
    except Exception as e:
        sources["bus_doorstep"] = _as_unknown(f"bus unreadable: {e}")
        freshness["bus_doorstep"] = None

    # Goal registry (weight-sum validators — no invented completion)
    try:
        import time

        gpath = ROOT / "coordination" / "goal" / "goal_state.json"
        if gpath.exists():
            goal = json.loads(gpath.read_text(encoding="utf-8"))
            sources["goal"] = goal
            freshness["goal"] = float(time.time() - gpath.stat().st_mtime)
        else:
            sources["goal"] = _as_unknown("coordination/goal/goal_state.json missing")
            freshness["goal"] = None
    except Exception as e:
        sources["goal"] = _as_unknown(f"goal state unreadable: {e}")
        freshness["goal"] = None

    # Local git repo status (observed; not remote GitHub API)
    try:
        import subprocess

        def _git(*args: str) -> str:
            r = subprocess.run(
                ["git", *args],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode != 0:
                return ""
            return (r.stdout or "").strip()

        branch = _git("rev-parse", "--abbrev-ref", "HEAD") or UNKNOWN
        head = _git("rev-parse", "--short", "HEAD") or UNKNOWN
        dirty = _git("status", "--porcelain")
        dirty_lines = [ln for ln in dirty.splitlines() if ln.strip()] if dirty else []
        # Count only — never list paths that may include secrets dirs in speech
        sources["repo"] = {
            "branch": branch,
            "head": head,
            "dirty_count": len(dirty_lines),
            "clean": len(dirty_lines) == 0,
            "remote_github": UNKNOWN,
            "remote_note": "GitHub remote status not observed in this path — local git only",
        }
        freshness["repo"] = 0.0
    except Exception as e:
        sources["repo"] = _as_unknown(f"git unreadable: {e}")
        freshness["repo"] = None

    sources["_freshness"] = freshness
    return sources


def _goal_lines(src: Dict[str, Any]) -> tuple:
    """Return (label, speech_lines, data)."""
    goal = src.get("goal") or {}
    fresh = (src.get("_freshness") or {}).get("goal")
    if isinstance(goal, dict) and goal.get("state") == UNKNOWN:
        return "UNKNOWN", [f"Goal state: UNKNOWN — {goal.get('reason')}"], {}
    if not isinstance(goal, dict) or not goal:
        return "UNKNOWN", ["Goal state: UNKNOWN."], {}

    label = _label(goal, observed=True, freshness=fresh)
    metrics = goal.get("metrics") or {}
    unknown_reasons = goal.get("metric_unknown_reasons") or {}
    blocker = metrics.get("current_critical_path_blocker")
    founder_pending = metrics.get("founder_only_actions_pending") or []
    north = metrics.get("north_star_completion")
    evidence = metrics.get("evidence_coverage")
    champion = metrics.get("champion_product")
    vfm = metrics.get("verified_founder_minutes_per_shipped_dollar")

    lines: List[str] = []
    if label == "STALE":
        lines.append("Goal state is STALE — older than freshness budget.")
    if champion:
        lines.append(f"Champion product: {champion}.")
    if north is not None:
        lines.append(f"North star completion (validator weight-sum): {north}.")
    else:
        lines.append("North star completion: UNKNOWN.")
    if evidence is not None:
        lines.append(f"Evidence coverage: {evidence}.")
    if blocker:
        lines.append(f"Critical path blocker: {blocker}.")
    else:
        lines.append("Critical path blocker: UNKNOWN.")
    if isinstance(founder_pending, list):
        lines.append(f"Founder-only requirements pending: {len(founder_pending)}.")
        for item in founder_pending[:4]:
            lines.append(f"Founder gate: {item}.")
    if vfm is None:
        reason = unknown_reasons.get("verified_founder_minutes_per_shipped_dollar") or (
            "no verified founder-minutes-per-dollar — not fabricated"
        )
        lines.append(f"Founder-minutes per shipped dollar: UNKNOWN — {reason}")
    else:
        lines.append(f"Founder-minutes per shipped dollar: {vfm}.")

    data = {
        "champion_product": champion,
        "north_star_completion": north,
        "critical_path_blocker": blocker,
        "founder_only_pending_count": len(founder_pending) if isinstance(founder_pending, list) else None,
        "evidence_coverage": evidence,
    }
    return label, lines, data


def _repo_lines(src: Dict[str, Any]) -> tuple:
    repo = src.get("repo") or {}
    if isinstance(repo, dict) and repo.get("state") == UNKNOWN:
        return "UNKNOWN", [f"Repository: UNKNOWN — {repo.get('reason')}"], {}
    if not isinstance(repo, dict):
        return "UNKNOWN", ["Repository: UNKNOWN."], {}
    label = "LIVE"
    lines = [
        f"Local git branch {repo.get('branch')}, head {repo.get('head')}.",
        (
            "Working tree clean."
            if repo.get("clean")
            else f"Working tree dirty: {repo.get('dirty_count')} path(s) observed."
        ),
        "GitHub remote status: UNKNOWN — not queried in this voice path.",
    ]
    return label, lines, {
        "branch": repo.get("branch"),
        "head": repo.get("head"),
        "dirty_count": repo.get("dirty_count"),
        "clean": repo.get("clean"),
    }


def _count_pending_approvals(src: Dict[str, Any]) -> tuple:
    """Returns (count_or_None, label, detail_lines)."""
    lines: List[str] = []
    n = 0
    observed = False

    auth = src.get("authority") or {}
    if isinstance(auth, dict) and auth.get("state") != UNKNOWN:
        pend = auth.get("pending_escalations") or []
        if isinstance(pend, list):
            n += len(pend)
            observed = True
            for p in pend[:5]:
                if isinstance(p, dict):
                    lines.append(
                        f"Escalation: {p.get('title') or p.get('id') or p.get('verb') or 'item'}"
                    )
                else:
                    lines.append(f"Escalation: {p}")

    af = src.get("approvals_file") or {}
    if isinstance(af, dict) and af.get("state") != UNKNOWN:
        observed = True
        n += int(af.get("pending_count") or 0)
        for a in (af.get("pending") or [])[:5]:
            if isinstance(a, dict):
                lines.append(
                    f"Approval: {a.get('task_description') or a.get('approval_id') or 'pending'}"
                )

    bus = src.get("bus_doorstep") or {}
    bus_fresh = (src.get("_freshness") or {}).get("bus_doorstep")
    bus_stale = bus_fresh is not None and bus_fresh > 300  # freshness budget (seconds)
    if isinstance(bus, dict) and bus.get("state") != UNKNOWN:
        observed = True
        if bus_stale:
            # Do NOT count or read stale coordination-bus items as current founder actions.
            lines.append(
                f"Coordination-bus doorstep: STALE — {int(bus.get('count') or 0)} item(s) older "
                "than the freshness budget; not spoken as current founder actions."
            )
        else:
            n += int(bus.get("count") or 0)
            for item in (bus.get("items") or [])[:5]:
                if isinstance(item, dict):
                    lines.append(f"Doorstep ({item.get('lane')}): {str(item.get('item'))[:120]}")

    if not observed:
        return None, "UNKNOWN", ["Founder approvals: UNKNOWN — authority sources unreadable."]
    return n, "LIVE", lines


def _factory_lines(src: Dict[str, Any]) -> tuple:
    fac = src.get("factories") or {}
    fresh = (src.get("_freshness") or {}).get("factories")
    if isinstance(fac, dict) and fac.get("state") == UNKNOWN:
        return "UNKNOWN", ["Factories: UNKNOWN — " + str(fac.get("reason") or "unreadable")]

    # canonical_factories shape varies; handle common patterns
    blocked: List[str] = []
    live: List[str] = []
    unknown: List[str] = []
    items = fac
    if isinstance(fac, dict):
        if "factories" in fac and isinstance(fac["factories"], dict):
            items = fac["factories"]
        elif "by_code" in fac and isinstance(fac["by_code"], dict):
            items = fac["by_code"]

    if isinstance(items, dict):
        for code, info in items.items():
            if code.startswith("_") or code in ("truth_class", "source", "state", "reason"):
                continue
            if not isinstance(info, dict):
                unknown.append(str(code))
                continue
            st = str(
                info.get("state")
                or info.get("status")
                or info.get("overall")
                or info.get("scoped_state")
                or UNKNOWN
            ).upper()
            name = str(info.get("name") or info.get("code") or code)
            if st in ("BLOCKED", "NO_GO", "FAIL", "CONTRADICTED"):
                blocked.append(f"{name}: {st}")
            elif st in ("LIVE", "PASS", "CONFIRMED_LIVE", "GO", "RUNNING", "IMPROVING", "CONVERGED"):
                live.append(f"{name}: {st}")
            else:
                unknown.append(f"{name}: {st}")
    elif isinstance(items, list):
        for info in items:
            if not isinstance(info, dict):
                continue
            name = str(info.get("name") or info.get("code") or "factory")
            st = str(info.get("state") or info.get("status") or UNKNOWN).upper()
            if st in ("BLOCKED", "NO_GO", "FAIL"):
                blocked.append(f"{name}: {st}")
            elif st in ("LIVE", "PASS", "GO", "RUNNING"):
                live.append(f"{name}: {st}")
            else:
                unknown.append(f"{name}: {st}")

    label = _label(fac, observed=True, freshness=fresh)
    lines = []
    if blocked:
        lines.append(f"Blocked factories ({len(blocked)}): " + "; ".join(blocked[:8]))
    else:
        lines.append("Blocked factories: none observed.")
    if live:
        lines.append(f"Live/healthy factories ({len(live)}): " + "; ".join(live[:8]))
    if unknown:
        lines.append(f"Unknown/other factories ({len(unknown)}): " + "; ".join(unknown[:8]))
    if not blocked and not live and not unknown:
        lines.append("Factories: structure observed but no factory rows to summarize — UNKNOWN detail.")
        label = "UNKNOWN"
    return label, lines


def _task_summary(src: Dict[str, Any]) -> tuple:
    tasks = src.get("tasks")
    if isinstance(tasks, dict) and tasks.get("state") == UNKNOWN:
        return None, "UNKNOWN", str(tasks.get("reason") or "tasks unreadable")
    if isinstance(tasks, dict):
        # common shapes: counts, active, by_status
        active = tasks.get("active") or tasks.get("active_count")
        total = tasks.get("total") or tasks.get("count")
        by = tasks.get("by_status") or tasks.get("status_counts")
        if isinstance(active, (int, float)):
            return int(active), "LIVE", f"Active tasks observed: {int(active)}"
        if isinstance(total, (int, float)):
            return int(total), "LIVE", f"Tasks observed: {int(total)}"
        if isinstance(by, dict):
            parts = [f"{k}={v}" for k, v in list(by.items())[:6]]
            return sum(int(v) for v in by.values() if isinstance(v, (int, float))) or None, "LIVE", (
                "Task status: " + ", ".join(parts)
            )
        if isinstance(tasks.get("tasks"), list):
            n = len(tasks["tasks"])
            return n, "LIVE", f"Task rows observed: {n}"
    if isinstance(tasks, list):
        return len(tasks), "LIVE", f"Task rows observed: {len(tasks)}"
    return None, "UNKNOWN", "Task counts: UNKNOWN — unrecognized shape."


def _next_move_line(src: Dict[str, Any]) -> str:
    orch = src.get("orchestrator") or {}
    if isinstance(orch, dict) and orch.get("state") == UNKNOWN:
        return f"Next move: UNKNOWN — {orch.get('reason')}"
    if not isinstance(orch, dict):
        return "Next move: UNKNOWN."
    nm = orch.get("next_move")
    if isinstance(nm, dict):
        return (
            f"Next move [{nm.get('tier') or '—'}]: "
            f"{nm.get('code') or ''} {nm.get('action') or ''} — {nm.get('detail') or ''}"
        ).strip()
    needs = orch.get("needs_operator") or []
    auto = orch.get("autonomous_now") or []
    if auto:
        a = auto[0]
        return f"Autonomous now: {a.get('code')} {a.get('action')} — {a.get('detail')}"
    if needs:
        n = needs[0]
        return f"Needs founder: {n.get('code')} {n.get('action')} — {n.get('detail')}"
    return "Next move: UNKNOWN — orchestrator returned no ranked action."


def build_executive_brief() -> Dict[str, Any]:
    src = _observe_sources()
    fresh = src.get("_freshness") or {}
    speech_parts: List[str] = []
    labels: Dict[str, str] = {}
    data: Dict[str, Any] = {"sources_present": []}

    speech_parts.append("HELM executive briefing.")

    # Runtime
    rt = src.get("runtime")
    rt_label = _label(rt, observed=not (isinstance(rt, dict) and rt.get("state") == UNKNOWN), freshness=fresh.get("runtime"))
    labels["runtime"] = rt_label
    if rt_label == "UNKNOWN":
        speech_parts.append("Runtime health: UNKNOWN.")
    elif rt_label == "STALE":
        speech_parts.append("Runtime health: STALE — data older than freshness budget.")
    else:
        if isinstance(rt, dict):
            conc = rt.get("effective_concurrency") or rt.get("concurrency") or rt.get("active")
            cap = rt.get("configured_capacity") or rt.get("capacity")
            overall = rt.get("overall") or rt.get("state") or "LIVE"
            speech_parts.append(
                f"Runtime {overall}. Concurrency {conc if conc is not None else 'UNKNOWN'}"
                + (f" of {cap}." if cap is not None else ".")
            )
        else:
            speech_parts.append("Runtime: LIVE (details compact).")
    data["sources_present"].append("runtime")

    # Tasks / missions
    tcount, tlabel, tline = _task_summary(src)
    labels["missions"] = tlabel
    speech_parts.append(tline if tlabel != "UNKNOWN" else "Active missions: UNKNOWN.")
    data["active_missions"] = tcount if tlabel != "UNKNOWN" else None

    # Approvals
    acount, alabel, alines = _count_pending_approvals(src)
    labels["founder_approvals"] = alabel
    if alabel == "UNKNOWN":
        speech_parts.append("Founder approvals: UNKNOWN.")
    else:
        speech_parts.append(f"Founder approvals pending: {acount}.")
        speech_parts.extend(alines[:3])
    data["founder_approvals_pending"] = acount if alabel != "UNKNOWN" else None

    # Factories
    flabel, flines = _factory_lines(src)
    labels["factories"] = flabel
    speech_parts.extend(flines[:3])
    data["sources_present"].append("factories")

    # Security
    sec = src.get("security")
    if isinstance(sec, dict) and sec.get("state") == UNKNOWN:
        labels["security"] = "UNKNOWN"
        speech_parts.append(f"Security posture: UNKNOWN — {sec.get('reason')}.")
    elif isinstance(sec, dict):
        labels["security"] = "LIVE"
        posture = sec.get("posture") or sec.get("overall") or sec.get("status") or sec.get("state")
        # live_security() reports posture_percent + control counts (no 'posture' key) —
        # read those so a perfect posture is spoken as 100%, not "None".
        if posture is None and sec.get("posture_percent") is not None:
            pct = sec.get("posture_percent"); impl = sec.get("implemented")
            assessed = sec.get("controls_assessed"); hi = sec.get("high_findings")
            opn = sec.get("open_findings"); fw = sec.get("framework") or "controls"
            posture = (f"{pct:.0f}% implemented ({impl} of {assessed} {fw} controls, "
                       f"{opn} open findings, {hi} high)")
        speech_parts.append(f"Security posture: {posture}.")
    else:
        labels["security"] = "UNKNOWN"
        speech_parts.append("Security posture: UNKNOWN.")

    # Goal / critical path
    glabel, glines, gdata = _goal_lines(src)
    labels["goal"] = glabel
    speech_parts.extend(glines[:5])
    data["goal"] = gdata
    data["sources_present"].append("goal")

    # Local repo (not remote GitHub)
    rlabel, rlines, rdata = _repo_lines(src)
    labels["repo"] = rlabel
    speech_parts.append(rlines[0] if rlines else "Repository: UNKNOWN.")
    data["repo"] = rdata

    # Verified revenue (ledger only)
    try:
        from backend.voice.revenue import observe_revenue

        rev = observe_revenue()
        labels["revenue"] = (rev.get("labels") or {}).get("revenue") or "UNKNOWN"
        labels["earning"] = (rev.get("labels") or {}).get("earning") or "NONE"
        speech_parts.append(rev.get("speech_text") or "Revenue: UNKNOWN.")
        data["revenue"] = rev.get("data")
    except Exception as e:
        labels["revenue"] = "UNKNOWN"
        speech_parts.append(f"Revenue: UNKNOWN — {e}.")

    # Next move
    speech_parts.append(_next_move_line(src))
    labels["next_move"] = (
        "LIVE"
        if isinstance(src.get("orchestrator"), dict)
        and src["orchestrator"].get("state") != UNKNOWN
        else "UNKNOWN"
    )

    speech_parts.append(
        "Labels: "
        + ", ".join(f"{k}={v}" for k, v in labels.items())
        + ". Unknown is not complete. Stale is not live."
    )

    raw_speech = " ".join(speech_parts)
    speech = sanitize_for_speech(raw_speech)

    overall = "LIVE"
    if any(v == "UNKNOWN" for v in labels.values()):
        overall = "PARTIAL"
    if all(v == "UNKNOWN" for v in labels.values()):
        overall = "UNKNOWN"
    if any(v == "STALE" for v in labels.values()):
        overall = "STALE" if overall == "LIVE" else overall

    return {
        "truth_class": "HELM_VOICE_BRIEF",
        "status": overall,
        "observed_at": src.get("observed_at") or _now(),
        "persona": load_voice_policy().get("persona"),
        "speech_text": speech,
        "labels": labels,
        "data": data,
        "freshness_seconds": {k: v for k, v in fresh.items()},
        "doctrine": "no_fake_green — every claim observed or UNKNOWN",
    }


def _mission_status(mission: str, src: Dict[str, Any]) -> Dict[str, Any]:
    mission_q = (mission or "").strip().lower()
    if not mission_q:
        return {
            "status": "UNKNOWN",
            "speech_text": sanitize_for_speech("Mission name missing. Status UNKNOWN."),
            "labels": {"mission": "UNKNOWN"},
        }

    hits: List[str] = []
    # Search tasks
    tasks = src.get("tasks")
    rows = []
    if isinstance(tasks, dict):
        rows = tasks.get("tasks") or tasks.get("items") or []
    if isinstance(tasks, list):
        rows = tasks
    for t in rows if isinstance(rows, list) else []:
        blob = json.dumps(t, default=str).lower() if not isinstance(t, str) else t.lower()
        if mission_q in blob:
            if isinstance(t, dict):
                hits.append(
                    f"{t.get('title') or t.get('name') or t.get('mission_id') or t.get('id')}: "
                    f"{t.get('status') or t.get('state') or UNKNOWN}"
                )
            else:
                hits.append(str(t)[:160])

    # Search orchestrator portfolio
    orch = src.get("orchestrator") or {}
    if isinstance(orch, dict):
        for a in orch.get("portfolio") or []:
            if isinstance(a, dict) and mission_q in json.dumps(a, default=str).lower():
                hits.append(
                    f"Factory {a.get('code')}: state {a.get('state')}, action {a.get('action')} — {a.get('detail')}"
                )

    # Heuristic known product names without inventing status
    if not hits:
        speech = (
            f"No observed ledger rows matched '{mission}'. "
            f"Status for that mission is UNKNOWN until Runtime Truth records it."
        )
        return {
            "status": "UNKNOWN",
            "speech_text": sanitize_for_speech(speech),
            "labels": {"mission": "UNKNOWN"},
            "data": {"mission_query": mission, "hits": []},
        }

    speech = f"Mission match for {mission}. " + " ".join(hits[:5])
    return {
        "status": "LIVE",
        "speech_text": sanitize_for_speech(speech),
        "labels": {"mission": "LIVE"},
        "data": {"mission_query": mission, "hits": hits[:10]},
    }


def _stage_route(factory: str, topic: str, utterance: str) -> Dict[str, Any]:
    dest = staging_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "schema": "helm-voice-stage-v1",
        "kind": "route_task",
        "staged_at": _now(),
        "factory": factory or UNKNOWN,
        "topic": topic or utterance,
        "utterance": utterance,
        "status": "STAGED",
        "execution": "NOT_EXECUTED",
        "note": "Voice STAGE_ONLY — requires HELM/human claim to execute",
    }
    path = dest / f"route_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    speech = (
        f"Staged route recommendation to {factory or 'unspecified factory'} "
        f"for {topic or 'stated topic'}. Not executed. Awaiting claim and policy check. "
        f"Artifact {path.relative_to(ROOT)}."
    )
    return {
        "status": "STAGED",
        "speech_text": sanitize_for_speech(speech),
        "labels": {"routing": "PLANNED"},
        "data": {"staging_path": str(path.relative_to(ROOT)), "payload": payload},
    }


def _stage_mission(utterance: str) -> Dict[str, Any]:
    dest = staging_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "schema": "helm-voice-stage-v1",
        "kind": "mission_intake",
        "staged_at": _now(),
        "utterance": utterance,
        "status": "STAGED",
        "execution": "NOT_EXECUTED",
    }
    path = dest / f"mission_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    speech = (
        f"Mission intake staged from voice. Not launched. "
        f"Review artifact {path.relative_to(ROOT)} before dispatch."
    )
    return {
        "status": "STAGED",
        "speech_text": sanitize_for_speech(speech),
        "labels": {"mission_intake": "PLANNED"},
        "data": {"staging_path": str(path.relative_to(ROOT)), "payload": payload},
    }


def _audit(entry: Dict[str, Any]) -> None:
    try:
        path = audit_log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def execute_voice_command(
    *,
    command_id: Optional[str] = None,
    utterance: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a governed voice command. Never invents LIVE metrics."""
    cmd, parsed_args = resolve_command(command_id, utterance)
    merged_args = {**parsed_args, **(args or {})}

    if cmd is None:
        result = {
            "truth_class": "HELM_VOICE_COMMAND",
            "status": "UNKNOWN",
            "command": None,
            "mode": None,
            "speech_text": sanitize_for_speech(
                "Command not recognized. Say executive brief, founder approvals, "
                "blocked factories, or highest priority mission. "
                "I will not invent a dashboard."
            ),
            "labels": {"command": "UNKNOWN"},
            "observed_at": _now(),
            "data": {"utterance": utterance, "command_id": command_id},
        }
        _audit({**result, "event": "voice_command_unknown"})
        return result

    mode = cmd["mode"]
    if mode == "DOORSTEP" or is_doorstep_verb(cmd["id"]):
        result = {
            "truth_class": "HELM_VOICE_COMMAND",
            "status": "DOORSTEP",
            "command": cmd["id"],
            "mode": "DOORSTEP",
            "speech_text": sanitize_for_speech(
                f"{cmd['id'].replace('_', ' ').title()} requires founder approval. "
                f"Voice will not execute deploy, spend, keys, sign, or money moves. "
                f"Stage it on the doorstep for the founder."
            ),
            "labels": {"execution": "BLOCKED", "gate": "DOORSTEP"},
            "observed_at": _now(),
            "data": {
                "command": cmd["id"],
                "description": cmd["description"],
                "execution_allowed": False,
            },
        }
        _audit({**result, "event": "voice_command_doorstep_blocked"})
        return result

    if not mode_allowed(mode):
        result = {
            "truth_class": "HELM_VOICE_COMMAND",
            "status": "BLOCKED",
            "command": cmd["id"],
            "mode": mode,
            "speech_text": sanitize_for_speech(
                f"Command mode {mode} is not allowed by voice policy."
            ),
            "labels": {"execution": "BLOCKED"},
            "observed_at": _now(),
            "data": {"command": cmd["id"]},
        }
        _audit({**result, "event": "voice_command_mode_blocked"})
        return result

    src = _observe_sources()
    body: Dict[str, Any]

    if cmd["id"] == "executive_brief":
        brief = build_executive_brief()
        body = {
            "status": brief["status"],
            "speech_text": brief["speech_text"],
            "labels": brief["labels"],
            "data": brief.get("data"),
            "freshness_seconds": brief.get("freshness_seconds"),
        }
    elif cmd["id"] == "founder_approvals":
        acount, alabel, alines = _count_pending_approvals(src)
        if alabel == "UNKNOWN":
            speech = "Founder approvals: UNKNOWN. Authority sources unreadable."
        else:
            speech = f"Founder approvals pending: {acount}. " + " ".join(alines[:6])
        body = {
            "status": alabel,
            "speech_text": sanitize_for_speech(speech),
            "labels": {"founder_approvals": alabel},
            "data": {"pending_count": acount if alabel != "UNKNOWN" else None, "details": alines},
        }
    elif cmd["id"] == "blocked_factories":
        flabel, flines = _factory_lines(src)
        body = {
            "status": flabel,
            "speech_text": sanitize_for_speech(" ".join(flines)),
            "labels": {"factories": flabel},
            "data": {"lines": flines},
        }
    elif cmd["id"] == "runtime_health":
        rt = src.get("runtime")
        fl = (src.get("_freshness") or {}).get("runtime")
        label = _label(
            rt,
            observed=not (isinstance(rt, dict) and rt.get("state") == UNKNOWN),
            freshness=fl,
        )
        if label == "UNKNOWN":
            speech = "Runtime health: UNKNOWN."
        else:
            speech = f"Runtime health: {label}. Snapshot: {json.dumps(rt, default=str)[:400]}"
        body = {
            "status": label,
            "speech_text": sanitize_for_speech(speech),
            "labels": {"runtime": label},
            "data": {"runtime": rt, "freshness_seconds": fl},
        }
    elif cmd["id"] == "highest_priority_mission":
        glabel, glines, gdata = _goal_lines(src)
        parts = []
        if gdata.get("critical_path_blocker"):
            parts.append(f"Critical path blocker: {gdata['critical_path_blocker']}.")
        if gdata.get("champion_product"):
            parts.append(f"Champion: {gdata['champion_product']}.")
        parts.append(_next_move_line(src))
        label = glabel if glabel != "UNKNOWN" else (
            "LIVE"
            if isinstance(src.get("orchestrator"), dict)
            and src["orchestrator"].get("state") != UNKNOWN
            else "UNKNOWN"
        )
        body = {
            "status": label,
            "speech_text": sanitize_for_speech(" ".join(parts)),
            "labels": {"priority": label, "goal": glabel},
            "data": {
                "goal": gdata,
                "orchestrator_next": (src.get("orchestrator") or {}).get("next_move"),
            },
        }
    elif cmd["id"] == "goal_status":
        glabel, glines, gdata = _goal_lines(src)
        body = {
            "status": glabel,
            "speech_text": sanitize_for_speech(" ".join(glines)),
            "labels": {"goal": glabel},
            "data": gdata,
        }
    elif cmd["id"] == "repo_status":
        rlabel, rlines, rdata = _repo_lines(src)
        body = {
            "status": rlabel,
            "speech_text": sanitize_for_speech(" ".join(rlines)),
            "labels": {"repo": rlabel, "github_remote": "UNKNOWN"},
            "data": rdata,
        }
    elif cmd["id"] == "factory_brief":
        from backend.voice.factory_agents import observe_factory

        fac = str(
            merged_args.get("factory")
            or (utterance or "").strip()
            or ""
        )
        body = observe_factory(fac)
        # normalize to command body shape
        body = {
            "status": body.get("status"),
            "speech_text": body.get("speech_text"),
            "labels": body.get("labels") or {},
            "data": body,
        }
    elif cmd["id"] == "role_brief":
        from backend.voice.role_agents import observe_role

        role = str(merged_args.get("role") or "")
        utt = (utterance or "").lower()
        if not role:
            if "ciso" in utt or "security" in utt:
                role = "ciso"
            elif "cfo" in utt or "finance" in utt:
                role = "cfo"
            elif "qa" in utt or "verifier" in utt:
                role = "qa"
            elif "mission control" in utt or "ops" in utt:
                role = "ops"
            elif "founder" in utt:
                role = "founder"
            else:
                role = "founder"
        rb = observe_role(role)
        body = {
            "status": rb.get("status"),
            "speech_text": rb.get("speech_text"),
            "labels": rb.get("labels") or {},
            "data": rb,
        }
    elif cmd["id"] == "revenue_status":
        from backend.voice.revenue import observe_revenue

        rev = observe_revenue()
        body = {
            "status": rev.get("status"),
            "speech_text": rev.get("speech_text"),
            "labels": rev.get("labels") or {},
            "data": rev.get("data"),
        }
    elif cmd["id"] == "security_alerts":
        from backend.voice.security_events import security_events_for_speech

        se = security_events_for_speech(mark_spoken=False)
        body = {
            "status": se.get("status"),
            "speech_text": se.get("speech_text"),
            "labels": se.get("labels") or {},
            "data": {
                "emit_count": se.get("emit_count"),
                "findings_total": se.get("findings_total"),
                "events": se.get("events"),
                "rate_limit": se.get("rate_limit"),
            },
        }
    elif cmd["id"] == "mission_ops":
        from backend.mission_control.mission_state import (
            build_mission_state,
            render_speech,
            write_mission_state,
        )

        try:
            st = write_mission_state()
        except Exception:
            st = build_mission_state()
        body = {
            "status": (st.get("overall") or {}).get("status") or "UNKNOWN",
            "speech_text": sanitize_for_speech(render_speech(st)),
            "labels": {
                "mission": (st.get("overall") or {}).get("status") or "UNKNOWN",
                "revenue": (st.get("revenue") or {}).get("status") or "UNKNOWN",
            },
            "data": {
                "dashboard": st.get("dashboard"),
                "critical_path": st.get("critical_path"),
                "overall": st.get("overall"),
                "mission": st.get("mission"),
            },
        }
    elif cmd["id"] == "security_posture":
        sec = src.get("security")
        if isinstance(sec, dict) and sec.get("state") == UNKNOWN:
            body = {
                "status": "UNKNOWN",
                "speech_text": sanitize_for_speech(
                    f"Security posture: UNKNOWN — {sec.get('reason')}"
                ),
                "labels": {"security": "UNKNOWN"},
                "data": {"security": sec},
            }
        else:
            body = {
                "status": "LIVE",
                "speech_text": sanitize_for_speech(
                    f"Security posture observed: {json.dumps(sec, default=str)[:500]}"
                ),
                "labels": {"security": "LIVE"},
                "data": {"security": sec},
            }
    elif cmd["id"] == "overnight_summary":
        events = src.get("events")
        if isinstance(events, dict) and events.get("state") == UNKNOWN:
            body = {
                "status": "UNKNOWN",
                "speech_text": sanitize_for_speech(
                    f"Overnight summary: UNKNOWN — {events.get('reason')}"
                ),
                "labels": {"events": "UNKNOWN"},
                "data": {},
            }
        else:
            # Do not invent "overnight" window if timestamps are missing
            n = 0
            sample = []
            if isinstance(events, dict):
                items = events.get("events") or events.get("items") or events.get("recent") or []
                if isinstance(items, list):
                    n = len(items)
                    sample = items[:5]
                elif isinstance(events.get("count"), int):
                    n = events["count"]
            elif isinstance(events, list):
                n = len(events)
                sample = events[:5]
            speech = (
                f"Recent observed events: {n}. "
                f"I will not claim an overnight window without timestamp evidence. "
                f"Sample: {json.dumps(sample, default=str)[:400]}"
            )
            body = {
                "status": "LIVE" if n or sample else "UNKNOWN",
                "speech_text": sanitize_for_speech(speech),
                "labels": {"events": "LIVE" if n or sample else "UNKNOWN"},
                "data": {"event_count": n, "sample": sample},
            }
    elif cmd["id"] == "mission_status":
        body = _mission_status(str(merged_args.get("mission") or ""), src)
    elif cmd["id"] == "evidence_gaps":
        # Honest: surface orchestrator escalations + blocked factories as gap proxies
        flabel, flines = _factory_lines(src)
        speech = (
            "Evidence gaps before release are only claimed from observed blockers. "
            + " ".join(flines[:3])
            + " "
            + _next_move_line(src)
            + " Final release GO is not voice authority."
        )
        body = {
            "status": flabel if flabel != "UNKNOWN" else "UNKNOWN",
            "speech_text": sanitize_for_speech(speech),
            "labels": {"evidence": flabel, "release_authority": "BLOCKED"},
            "data": {"factory_lines": flines},
        }
    elif cmd["id"] == "idle_agents":
        body = {
            "status": "UNKNOWN",
            "speech_text": sanitize_for_speech(
                "Idle agent reassignment requires the agent accountability ledger. "
                "Without attributed evidence package, utilization is UNKNOWN. "
                "I will not invent idle workers."
            ),
            "labels": {"agents": "UNKNOWN"},
            "data": {"reason": "no fabricated agent leaderboard; see /api/v1/helm/agents"},
        }
        try:
            import backend.helm_live_api as helm
            # Prefer reusing agents endpoint logic if importable without request cycle
            # Fall through — keep UNKNOWN unless we can observe
            _ = helm  # reserved for future direct call
        except Exception:
            pass
    elif cmd["id"] == "route_task":
        body = _stage_route(
            str(merged_args.get("factory") or ""),
            str(merged_args.get("topic") or utterance or ""),
            utterance or "",
        )
    elif cmd["id"] == "stage_mission":
        body = _stage_mission(utterance or json.dumps(merged_args))
    else:
        body = {
            "status": "UNKNOWN",
            "speech_text": sanitize_for_speech(
                f"Command {cmd['id']} is registered but handler not implemented. Status UNKNOWN."
            ),
            "labels": {"command": "UNKNOWN"},
            "data": {},
        }

    result = {
        "truth_class": "HELM_VOICE_COMMAND",
        "command": cmd["id"],
        "mode": mode,
        "description": cmd["description"],
        "observed_at": _now(),
        "persona": load_voice_policy().get("persona"),
        **body,
    }
    result["speech_text"] = sanitize_for_speech(result.get("speech_text") or "")
    _audit(
        {
            "event": "voice_command",
            "command": cmd["id"],
            "mode": mode,
            "status": result.get("status"),
            "observed_at": result["observed_at"],
            "utterance": (utterance or "")[:300],
        }
    )
    return result
