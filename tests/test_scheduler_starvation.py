"""Regression: a few permanently-failing missions must not starve the executive-loop queue.

Root cause (2026-07-18): failure paths BEFORE validation (authority binding, lease, dispatch)
returned False without counting toward retries or reaching a terminal state, and
evaluate_runnable_tasks treats FAILED as runnable — so a task that failed downstream looped
PENDING→dispatch→fail forever, pinning the queue (throughput stalled at 95 with 3 stuck tasks).

Fix: an attempt cap counted at the single execute_task chokepoint (AFTER the founder gate, so
held/denied tasks are NOT counted). After max_retries genuine attempts a task becomes terminal
EXHAUSTED, which evaluate_runnable_tasks excludes.
"""
import pytest

import backend.mission_control.persistent_scheduler as ps

TABLES = """
CREATE TABLE mission_control_missions(
  mission_id TEXT PRIMARY KEY, name TEXT, target_pod TEXT, command TEXT,
  status TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE mission_control_tasks(
  task_id TEXT PRIMARY KEY, mission_id TEXT, name TEXT, assigned_agent TEXT, status TEXT,
  step_index INTEGER, dependencies TEXT, error_message TEXT, evidence_path TEXT,
  created_at TEXT, updated_at TEXT, mission_prompt TEXT, validator_ctx TEXT);
"""


def _seed(db, task_id, status, prompt="Summarize the module for documentation.", pod="HASF"):
    now = "2026-01-01T00:00:00Z"
    c = ps._sqlite_connect(db)
    c.execute("INSERT OR REPLACE INTO mission_control_missions VALUES (?,?,?,?,?,?,?)",
              (f"M-{task_id}", task_id, pod, "factory", status, now, now))
    c.execute("INSERT OR REPLACE INTO mission_control_tasks "
              "(task_id,mission_id,name,assigned_agent,status,step_index,dependencies,"
              " error_message,evidence_path,created_at,updated_at,mission_prompt,validator_ctx) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (task_id, f"M-{task_id}", "review", "AgentHASF", status, 1, "", "", "",
               now, now, prompt, "{}"))
    c.commit(); c.close()


def _mk(tmp_path, monkeypatch):
    # keep init light + side-effect-free: the real gateway monkeypatches subprocess; not needed
    monkeypatch.setattr(ps, "CouncilDispatchGateway", lambda *a, **k: object())
    db = tmp_path / "t.db"
    c = ps._sqlite_connect(db)
    c.executescript(TABLES)
    c.commit(); c.close()
    s = ps.PersistentScheduler(evidence_dir=tmp_path / "ev")
    s.db_path = db
    return s, db


def test_evaluate_excludes_exhausted(tmp_path, monkeypatch):
    s, db = _mk(tmp_path, monkeypatch)
    _seed(db, "T-P", "PENDING")
    _seed(db, "T-F", "FAILED")
    _seed(db, "T-X", "EXHAUSTED")
    ids = {t["task_id"] for t in s.evaluate_runnable_tasks()}
    assert "T-P" in ids and "T-F" in ids       # PENDING + FAILED are still retried
    assert "T-X" not in ids                     # EXHAUSTED has left the rotation


def test_attempt_cap_exhausts_and_frees_queue(tmp_path, monkeypatch):
    s, db = _mk(tmp_path, monkeypatch)
    # force every genuine attempt to fail downstream (lease acquisition fails, past the gate)
    monkeypatch.setattr(s.lease_manager, "acquire_lease", lambda *a, **k: None)
    _seed(db, "T-STUCK", "PENDING")
    task = {"task_id": "T-STUCK", "target_pod": "HASF", "name": "review",
            "mission_prompt": "Summarize the module for documentation.",
            "required_capability": None, "dispatch_type": "LOCAL_OLLAMA"}

    results = [s.execute_task(dict(task)) for _ in range(s.max_retries + 1)]
    assert all(r is False for r in results)     # every attempt failed downstream

    c = ps._sqlite_connect(db)
    st = c.execute("SELECT status FROM mission_control_tasks WHERE task_id='T-STUCK'").fetchone()[0]
    c.close()
    assert st == "EXHAUSTED"                     # terminal after max_retries genuine attempts
    assert "T-STUCK" not in {t["task_id"] for t in s.evaluate_runnable_tasks()}  # queue freed


def test_held_task_leaves_rotation_and_is_not_exhausted(tmp_path, monkeypatch):
    """A founder-gated task is escalated ONCE, moved to terminal-for-runnable HELD_FOUNDER,
    and leaves the rotation — it is NOT counted toward the attempt cap (that only bounds
    tasks past the gate) and NOT auto-EXHAUSTED. This stops the re-escalation loop that
    starved the queue, while the task correctly awaits the founder."""
    s, db = _mk(tmp_path, monkeypatch)
    _seed(db, "T-HELD", "PENDING", prompt="Deploy the app to production and publish to the App Store.")
    task = {"task_id": "T-HELD", "target_pod": "HASF", "name": "release",
            "mission_prompt": "Deploy the app to production and publish to the App Store.",
            "required_capability": None, "dispatch_type": "LOCAL_OLLAMA"}
    for _ in range(s.max_retries + 3):
        s.execute_task(dict(task))
    assert s.attempts.get("T-HELD", 0) == 0          # held before the cap → never counted
    c = ps._sqlite_connect(db)
    st = c.execute("SELECT status FROM mission_control_tasks WHERE task_id='T-HELD'").fetchone()[0]
    c.close()
    assert st == "HELD_FOUNDER"                       # escalated once, awaiting founder
    assert st != "EXHAUSTED"
    assert "T-HELD" not in {t["task_id"] for t in s.evaluate_runnable_tasks()}  # left the queue
