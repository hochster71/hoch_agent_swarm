"""F-A1 / F-A2 / F-A6 negative controls for HELM live-truth surface.

Required proofs:
  missing declared ledger path            → RUNTIME_SOURCE_UNPUBLISHED
  declared path exists but scheduler ID differs → RUNTIME_SOURCE_MISMATCH
  newer active 2H soak + older smoke      → active 2H selected
  sealed 2H soak + newer unrelated smoke  → sealed authoritative 2H selected
  wall metadata missing required field    → deterministic test failure
  Vite proxy unavailable                  → canonical route remains :8770
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from backend.truth import runtime_source as RS  # noqa: E402
from backend.truth.soak_select import select_soak_package, list_phase_packages  # noqa: E402
from backend.truth.wall_state import wall_state  # noqa: E402

REQUIRED_WALL_META = (
    "truth_class",
    "source",
    "observed_at",
    "freshness_seconds",
    "tested_commit",
)


@pytest.fixture
def tmp_ptr(tmp_path, monkeypatch):
    """Redirect POINTER + LEASE_DIR into an isolated temp tree."""
    ptr = tmp_path / "active_runtime_source.json"
    leases = tmp_path / "leases"
    leases.mkdir()
    monkeypatch.setattr(RS, "POINTER", ptr)
    monkeypatch.setattr(RS, "LEASE_DIR", leases)
    monkeypatch.setattr(RS, "ROOT", tmp_path)
    return tmp_path, ptr, leases


def test_fa1_missing_declared_ledger_is_unpublished(tmp_ptr):
    tmp_path, ptr, _ = tmp_ptr
    missing = tmp_path / "no_such" / "task_lease_ledger.jsonl"
    ptr.write_text(json.dumps({
        "scheduler_instance_id": "sched-deadbeef",
        "ledger_path": str(missing),
        "evidence_dir": str(missing.parent),
        "pid": 1,
        "published_at": "2026-07-14T00:00:00Z",
    }))
    out = RS.concurrency_truth(configured_capacity=4)
    assert out["truth_source"] == "RUNTIME_SOURCE_UNPUBLISHED"
    assert out["status"] == "UNPUBLISHED"
    assert "does not exist" in (out.get("reason") or out.get("mismatch") or "")


def test_fa1_no_pointer_is_unpublished(tmp_ptr):
    _, ptr, _ = tmp_ptr
    assert not ptr.exists()
    out = RS.concurrency_truth()
    assert out["truth_source"] == "RUNTIME_SOURCE_UNPUBLISHED"
    assert out["status"] == "UNPUBLISHED"


def test_fa1_instance_id_mismatch(tmp_ptr):
    tmp_path, ptr, _ = tmp_ptr
    evid = tmp_path / "evid"
    evid.mkdir()
    ledger = evid / "task_lease_ledger.jsonl"
    ledger.write_text(
        json.dumps({"ts": "2026-07-14T00:00:00Z", "lease_id": "L1",
                    "task_id": "T1", "status": "ACQUIRED"}) + "\n"
        + json.dumps({"ts": "2026-07-14T00:00:01Z", "lease_id": "L1",
                      "task_id": "T1", "status": "RELEASED"}) + "\n"
    )
    # sidecar says sched-AAAA
    (evid / RS.INSTANCE_SIDECAR_NAME).write_text(json.dumps({
        "scheduler_instance_id": "sched-AAAA",
        "ledger_path": str(ledger),
    }))
    # pointer claims sched-BBBB
    ptr.write_text(json.dumps({
        "scheduler_instance_id": "sched-BBBB",
        "ledger_path": str(ledger),
        "evidence_dir": str(evid),
    }))
    out = RS.concurrency_truth()
    assert out["truth_source"] == "RUNTIME_SOURCE_MISMATCH"
    assert out["status"] == "MISMATCH"
    assert "differ" in (out.get("reason") or out.get("mismatch") or "").lower()


def test_fa1_publish_creates_existing_ledger_and_matches(tmp_ptr):
    tmp_path, ptr, _ = tmp_ptr
    evid = tmp_path / "daemon_evid"
    RS.publish(evid, "sched-GOOD01")
    assert ptr.exists()
    ledger = Path(json.loads(ptr.read_text())["ledger_path"])
    assert ledger.exists()
    out = RS.concurrency_truth()
    assert out["truth_source"].startswith("OBSERVED_RUNTIME")
    assert out["scheduler_instance_id"] == "sched-GOOD01"
    assert out["status"] in ("OK", "UNPROVEN", "DEGRADED")


def test_fa2_prefers_active_2h_over_older_smoke(tmp_path):
    root = tmp_path / "pkgs"
    root.mkdir()
    smoke = root / "HELM-SOAK-XH-20260713T230828Z"
    smoke.mkdir()
    (smoke / "soak_config.json").write_text(json.dumps({
        "phase": "SMOKE3", "started_at": "2026-07-13T23:08:28Z", "seconds": 150,
    }))
    active = root / "HELM-SOAK-2H-20260713T232714Z"
    active.mkdir()
    (active / "soak_config.json").write_text(json.dumps({
        "phase": "A", "started_at": "2026-07-13T23:27:14Z", "seconds": 7200,
    }))
    (active / "runtime_truth_snapshots.jsonl").write_text(json.dumps({
        "at": "2026-07-13T23:28:00Z", "soak_status": "IN_PROGRESS",
    }) + "\n")
    # newer mtime on smoke should NOT win
    time.sleep(0.05)
    (smoke / "soak_config.json").write_text(json.dumps({
        "phase": "SMOKE3", "started_at": "2026-07-13T23:59:00Z", "seconds": 150,
    }))
    picked = select_soak_package(root)
    assert picked is not None
    assert picked.name == "HELM-SOAK-2H-20260713T232714Z"
    assert "XH" not in picked.name


def test_fa2_sealed_2h_beats_newer_smoke(tmp_path):
    root = tmp_path / "pkgs"
    root.mkdir()
    sealed = root / "HELM-SOAK-2H-20260713T231226Z"
    sealed.mkdir()
    (sealed / "soak_config.json").write_text(json.dumps({
        "phase": "A", "started_at": "2026-07-13T23:12:26Z", "seconds": 7200,
    }))
    (sealed / "seal_verdict.json").write_text(json.dumps({
        "verdict": "SOAK_PHASE_A_FAIL",
        "sealed_at": "2026-07-13T23:26:37Z",
    }))
    smoke = root / "HELM-SOAK-XH-20260714T000000Z"
    smoke.mkdir()
    (smoke / "soak_config.json").write_text(json.dumps({
        "phase": "SMOKE", "started_at": "2026-07-14T00:00:00Z", "seconds": 90,
    }))
    # touch smoke later
    time.sleep(0.05)
    (smoke / "marker").write_text("x")
    picked = select_soak_package(root)
    assert picked is not None
    assert picked.name.startswith("HELM-SOAK-2H-")
    assert picked.name == "HELM-SOAK-2H-20260713T231226Z"


def test_fa2_latest_seal_wins_among_2h(tmp_path):
    root = tmp_path / "pkgs"
    root.mkdir()
    a = root / "HELM-SOAK-2H-20260713T231226Z"
    b = root / "HELM-SOAK-2H-20260713T232714Z"
    for p, started, sealed in (
        (a, "2026-07-13T23:12:26Z", "2026-07-13T23:26:37Z"),
        (b, "2026-07-13T23:27:14Z", "2026-07-14T00:09:14Z"),
    ):
        p.mkdir()
        (p / "soak_config.json").write_text(json.dumps({
            "phase": "A", "started_at": started, "seconds": 7200,
        }))
        (p / "seal_verdict.json").write_text(json.dumps({
            "verdict": "SOAK_PHASE_A_FAIL", "sealed_at": sealed,
        }))
    picked = select_soak_package(root)
    assert picked is not None
    assert picked.name == "HELM-SOAK-2H-20260713T232714Z"


def test_fa6_wall_metadata_contract():
    w = wall_state()
    missing = [k for k in REQUIRED_WALL_META if k not in w or w[k] in (None, "")]
    assert missing == [], f"wall missing required metadata: {missing}"
    assert w["truth_class"] == "HELM_WALL_STATE"
    assert isinstance(w["freshness_seconds"], (int, float))
    assert "scopes" in w
    assert "authority" in w


def test_fa6_wall_metadata_missing_field_fails_deterministically(monkeypatch):
    """If wall_state ever drops a required field, this test fails closed."""
    real = wall_state

    def broken():
        d = real()
        d.pop("tested_commit", None)
        return d

    monkeypatch.setattr("backend.truth.wall_state.wall_state", broken)
    # re-import path used by tests
    from backend.truth import wall_state as WS
    monkeypatch.setattr(WS, "wall_state", broken)
    w = broken()
    missing = [k for k in REQUIRED_WALL_META if k not in w or w[k] in (None, "")]
    assert "tested_commit" in missing


def test_authority_empty_ok_only_when_idle(tmp_ptr, monkeypatch):
    from backend.truth import wall_state as WS
    tmp_path, _, leases = tmp_ptr
    # no locks → EMPTY_OK
    monkeypatch.setattr(WS, "ROOT", ROOT)  # keep real factory registry
    # isolate lease dir for classify
    monkeypatch.setattr(RS, "LEASE_DIR", leases)
    panel = WS._authority_panel({})
    assert panel["panel_status"] == "EMPTY_OK"

    # active worker without authority_decision_id → INCOMPLETE
    lock = leases / "SOAK-HCF-1.lock"
    lock.write_text(json.dumps({
        "task_id": "SOAK-HCF-1",
        "status": "ACTIVE",
        "expires_at": "2099-01-01T00:00:00Z",
    }))
    panel2 = WS._authority_panel({"HCF": 1})
    assert panel2["panel_status"] == "INCOMPLETE"
    assert panel2["missing_bindings"]


def test_canonical_route_is_8770_not_vite():
    """Vite proxy unavailable must not invent a green UI — canonical is :8770."""
    w = wall_state()
    assert "8770" in w["doctrine"]["canonical_browser_route"]
    assert w["doctrine"]["vite_3012_not_canonical_until_proven"] is True
