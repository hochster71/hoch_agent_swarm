"""CYB-003 — the Node observer must prove detection before reporting absence."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.node_execution_observer import (  # noqa: E402
    DOES_NOT_OBSERVE, OBSERVES, POSITIVE_CONTROL, RUNTIME, WATCHED, observe_node,
)

needs_node = pytest.mark.skipif(not shutil.which("node"), reason="node absent")


def test_every_artifact_declares_its_runtime_and_blind_spots():
    """The defect that started CYB-003: an artifact with no declared scope gets read as
    covering the whole system. A python window nearly 'validated' a vite change."""
    ev = observe_node(["node", "-e", "0"], label="t")
    assert ev["runtime"] == RUNTIME == "node"
    assert ev["DOES_NOT_OBSERVE"] == DOES_NOT_OBSERVE
    assert any("python" in d for d in ev["DOES_NOT_OBSERVE"])
    assert "node runtime ONLY" in ev["scope_warning"]


def test_capability_block_states_both_module_systems():
    ev = observe_node(["node", "-e", "0"], label="t")
    cap = ev["observer_capability"]
    assert set(cap["module_systems"]) == {"CommonJS", "ESM"}
    assert cap["negative_reporting_gated_on"] == "run_positive_control()"


def test_missing_node_is_UNOBSERVED_not_a_clean_window(monkeypatch):
    """THE guard. 'Could not look' must never render as 'nothing loaded'."""
    import backend.helm_runtime.node_execution_observer as m
    monkeypatch.setattr(m, "_node_available", lambda: None)
    ev = m.observe_node(["node", "-e", "0"], label="t")
    assert ev["outcome"] == "UNOBSERVED"
    assert "watched_NOT_LOADED_in_this_run" not in ev, \
        "an unobserved window must not emit negative assertions"


@needs_node
def test_cjs_pipeline_is_observed():
    ev = observe_node(["node", "-e", "require('path')"], label="t")
    assert ev["outcome"] == "COMPLETED"
    assert ev["resolved_via_commonjs"] > 0


@needs_node
def test_esm_pipeline_is_observed():
    """CYB-003 DEFECT-002. Module._load sees require() only; vite is ESM. 192 ESM
    resolutions were invisible while the CJS count looked healthy."""
    ev = observe_node(["node", "--input-type=module", "-e", "import('node:path')"],
                      label="t")
    assert ev["resolved_via_esm"] > 0, "ESM pipeline unobserved — the CYB-003 defect"


def test_positive_control_names_what_it_must_detect():
    assert set(POSITIVE_CONTROL["must_detect"]) <= set(WATCHED)
    assert "uninterpretable" in POSITIVE_CONTROL["rationale"]


def test_observer_declares_esm_as_covered_not_a_blind_spot():
    """Regression: if a Node upgrade breaks module.register the coverage claim must not
    silently survive. OBSERVES is the assertion; the positive control is the proof."""
    assert any("ESM" in o for o in OBSERVES)
    assert not any("ESM" in d for d in DOES_NOT_OBSERVE)
