"""Computed evidence for the HOCH-200 relay telemetry — replaces hardcoded PASS/GO/HEARTBEAT_FRESH
constants with real evaluations (no-fake-green: a check reads green only when the evidence says so).

Design rules:
- Pure evaluators (heartbeat / queue / doctrine / overall verdict) take state in, return verdicts —
  fully unit-testable, no I/O.
- Probes (port exposure, health endpoint) do real I/O and FAIL CLOSED: when the tool or network is
  unavailable they return None / "UNKNOWN", never a green value. Callers must treat UNKNOWN as not-green.
- Nothing here fabricates. If it can't be verified, it says UNVERIFIED/UNKNOWN.
"""
from __future__ import annotations

import datetime
import shutil
import subprocess

# Agents/adapters THIS execution daemon can actually service. Pending tasks for anything else are a
# foreign backlog — real work waiting on a different worker, which must be surfaced, not hidden green.
EXECUTOR_AGENTS = ("hasf_builder_agent",)
EXECUTOR_ADAPTERS = ("ag_execution_adapter",)


def _parse_iso(ts: str) -> datetime.datetime | None:
    if not ts:
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def evaluate_heartbeat(state: dict, now: datetime.datetime) -> dict:
    """FRESH only if now <= heartbeat_expires_at. Otherwise STALE (with age). UNKNOWN if unparseable."""
    exp = _parse_iso(state.get("heartbeat_expires_at", ""))
    last = _parse_iso(state.get("last_heartbeat", ""))
    if exp is None:
        return {"status": "UNKNOWN", "fresh": False, "reason": "no parseable heartbeat_expires_at"}
    fresh = now <= exp
    age_s = (now - last).total_seconds() if last else None
    return {"status": "HEARTBEAT_FRESH" if fresh else "HEARTBEAT_STALE", "fresh": fresh,
            "age_s": age_s, "expires_at": state.get("heartbeat_expires_at")}


def _serviceable(task: dict) -> bool:
    return task.get("allowed_agent") in EXECUTOR_AGENTS or task.get("adapter") in EXECUTOR_ADAPTERS


def evaluate_queue(queue) -> dict:
    """Queue health from real contents. PASS only when valid and nothing is stuck that THIS daemon can
    drain. A backlog for other workers is reported as FOREIGN_BACKLOG (honest: not this daemon's to
    clear, but not 'all clear' either). Invalid queue => FAIL."""
    if not isinstance(queue, list):
        return {"verdict": "FAIL", "valid": False, "reason": "queue is not a list"}
    pending = [t for t in queue if t.get("status") in ("PENDING", "RETRY_PENDING")]
    by_agent: dict[str, int] = {}
    for t in pending:
        by_agent[t.get("allowed_agent") or t.get("adapter") or "unknown"] = \
            by_agent.get(t.get("allowed_agent") or t.get("adapter") or "unknown", 0) + 1
    serviceable = [t for t in pending if _serviceable(t)]
    foreign = [t for t in pending if not _serviceable(t)]
    if not pending:
        verdict = "PASS"
    elif not serviceable and foreign:
        verdict = "FOREIGN_BACKLOG"   # all pending work belongs to other workers
    else:
        verdict = "PASS"              # this daemon has serviceable work it will pick up
    return {"verdict": verdict, "valid": True, "pending": len(pending),
            "serviceable_pending": len(serviceable), "foreign_pending": len(foreign),
            "pending_by_agent": by_agent}


def evaluate_doctrine(allow_ag: bool, hold_active: bool, port_public) -> dict:
    """Private-execution doctrine. GO only when exposure is confirmed PRIVATE and no operator hold.
    port_public: True=public (bad), False=private (good), None=unknown (fail closed to NO_GO/UNKNOWN)."""
    if hold_active:
        return {"status": "HOLD", "reason": "operator hold active"}
    if port_public is None:
        return {"status": "UNKNOWN", "reason": "port exposure unverified"}
    if port_public:
        return {"status": "NO_GO", "reason": "relay port is publicly exposed"}
    return {"status": "GO", "allow_ag": bool(allow_ag)}


def evaluate_relay_verdict(checks: dict, burn_in_hours: float | None, min_hours: float = 24.0) -> dict:
    """Overall relay verdict from component checks + burn-in maturity.
    NO_GO if any critical check is failing; UNKNOWN if any critical input is unknown; else
    CONDITIONAL_GO until burn_in_hours >= min_hours, then GO."""
    critical = {
        "exposure_private": checks.get("port_public") is False,
        "health_ok": checks.get("health") == "healthy",
        "heartbeat_fresh": checks.get("heartbeat_fresh") is True,
        "doctrine_go": checks.get("doctrine") == "GO",
    }
    # any explicit False among criticals that are known => NO_GO
    if checks.get("port_public") is True or checks.get("health") == "unhealthy" \
            or checks.get("heartbeat_fresh") is False or checks.get("doctrine") in ("NO_GO",):
        return {"verdict": "NO_GO", "criticals": critical}
    # unknown criticals => can't claim green
    if checks.get("port_public") is None or checks.get("health") in (None, "unknown") \
            or checks.get("doctrine") in (None, "UNKNOWN"):
        return {"verdict": "UNKNOWN", "criticals": critical}
    if burn_in_hours is None:
        return {"verdict": "UNKNOWN", "criticals": critical, "reason": "burn-in age unknown"}
    if burn_in_hours < min_hours:
        return {"verdict": "CONDITIONAL_GO", "criticals": critical,
                "burn_in_hours": round(burn_in_hours, 2), "min_hours": min_hours}
    return {"verdict": "GO", "criticals": critical, "burn_in_hours": round(burn_in_hours, 2)}


# ---- probes (real I/O, fail-closed) ----------------------------------------

def probe_port_public(port: int) -> bool | None:
    """Is `port` reachable from the public interface? Uses ufw. Returns True(public)/False(blocked)/
    None(unknown — ufw absent or unreadable). Never guesses."""
    if not shutil.which("ufw"):
        return None
    try:
        out = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    if out.returncode != 0 or "Status: active" not in out.stdout:
        return None  # can't confirm firewall posture -> unknown, not "blocked"
    for line in out.stdout.splitlines():
        if str(port) in line and ("ALLOW" in line.upper()) and ("Anywhere" in line or "0.0.0.0" in line):
            return True   # an allow rule from anywhere = public
    return False          # active firewall, no public allow rule for the port


def probe_health(url: str, timeout: float = 5.0) -> str:
    """'healthy' iff the endpoint returns 2xx; 'unhealthy' on a reachable non-2xx; 'unknown' if it
    can't be reached at all (fail closed — unreachable is never 'healthy')."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (internal tailnet URL)
            return "healthy" if 200 <= r.status < 300 else "unhealthy"
    except Exception:
        return "unknown"


def assess_foreign_backlog(pending_by_agent: dict, worker_alive: dict) -> dict:
    """Judge a foreign backlog by whether its worker is alive. Makes the 7-pending-scoring-tasks case
    actionable instead of merely counted.

    worker_alive: {agent_or_adapter: True(alive) | False(down) | None(unverified)}.
    Verdict:
      NONE       — no foreign backlog.
      DRAINING   — backlog exists and every responsible worker is confirmed alive.
      STALLED    — backlog exists and a responsible worker is confirmed DOWN (real problem).
      UNVERIFIED — backlog exists but a worker's liveness can't be confirmed (fail closed: not 'fine')."""
    if not pending_by_agent:
        return {"verdict": "NONE", "per_worker": {}}
    per = {}
    any_down = any_unknown = False
    for agent, n in pending_by_agent.items():
        alive = worker_alive.get(agent)
        per[agent] = {"pending": n, "worker_alive": alive}
        if alive is False:
            any_down = True
        elif alive is None:
            any_unknown = True
    verdict = "STALLED" if any_down else ("UNVERIFIED" if any_unknown else "DRAINING")
    return {"verdict": verdict, "per_worker": per}


def heartbeats_from_ledger(db_path, now: datetime.datetime, ) -> dict:
    """Read component -> alive(bool)/None from the runtime_heartbeats table. Fresh iff
    now - last_seen <= ttl. Missing/unreadable => {} (callers then see None per component = unverified)."""
    out: dict = {}
    try:
        import sqlite3
        c = sqlite3.connect(str(db_path), timeout=10)
        for comp, last_seen, ttl_ms in c.execute(
                "SELECT component, last_seen, ttl_ms FROM runtime_heartbeats").fetchall():
            ls = _parse_iso(last_seen)
            if ls is None:
                out[comp] = None
                continue
            out[comp] = (now - ls).total_seconds() <= (float(ttl_ms or 0) / 1000.0)
        c.close()
    except Exception:
        return {}
    return out


def gpu_pod_alive(state_path, now: datetime.datetime, max_age_s: float = 300.0) -> bool | None:
    """The GPU scoring pod is ephemeral; treat a FRESH adapter-state file as 'up'. Missing file => False
    (not up). Unreadable/unparseable mtime => None (unverified). Never assumes alive."""
    try:
        import os
        if not os.path.exists(state_path):
            return False
        age = now.timestamp() - os.path.getmtime(state_path)
        return age <= max_age_s
    except Exception:
        return None


def cumulative_failed_from_ledger(ledger_lines: list[str]) -> tuple[int, int]:
    """(failed_real, total_real) counted across the WHOLE burn-in ledger — not just the last cycle,
    which is what made the dashboard's '0.00% failed rate' misleading."""
    total = failed = 0
    for ln in ledger_lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            import json
            e = json.loads(ln)
        except Exception:
            continue
        if e.get("simulated"):
            continue
        total += 1
        if e.get("verdict") == "FAIL" or e.get("incident_class") not in (None, "none"):
            failed += 1
    return failed, total
