"""T1-F2 negative regression guard (2026-07-19, executed-evidence finding).

PROVES mutation of the authoritative goal state by a no-exec computation is impossible:
compute(execute=False) may write ONLY the clearly-marked preview artifact; the
authoritative goal_state.json must remain BYTE-IDENTICAL. Also covers the T1-F3
pipeline-exit mechanism contract.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load_engine():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "goal_engine_guard_test", ROOT / "scripts" / "goal" / "goal_engine.py")
    ge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ge)
    return ge


def _hermetic(ge, tmp_path, monkeypatch):
    """Point the engine at a hermetic sandbox with a sentinel authoritative state."""
    contract = tmp_path / "contract.json"
    reqs = tmp_path / "reqs.json"
    contract.write_text(json.dumps({
        "north_star": "test", "goal_hierarchy": {"3_current_champion_product": {}},
        "hard_constraint": {"statement": "no fake green"}}))
    reqs.write_text(json.dumps({"requirements": [{
        "id": "REQ-T", "layer": "GOV", "statement": "t", "owner": "agent",
        "blocking": True, "weight": 1, "validator": "python3 -c 'print(1)'",
        "evidence_path": "contract.json", "freshness_sla_hours": 999}]}))
    out_dir = tmp_path / "goal"
    out_dir.mkdir()
    state = out_dir / "goal_state.json"
    sentinel = json.dumps({"authoritative": True, "metrics": {"real": 42}})
    state.write_text(sentinel)
    monkeypatch.setattr(ge, "CONTRACT", contract)
    monkeypatch.setattr(ge, "REQUIREMENTS", reqs)
    monkeypatch.setattr(ge, "OUT_DIR", out_dir)
    monkeypatch.setattr(ge, "STATE_PATH", state)
    monkeypatch.setattr(ge, "ROOT", tmp_path)
    return state, sentinel


def test_no_exec_cannot_mutate_authoritative_state(tmp_path, monkeypatch):
    ge = _load_engine()
    state, sentinel = _hermetic(ge, tmp_path, monkeypatch)
    before = hashlib.sha256(state.read_bytes()).hexdigest()

    ge.compute(execute=False)

    after = hashlib.sha256(state.read_bytes()).hexdigest()
    assert before == after, "MUTATION: no-exec touched the authoritative goal_state (T1-F2 regression)"
    assert state.read_text() == sentinel


def test_no_exec_writes_only_marked_preview(tmp_path, monkeypatch):
    ge = _load_engine()
    state, _ = _hermetic(ge, tmp_path, monkeypatch)

    result = ge.compute(execute=False)

    preview = state.with_name("goal_state.preview_no_exec.json")
    assert preview.exists(), "no-exec must persist its projection to the preview artifact"
    p = json.loads(preview.read_text())
    assert "NO_EXEC_PREVIEW" in p.get("nature", ""), "preview must be clearly marked non-authoritative"
    assert result["requirements"][0]["state"] == "VALIDATOR_NOT_RUN"
    # and nothing else in the goal dir was created/altered
    assert sorted(f.name for f in state.parent.iterdir()) == [
        "goal_state.json", "goal_state.preview_no_exec.json"]


def test_execute_true_still_writes_authoritative(tmp_path, monkeypatch):
    """Positive control: the fix must not break real computations."""
    ge = _load_engine()
    state, sentinel = _hermetic(ge, tmp_path, monkeypatch)

    ge.compute(execute=True)

    assert state.read_text() != sentinel, "a real run must update the authoritative state"
    assert json.loads(state.read_text())["schema"] == "HOCH_GOAL_STATE_v1"


def test_pipefail_mechanism_contract():
    """T1-F3: the pipeline-exit mechanism must propagate the producer's failure through tee,
    and the confirmation script must declare pipefail. FAIL/FINDING => nonzero status."""
    r = subprocess.run(["zsh", "-c", "set -o pipefail; python3 -c 'import sys; sys.exit(7)' | tee /dev/null"],
                       capture_output=True)
    assert r.returncode == 7, "pipefail must surface the producer's exit status through tee"
    r_ok = subprocess.run(["zsh", "-c", "set -o pipefail; python3 -c 'print(1)' | tee /dev/null"],
                          capture_output=True)
    assert r_ok.returncode == 0, "success path must remain zero"
    script = (ROOT / "scripts" / "goal" / "run_dependency_runtime_confirmation.sh").read_text()
    assert "set -o pipefail" in script, "confirmation script must declare pipefail (T1-F3)"
