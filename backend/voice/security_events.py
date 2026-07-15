"""Security HIGH findings → rate-limited speech events.

Only HIGH (or equivalent) severity. Fail closed. No secret material in speech.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.voice.policy import load_voice_policy
from backend.voice.sanitizer import sanitize_for_speech

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "UNKNOWN"
_CURSOR_PATH = ROOT / "data" / "runtime" / "voice_security_event_cursor.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_cursor() -> Dict[str, Any]:
    try:
        if _CURSOR_PATH.exists():
            return json.loads(_CURSOR_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"spoken_ids": [], "window_start": time.time(), "events_this_hour": 0}


def _save_cursor(cur: Dict[str, Any]) -> None:
    try:
        _CURSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Cap spoken id list
        ids = cur.get("spoken_ids") or []
        cur["spoken_ids"] = ids[-200:]
        _CURSOR_PATH.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    except Exception:
        pass


def collect_high_security_findings() -> List[Dict[str, Any]]:
    """Gather HIGH findings from posture + cyber swarm (observed only)."""
    findings: List[Dict[str, Any]] = []

    pos_p = ROOT / "coordination" / "security" / "helm_control_posture.json"
    if pos_p.exists():
        try:
            d = json.loads(pos_p.read_text(encoding="utf-8"))
            high = int(d.get("high_findings") or 0)
            open_f = int(d.get("open_findings") or 0)
            pct = d.get("posture_percent")
            assessed = d.get("assessed_at")
            # Individual HIGH controls not implemented
            for c in d.get("controls") or []:
                if not isinstance(c, dict):
                    continue
                sev = str(c.get("severity", "")).upper()
                st = str(c.get("status", "")).upper()
                if sev == "HIGH" and st not in ("IMPLEMENTED", "PASS"):
                    cid = c.get("control_id") or "CTRL"
                    findings.append(
                        {
                            "id": f"posture-{cid}-{st}",
                            "severity": "HIGH",
                            "source": "helm_control_posture",
                            "summary": f"{cid} {c.get('title') or ''} status {st}",
                            "detail": str(c.get("detail") or c.get("evidence") or "")[:160],
                            "observed_at": assessed or _now(),
                        }
                    )
            if high > 0 and not any(f["source"] == "helm_control_posture" for f in findings):
                findings.append(
                    {
                        "id": f"posture-summary-{assessed or 'na'}-{high}",
                        "severity": "HIGH",
                        "source": "helm_control_posture",
                        "summary": f"Posture {pct}% with {high} HIGH and {open_f} open findings",
                        "detail": "",
                        "observed_at": assessed or _now(),
                    }
                )
        except Exception:
            pass

    cyber_p = ROOT / "data" / "prompt_brain" / "cyber_swarm_state.json"
    if cyber_p.exists():
        try:
            d = json.loads(cyber_p.read_text(encoding="utf-8"))
            verdict = d.get("verdict")
            real_high = int(d.get("real_high") or 0)
            if real_high > 0 or str(verdict).upper() in ("NOT_SECURE", "FAIL", "NO_GO"):
                findings.append(
                    {
                        "id": f"cyber-{d.get('at') or 'na'}-{real_high}-{verdict}",
                        "severity": "HIGH",
                        "source": "cyber_swarm_state",
                        "summary": (
                            f"Cyber swarm {verdict}, real HIGH findings {real_high}, "
                            f"coverage {d.get('detection_coverage_pct')}%"
                        ),
                        "detail": str(d.get("why") or "")[:200],
                        "observed_at": d.get("at") or _now(),
                    }
                )
        except Exception:
            pass

    # Goal critical path security
    goal_p = ROOT / "coordination" / "goal" / "goal_state.json"
    if goal_p.exists():
        try:
            g = json.loads(goal_p.read_text(encoding="utf-8"))
            blocker = (g.get("metrics") or {}).get("current_critical_path_blocker")
            if blocker and "SECURITY" in str(blocker).upper():
                findings.append(
                    {
                        "id": f"goal-blocker-{blocker}",
                        "severity": "HIGH",
                        "source": "goal_state",
                        "summary": f"Critical path blocker {blocker}",
                        "detail": "Security is the binding constraint on the north-star path",
                        "observed_at": g.get("computed_at") or _now(),
                    }
                )
        except Exception:
            pass

    return findings


def security_events_for_speech(*, mark_spoken: bool = False) -> Dict[str, Any]:
    """Return HIGH findings eligible for speech under rate limit + dedupe."""
    p = load_voice_policy()
    max_per_hour = int(p.get("max_events_per_hour") or 30)
    # Cap security specifically more tightly
    max_sec = min(max_per_hour, 10)

    findings = collect_high_security_findings()
    cur = _load_cursor()
    now = time.time()
    if now - float(cur.get("window_start") or 0) > 3600:
        cur["window_start"] = now
        cur["events_this_hour"] = 0

    spoken = set(cur.get("spoken_ids") or [])
    pending = [f for f in findings if f["id"] not in spoken]
    budget = max(0, max_sec - int(cur.get("events_this_hour") or 0))
    emit = pending[:budget]

    speech_parts = []
    for f in emit:
        speech_parts.append(
            f"Security HIGH. {f['summary']}. {f.get('detail') or ''}".strip()
        )

    if mark_spoken and emit:
        cur["spoken_ids"] = list(spoken) + [f["id"] for f in emit]
        cur["events_this_hour"] = int(cur.get("events_this_hour") or 0) + len(emit)
        _save_cursor(cur)

    if not findings:
        speech = "No HIGH security findings observed in posture or cyber swarm sources."
        status = "LIVE"
    elif not emit:
        speech = (
            f"{len(findings)} HIGH finding(s) known; "
            f"{len(pending)} new; rate-limit or already spoken — no new speech this hour "
            f"({cur.get('events_this_hour')}/{max_sec})."
        )
        status = "LIVE"
    else:
        speech = " ".join(speech_parts)
        status = "LIVE"

    return {
        "truth_class": "HELM_VOICE_SECURITY_EVENTS",
        "status": status,
        "observed_at": _now(),
        "severity_filter": "HIGH",
        "findings_total": len(findings),
        "pending_new": len(pending),
        "emit_count": len(emit),
        "rate_limit": {
            "max_per_hour": max_sec,
            "events_this_hour": cur.get("events_this_hour"),
            "remaining": max(0, max_sec - int(cur.get("events_this_hour") or 0)),
        },
        "events": emit,
        "all_findings": findings,
        "speech_text": sanitize_for_speech(speech),
        "labels": {
            "security_events": "LIVE",
            "severity": "HIGH",
            "findings": "LIVE" if findings else "NONE",
        },
    }
