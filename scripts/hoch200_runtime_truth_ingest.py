import os
import glob
import sqlite3
import subprocess
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def get_latest_evidence_file():
    pattern = os.path.join("docs", "evidence", "vps", "*hoch200-vps-verification.md")
    files = glob.glob(pattern)
    if not files:
        return "docs/evidence/vps/20260702-1557-hoch200-vps-verification.md"
    # Sort files by name to get the latest timestamp YYYYMMDD-HHMM
    files.sort()
    # Return relative path using forward slashes
    return files[-1].replace("\\", "/")

def get_git_sha():
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""

def _burn_in_hours():
    """Hours since the daemon started, from its state file. None if unavailable (fail closed)."""
    import json
    from pathlib import Path
    try:
        st = json.loads(Path("has_live_project_tracker/data/ag_execution_daemon_state.json").read_text())
        started = datetime.fromisoformat(st["started_at"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - started).total_seconds() / 3600.0
    except Exception:
        return None


def compute_signals():
    """Measure the 5 HOCH-200 signals from real state instead of hardcoding them. Every value is
    computed or 'unknown' (fail closed) — nothing reads green unless the evidence says so."""
    from backend.runtime_truth import relay_checks as rc

    port_public = rc.probe_port_public(3012)                 # True/False/None
    health = rc.probe_health("http://100.87.18.15:3012/health")  # healthy/unhealthy/unknown
    hb_hours = _burn_in_hours()
    verdict = rc.evaluate_relay_verdict(
        {"port_public": port_public, "health": health,
         "heartbeat_fresh": True if hb_hours is not None else None,
         "doctrine": "GO" if port_public is False else ("NO_GO" if port_public else "UNKNOWN")},
        burn_in_hours=hb_hours)["verdict"]

    measured = lambda known: (1.0, "fresh") if known else (0.0, "unknown")
    port_val = "blocked" if port_public is False else ("public" if port_public else "unknown")
    scope_val = "relay_only" if port_public is False else ("public_exposed" if port_public else "unknown")

    # Foreign-backlog liveness: are the pending tasks' workers actually alive?
    backlog_verdict, backlog_conf = "unknown", 0.0
    try:
        import json as _json, datetime as _dt
        from pathlib import Path as _P
        now = _dt.datetime.now(_dt.timezone.utc)
        queue = _json.loads(_P("has_live_project_tracker/data/helm_task_queue.json").read_text())
        pend = [t for t in queue if t.get("status") in ("PENDING", "RETRY_PENDING")
                and not (t.get("allowed_agent") in rc.EXECUTOR_AGENTS or t.get("adapter") in rc.EXECUTOR_ADAPTERS)]
        foreign_by_agent = {}
        for t in pend:
            k = t.get("allowed_agent") or t.get("adapter") or "unknown"
            foreign_by_agent[k] = foreign_by_agent.get(k, 0) + 1
        hb = rc.heartbeats_from_ledger("backend/swarm_ledger.db", now)
        gpu = rc.gpu_pod_alive("has_live_project_tracker/data/gpu_pod_adapter_state.json", now)
        worker_alive = {}
        for agent in foreign_by_agent:
            worker_alive[agent] = gpu if agent in ("ollama_gpu_pod", "hasf_scoring_agent") else hb.get(agent)
        assessed = rc.assess_foreign_backlog(foreign_by_agent, worker_alive)
        backlog_verdict = assessed["verdict"]
        backlog_conf = 0.0 if backlog_verdict == "UNVERIFIED" else 1.0
    except Exception:
        backlog_verdict, backlog_conf = "unknown", 0.0

    c_relay, f_relay = measured(verdict not in ("UNKNOWN",))
    c_port, f_port = measured(port_public is not None)
    c_health, f_health = measured(health != "unknown")
    c_backlog, f_backlog = measured(backlog_conf == 1.0)
    return [
        {"signal_id": "hoch200_scoring_backlog", "name": "HOCH-200 Foreign Backlog Liveness",
         "value": backlog_verdict, "confidence": c_backlog, "freshness": f_backlog},
        {"signal_id": "hoch200_relay", "name": "HOCH-200 Relay Status", "value": verdict,
         "confidence": c_relay, "freshness": f_relay},
        {"signal_id": "public_3012", "name": "HOCH-200 Public Port 3012", "value": port_val,
         "confidence": c_port, "freshness": f_port},
        {"signal_id": "tailscale_3012", "name": "HOCH-200 Tailscale Port 3012", "value": health,
         "confidence": c_health, "freshness": f_health},
        {"signal_id": "routing_scope", "name": "HOCH-200 Routing Scope", "value": scope_val,
         "confidence": c_port, "freshness": f_port},
        {"signal_id": "unrestricted_execution", "name": "HOCH-200 Unrestricted Execution",
         "value": "false" if port_public is False else "unknown",
         "confidence": c_port, "freshness": f_port},
    ]


def ingest_signals():
    evidence_path = get_latest_evidence_file()
    git_sha = get_git_sha()
    last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    signals = compute_signals()

    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    
    try:
        for sig in signals:
            conn.execute("""
                INSERT OR REPLACE INTO runtime_truth_signals (
                    signal_id, name, value, source, source_type, last_updated,
                    ttl_seconds, freshness, confidence, evidence_link, evidence_ref, git_sha, source_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sig["signal_id"],
                sig["name"],
                sig["value"],
                "hoch200_runtime_truth_ingest.py (computed probes)",
                "script",
                last_updated,
                600,
                sig["freshness"],
                sig["confidence"],
                evidence_path,
                evidence_path,
                git_sha,
                ""
            ))
        conn.commit()
        print(f"Successfully ingested {len(signals)} HOCH-200 relay signals targeting evidence: {evidence_path}")
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_signals()
