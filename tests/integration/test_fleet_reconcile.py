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


def test_extract_catches_pathlib_chains():
    # HOCH code builds paths via pathlib, not literal slash-strings — the extractor must catch both.
    txt = 'OUT = ROOT / "frontend" / "data" / "brain_live.json"\nOUT.write_text(x)\n'
    got = R.extract_output_paths(txt)
    assert "frontend/data/brain_live.json" in got


def test_anchor_normalizes_root_prefixes():
    # same file reached via different var prefixes must normalize to one key (else contention is missed)
    assert R._anchor("/Users/x/repo/data/prompt_brain/champion_registry.json") == "data/prompt_brain/champion_registry.json"


def test_reconcile_from_synthetic_job_list_is_honest_about_unresolved():
    # jobs whose plists don't resolve are reported, not silently dropped or fabricated
    r = R.reconcile(source_jobs=[{"label": "com.hoch.nonexistent.job"}], source_note="synthetic")
    assert r["job_source"] == "synthetic"
    assert "com.hoch.nonexistent.job" in r["unresolved_plists"]
    assert r["safety"]["never_executes"] is True


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


def test_recommendation_handles_cross_class_contention():
    # regression: the real Mac run found tasks/phase50_tasks.json written by an OPS/HEALTH job AND a
    # PHASE job — different classes. Per-class grouping missed it; per-file must catch it.
    job_class = {"com.hoch.phase60.neo.reconciler": "OPS/HEALTH",
                 "com.hoch.phase63.research.traces": "PHASE (build)"}
    contention = {"tasks/phase50_tasks.json": ["com.hoch.phase60.neo.reconciler", "com.hoch.phase63.research.traces"]}
    plan = R.recommend(job_class, contention)
    assert len(plan["recommendations"]) == 1
    rec = plan["recommendations"][0]
    assert rec["contested_file"] == "tasks/phase50_tasks.json"
    assert set(rec["writers"]) == set(contention["tasks/phase50_tasks.json"])
    assert len(plan["actions"]) == 1  # one loser -> one staged T3 stop
    assert plan["actions"][0]["executed"] is False


def test_all_actions_are_inert_T3():
    job_class = {"com.hoch.daemon": "EXECUTOR/CADENCE", "com.hoch.brain.cadence": "EXECUTOR/CADENCE"}
    contention = {"data/prompt_brain/champion_registry.json": ["com.hoch.brain.cadence", "com.hoch.daemon"]}
    plan = R.recommend(job_class, contention)
    assert plan["actions"], "expected at least one staged stop action"
    for a in plan["actions"]:
        assert a["executed"] is False
        assert a["status"] == "PENDING_OPERATOR_APPROVAL_T3"
        assert a["tier"] == "T3"


def test_evidence_tags_write_vs_read():
    scripts = {
        "scripts/writer.sh": "python3 -m backend.writer\n",
        "backend/writer.py": "Path('tasks/phase50_tasks.json').write_text(x)\n",
        "scripts/reader.sh": "python3 -m backend.reader\n",
        "backend/reader.py": "data = json.load(open('tasks/phase50_tasks.json'))\n",
    }
    rd = lambda f: scripts.get(f)
    w = R.evidence_for_path(["/bin/bash", "scripts/writer.sh"], rd, "tasks/phase50_tasks.json")
    r = R.evidence_for_path(["/bin/bash", "scripts/reader.sh"], rd, "tasks/phase50_tasks.json")
    assert any(h["kind"] == "WRITE" for h in w)          # writer flagged WRITE
    assert all(h["kind"] == "read/ref" for h in r)        # reader never flagged WRITE (open(...) w/o mode)


def test_live_feed_carries_fleet_reconcile_key():
    """The deck's live path reads last.fleet_reconcile — the builder must always emit the key
    (None until the reconciler has run, so the panel falls back to the static mirror, never STALE-lies)."""
    sys.path.insert(0, str(ROOT))
    from scripts.write_brain_live import build_live_state
    st = build_live_state()
    assert "fleet_reconcile" in st  # present even when no reconcile has run yet


def test_diagnostic_run_does_not_clobber_canonical_output(tmp_path):
    # a diagnostic run (out_path set, deck_mirror off) must NOT touch the authoritative fleet_reconcile.json
    diag = tmp_path / "fleet_reconcile.from_audit.json"
    canonical_before = R.OUT.stat().st_mtime if R.OUT.exists() else None
    R.reconcile(source_jobs=[{"label": "com.hoch.x"}], source_note="diag", out_path=diag, deck_mirror=False)
    assert diag.exists()
    canonical_after = R.OUT.stat().st_mtime if R.OUT.exists() else None
    assert canonical_before == canonical_after  # canonical untouched


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
