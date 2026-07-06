"""Tests for computed relay evidence (replaces hardcoded PASS/GO). Enforces no-fake-green: unknowns
and stale/foreign conditions must NOT read green."""
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from backend.runtime_truth import relay_checks as RC  # noqa: E402

NOW = datetime.datetime(2026, 7, 6, 13, 0, tzinfo=datetime.timezone.utc)


def _iso(dt): return dt.isoformat().replace("+00:00", "Z")


def test_heartbeat_fresh_vs_stale():
    fresh = RC.evaluate_heartbeat({"last_heartbeat": _iso(NOW),
                                   "heartbeat_expires_at": _iso(NOW + datetime.timedelta(seconds=60))}, NOW)
    assert fresh["status"] == "HEARTBEAT_FRESH"
    stale = RC.evaluate_heartbeat({"last_heartbeat": _iso(NOW - datetime.timedelta(minutes=10)),
                                   "heartbeat_expires_at": _iso(NOW - datetime.timedelta(minutes=9))}, NOW)
    assert stale["status"] == "HEARTBEAT_STALE"
    assert RC.evaluate_heartbeat({}, NOW)["status"] == "UNKNOWN"   # fail closed


def test_queue_foreign_backlog_is_not_plain_pass():
    # the exact HOCH-200 situation: pending tasks all belong to a non-executor worker
    q = [{"status": "PENDING", "allowed_agent": "hasf_scoring_agent", "adapter": "ollama_gpu_pod"}] * 7
    r = RC.evaluate_queue(q)
    assert r["verdict"] == "FOREIGN_BACKLOG"      # NOT a bare PASS
    assert r["foreign_pending"] == 7 and r["serviceable_pending"] == 0


def test_queue_pass_and_invalid():
    assert RC.evaluate_queue([])["verdict"] == "PASS"
    assert RC.evaluate_queue([{"status": "PENDING", "allowed_agent": "hasf_builder_agent"}])["verdict"] == "PASS"
    assert RC.evaluate_queue("not a list")["verdict"] == "FAIL"


def test_doctrine_requires_confirmed_private():
    assert RC.evaluate_doctrine(True, False, False)["status"] == "GO"       # private, no hold
    assert RC.evaluate_doctrine(True, False, True)["status"] == "NO_GO"     # publicly exposed
    assert RC.evaluate_doctrine(True, False, None)["status"] == "UNKNOWN"   # exposure unverified -> not GO
    assert RC.evaluate_doctrine(True, True, False)["status"] == "HOLD"


def test_relay_verdict_matrix():
    ok = {"port_public": False, "health": "healthy", "heartbeat_fresh": True, "doctrine": "GO"}
    assert RC.evaluate_relay_verdict(ok, burn_in_hours=18.2)["verdict"] == "CONDITIONAL_GO"
    assert RC.evaluate_relay_verdict(ok, burn_in_hours=25)["verdict"] == "GO"
    bad = dict(ok, port_public=True)
    assert RC.evaluate_relay_verdict(bad, burn_in_hours=25)["verdict"] == "NO_GO"
    unk = dict(ok, health="unknown")
    assert RC.evaluate_relay_verdict(unk, burn_in_hours=25)["verdict"] == "UNKNOWN"


def test_probes_fail_closed(monkeypatch=None):
    # health probe to an unreachable URL must be 'unknown', never 'healthy'
    assert RC.probe_health("http://127.0.0.1:9/definitely-down", timeout=0.2) == "unknown"


def test_foreign_backlog_liveness_verdicts():
    pend = {"ollama_gpu_pod": 7}
    assert RC.assess_foreign_backlog({}, {})["verdict"] == "NONE"
    assert RC.assess_foreign_backlog(pend, {"ollama_gpu_pod": True})["verdict"] == "DRAINING"
    assert RC.assess_foreign_backlog(pend, {"ollama_gpu_pod": False})["verdict"] == "STALLED"
    assert RC.assess_foreign_backlog(pend, {"ollama_gpu_pod": None})["verdict"] == "UNVERIFIED"
    assert RC.assess_foreign_backlog(pend, {})["verdict"] == "UNVERIFIED"   # unknown worker -> not 'fine'


def test_gpu_pod_alive_missing_is_down_not_unknown():
    assert RC.gpu_pod_alive("/no/such/gpu_state.json", NOW) is False


def test_cumulative_failed_rate_counts_history():
    import json
    lines = [json.dumps({"verdict": "PASS", "simulated": False}),
             json.dumps({"verdict": "FAIL", "simulated": False, "incident_class": "runner_error"}),
             json.dumps({"verdict": "PASS", "simulated": True}),   # simulated excluded
             json.dumps({"verdict": "PASS", "simulated": False})]
    failed, total = RC.cumulative_failed_from_ledger(lines)
    assert (failed, total) == (1, 3)   # not 0/last-cycle-only


if __name__ == "__main__":
    import traceback
    fns = [(n, f) for n, f in dict(globals()).items() if n.startswith("test_")]
    bad = 0
    for n, f in fns:
        try:
            f()
        except Exception:
            bad += 1; print("FAIL", n); traceback.print_exc()
    print(f"--- {len(fns)-bad}/{len(fns)} passed")
    sys.exit(1 if bad else 0)
