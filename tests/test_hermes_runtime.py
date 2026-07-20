"""HERMES runtime tests — registry, capability selection, dispatcher, learning hooks.

These prove the runtime is OPERATIONAL, not merely present:
  * manifests load and availability is OBSERVED (never asserted)
  * capability → worker selection is explainable and fails closed
  * the dispatcher routes by capability and never imports a vendor entry point
  * the frozen capability registry is composed over, NOT modified
  * learning hooks record mission evidence
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.hermes import worker_registry as WR          # noqa: E402
from backend.hermes import capability_map as CM           # noqa: E402
from backend.hermes import dispatcher as DP               # noqa: E402
from backend.hermes import learning as LN                 # noqa: E402


# ── Worker Registry ───────────────────────────────────────────────────────────
def test_manifests_load_and_have_required_metadata():
    ws = WR.list_workers()
    assert ws, "no worker manifests loaded"
    required = {"capabilities", "context_length", "modality", "cost_class",
                "latency_class", "locality", "availability"}
    for w in ws:
        missing = required - set(w)
        assert not missing, f"{w['id']} missing manifest fields: {missing}"


def test_availability_is_observed_never_asserted():
    """NO FAKE GREEN: availability must come from an observation with evidence."""
    for w in WR.list_workers():
        assert w["availability"] in {"AVAILABLE", "UNREACHABLE", "NOT_CONFIGURED", "UNKNOWN"}
        assert w.get("evidence"), f"{w['id']} claims availability with no evidence"


def test_manifest_file_does_not_assert_availability():
    raw = json.loads((ROOT / "coordination" / "hermes" / "workers.json").read_text())
    for wid, spec in raw["workers"].items():
        assert "availability" not in spec, f"{wid} hard-codes availability (fake green)"


def test_local_discovery_reuses_existing_scanner():
    d = WR.discover_local()
    assert d["source"].endswith("scan_ai_runtimes.py"), "must reuse existing discovery"
    assert "observed_models" in d


# ── Capability Registry / selection ───────────────────────────────────────────
def test_frozen_capability_registry_is_used_not_replaced():
    """HERMES must consult the FROZEN registry for capability→role."""
    from backend.helm_runtime.capability_registry import route_capability
    assert route_capability("verification").get("role") == "auditor"
    sel = CM.select_worker("verification")
    assert sel.get("role") == "auditor", "HERMES ignored the frozen capability→role mapping"


def test_frozen_registry_data_unmodified():
    """The frozen registry JSON must still contain exactly its original three roles."""
    p = ROOT / "coordination" / "governance" / "capability_registry.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert set(data["roles"]) == {"orchestrator", "builder", "auditor"}, \
        "HERMES modified the frozen capability registry — forbidden"


def test_selection_is_explainable():
    sel = CM.select_worker("code_generation")
    assert "reason" in sel and sel["reason"]
    if sel["resolved"]:
        assert sel["worker_id"] in sel["candidates"]


def test_unknown_capability_fails_closed():
    sel = CM.select_worker("teleportation")
    assert sel["resolved"] is False
    assert "no worker advertises" in sel["reason"] or "AVAILABLE" in sel["reason"]


def test_capability_matrix_marks_servable_honestly():
    m = CM.capability_matrix()["capabilities"]
    assert m, "empty capability matrix"
    for cap, e in m.items():
        assert e["servable"] == bool(e["available"]), f"{cap} servable flag not evidence-based"


# ── Dispatcher ────────────────────────────────────────────────────────────────
def test_dispatcher_has_no_vendor_entry_points():
    src = (ROOT / "backend" / "hermes" / "dispatcher.py").read_text(encoding="utf-8")
    for bad in ("dispatch_to_claude", "dispatch_to_openai", "dispatch_to_grok"):
        assert bad not in src, f"vendor entry point {bad} present — must dispatch by capability"


def test_dispatcher_routes_through_the_existing_guarded_gateway():
    src = (ROOT / "backend" / "hermes" / "dispatcher.py").read_text(encoding="utf-8")
    assert "guarded_council import guarded_dispatch" in src, \
        "HERMES must execute via the existing guarded choke point, not its own path"
    for dup in ("class Queue", "Scheduler(", "EventBus("):
        assert dup not in src, f"duplicate runtime primitive {dup} — forbidden"


def test_explain_dispatches_nothing():
    e = DP.explain("verification")
    assert e["dispatched"] is False


def test_dispatch_unknown_capability_returns_blocked_not_fake_success():
    r = DP.dispatch("teleportation", "hello")
    assert r["ok"] is False
    assert r["error"] == "no_worker_for_capability"
    assert "reason" in r


# ── Learning hooks ────────────────────────────────────────────────────────────
def test_learning_records_mission_evidence():
    rec = LN.record_mission(capability="unit_test", worker="ollama_local", ok=True,
                            latency_ms=42, selection_reason="test", fallback_used=False)
    assert rec["schema"] == "HERMES_MISSION_RECORD_v1"
    assert rec["sink"] in {"helm_event_ledger", "fallback_jsonl"}, "evidence was dropped"
    for f in ("worker", "capability", "latency_ms", "ok", "fallback_used"):
        assert f in rec


def test_learning_engine_is_interface_only_by_scope():
    r = LN.recommend_worker("code_generation")
    assert r["status"] == "INTERFACE_ONLY"
    assert r["recommendation"] == "NO_RECOMMENDATION", \
        "learned routing must not be active without an EDR"


def test_worker_stats_reports_no_evidence_honestly():
    s = LN.worker_stats("a_worker_that_never_ran")
    assert s["status"] in {"NO_EVIDENCE_YET", "OBSERVED"}
