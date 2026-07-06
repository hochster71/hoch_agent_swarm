"""Integration tests for the dry-run fleet reconciler.

Exercises the PURE logic (write-set extraction, contention detection, per-class owner recommendation)
with synthetic plist ProgramArguments + script texts — no launchctl, no real fleet. Also enforces the
T3 invariant: the module must not execute any runtime-stop op, and every staged action must be inert.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import hoch_fleet_reconcile as R  # noqa: E402


# Synthetic script bodies: two EXECUTOR jobs both write the same brain state file (real contention),
# plus a SWARM job that writes a different file (no contention).
SCRIPTS = {
    "scripts/hoch_daemon.sh": "python3 -m backend.orchestrator.founder_orchestrator\n",
    "backend/orchestrator/founder_orchestrator.py":
        "OUT='data/prompt_brain/champion_registry.json'\n"
        "Path(OUT).write_text(json.dumps(x))\n",
    "scripts/hoch_cadence.sh": "python3 -m backend.brain_convergence.cadence\n",
    "backend/brain_convergence/cadence.py":
        "with open('data/prompt_brain/champion_registry.json','w') as f: json.dump(x,f)\n",
    "scripts/start_has_runtime.sh":
        "python3 -m backend.swarm.cyber_swarm\n",
    "backend/swarm/cyber_swarm.py":
        "Path('data/prompt_brain/cyber_swarm_state.json').write_text(s)\n",
}


def fake_read(path):
    return SCRIPTS.get(path)


def test_extract_output_paths_requires_write_call():
    assert R.extract_output_paths("just data/prompt_brain/x.json referenced, no write") == set()
    got = R.extract_output_paths("Path('data/prompt_brain/x.json').write_text(y)")
    assert "data/prompt_brain/x.json" in got


def test_entry_scripts_drops_interpreters():
    assert R.entry_scripts(["/bin/bash", "/x/scripts/hoch_daemon.sh"]) == ["/x/scripts/hoch_daemon.sh"]


def test_write_set_follows_one_level_fanout():
    writes = R.collect_writes_for_job(["/bin/bash", "scripts/hoch_daemon.sh"], fake_read)
    assert "data/prompt_brain/champion_registry.json" in writes


def test_contention_detects_same_file_writers():
    jobs = {
        "com.hoch.daemon": R.collect_writes_for_job(["/bin/bash", "scripts/hoch_daemon.sh"], fake_read),
        "com.hoch.brain.cadence": R.collect_writes_for_job(["/bin/bash", "scripts/hoch_cadence.sh"], fake_read),
        "com.hoch.agent.swarm.runtime": R.collect_writes_for_job(["/bin/bash", "scripts/start_has_runtime.sh"], fake_read),
    }
    contention = R.detect_contention(jobs)
    # both executors write champion_registry.json -> contested
    assert "data/prompt_brain/champion_registry.json" in contention
    assert set(contention["data/prompt_brain/champion_registry.json"]) == {
        "com.hoch.daemon", "com.hoch.brain.cadence"}
    # swarm file has a single writer -> not contested
    assert "data/prompt_brain/cyber_swarm_state.json" not in contention


def test_recommendation_prefers_canonical_owner():
    job_class = {"com.hoch.daemon": "EXECUTOR/CADENCE", "com.hoch.brain.cadence": "EXECUTOR/CADENCE"}
    contention = {"data/prompt_brain/champion_registry.json": ["com.hoch.brain.cadence", "com.hoch.daemon"]}
    plan = R.recommend(job_class, contention)
    rec = plan["recommendations"][0]
    assert rec["canonical_owner"] == "com.hoch.daemon"          # preferred consolidated runtime kept
    assert rec["bootout_candidates"] == ["com.hoch.brain.cadence"]


def test_all_actions_are_inert_T3():
    job_class = {"com.hoch.daemon": "EXECUTOR/CADENCE", "com.hoch.brain.cadence": "EXECUTOR/CADENCE"}
    contention = {"data/prompt_brain/champion_registry.json": ["com.hoch.brain.cadence", "com.hoch.daemon"]}
    plan = R.recommend(job_class, contention)
    assert plan["actions"], "expected at least one staged stop action"
    for a in plan["actions"]:
        assert a["executed"] is False
        assert a["status"] == "PENDING_OPERATOR_APPROVAL_T3"
        assert a["tier"] == "T3"


def test_live_feed_carries_fleet_reconcile_key():
    """The deck's live path reads last.fleet_reconcile — the builder must always emit the key
    (None until the reconciler has run, so the panel falls back to the static mirror, never STALE-lies)."""
    sys.path.insert(0, str(ROOT))
    from scripts.write_brain_live import build_live_state
    st = build_live_state()
    assert "fleet_reconcile" in st  # present even when no reconcile has run yet


def test_module_never_executes_a_stop():
    """T3 guard: no forbidden runtime-stop op is ever handed to subprocess/os.system."""
    src = (ROOT / "scripts" / "hoch_fleet_reconcile.py").read_text()
    # the only subprocess call must be `launchctl list` (read-only enumeration)
    calls = re.findall(r"subprocess\.\w+\(\[([^\]]*)\]", src)
    for c in calls:
        assert "list" in c and not any(op in c for op in R._FORBIDDEN_OPS), f"unsafe subprocess: {c}"
    # no os.system / launchctl bootout|unload|kill as an executed command string
    assert "os.system" not in src
    assert not re.search(r"subprocess\.\w+\([^)]*bootout", src)
