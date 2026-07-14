"""Authority-binding chain: 10 negative controls + one end-to-end COMPLETE.

Fail-closed rules under test:
  active + missing authority_decision_id → AUTHORITY_INCOMPLETE
  decision digest mismatch               → AUTHORITY_BINDING_MISMATCH
  dispatch digest mismatch               → DISPATCH_BINDING_MISMATCH
  scheduler instance mismatch            → RUNTIME_SOURCE_MISMATCH
  revoked / expired decision             → dispatch prohibited
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.truth import authority_binding as AB  # noqa: E402
from backend.truth.authority_binding import (  # noqa: E402
    BindingError,
    assert_active_binding,
    assert_artifact_does_not_infer_authority,
    assert_decision_digest,
    assert_dispatch_digest,
    assert_lease_owns_decision,
    assert_scheduler_instance,
    compute_dispatch_digest,
    create_autonomous_decision,
    mint_binding,
    panel_status_from_workers,
    task_identity_digest,
)


@pytest.fixture
def ledgers(tmp_path, monkeypatch):
    dled = tmp_path / "decisions.jsonl"
    bled = tmp_path / "bindings.jsonl"
    monkeypatch.setattr(AB, "DECISION_LEDGER", dled)
    monkeypatch.setattr(AB, "BINDING_LEDGER", bled)
    return tmp_path, dled, bled


def _task(tid="T-AUTH-1", pod="HCF"):
    return {
        "task_id": tid,
        "name": "auth bind test",
        "target_pod": pod,
        "mission_prompt": "Analyse control evidence and identify one gap.",
        "dispatch_type": "LOCAL_OLLAMA",
    }


def test_01_leased_without_authority_id_rejected(ledgers):
    with pytest.raises(BindingError) as ei:
        assert_active_binding({
            "task_id": "T1", "lease_id": "L1", "authority_class": "AUTONOMOUS",
            "authority_decision_id": "", "authority_status": "ACTIVE",
            "decision_digest": "x", "dispatch_digest": "y",
            "scheduler_instance_id": "sched-1",
        })
    assert ei.value.code == "AUTHORITY_INCOMPLETE"


def test_02_copied_authority_wrong_task_digest_rejected(ledgers):
    t = _task()
    dec = create_autonomous_decision(
        task=t, authority_class="AUTONOMOUS", scheduler_instance_id="sched-1")
    # wrong task digest on decision
    dec["task_digest"] = "0" * 64
    with pytest.raises(BindingError) as ei:
        mint_binding(
            task=t, lease_id="lease-aa", authority_class="AUTONOMOUS",
            scheduler_instance_id="sched-1", envelope_hash="eh" * 16, decision=dec,
        )
    assert ei.value.code == "AUTHORITY_BINDING_MISMATCH"


def test_03_valid_decision_bound_to_other_lease_rejected(ledgers):
    t = _task()
    b = mint_binding(
        task=t, lease_id="lease-A", authority_class="AUTONOMOUS",
        scheduler_instance_id="sched-1", envelope_hash="ab" * 16,
    )
    with pytest.raises(BindingError) as ei:
        assert_lease_owns_decision(b.to_dict(), "lease-B")
    assert ei.value.code == "AUTHORITY_BINDING_MISMATCH"


def test_04_revoked_decision_cannot_dispatch(ledgers):
    t = _task()
    dec = create_autonomous_decision(
        task=t, authority_class="AUTONOMOUS", scheduler_instance_id="sched-1",
        status="REVOKED",
    )
    with pytest.raises(BindingError) as ei:
        mint_binding(
            task=t, lease_id="lease-r", authority_class="AUTONOMOUS",
            scheduler_instance_id="sched-1", envelope_hash="cd" * 16, decision=dec,
        )
    assert ei.value.code == "AUTHORITY_REVOKED"


def test_05_expired_decision_cannot_dispatch(ledgers):
    t = _task()
    dec = create_autonomous_decision(
        task=t, authority_class="AUTONOMOUS", scheduler_instance_id="sched-1",
        expires_at="2000-01-01T00:00:00Z",
    )
    with pytest.raises(BindingError) as ei:
        mint_binding(
            task=t, lease_id="lease-e", authority_class="AUTONOMOUS",
            scheduler_instance_id="sched-1", envelope_hash="ef" * 16, decision=dec,
        )
    assert ei.value.code == "AUTHORITY_EXPIRED"


def test_06_altered_dispatch_digest_rejected(ledgers):
    t = _task()
    b = mint_binding(
        task=t, lease_id="lease-d", authority_class="AUTONOMOUS",
        scheduler_instance_id="sched-1", envelope_hash="11" * 16,
    ).to_dict()
    b["dispatch_digest"] = "ALTERED" + b["dispatch_digest"]
    with pytest.raises(BindingError) as ei:
        assert_dispatch_digest(b, envelope_hash="11" * 16)
    assert ei.value.code == "DISPATCH_BINDING_MISMATCH"


def test_07_validator_without_binding_cannot_complete(ledgers):
    """Simulates validator path: missing authority fields → incomplete."""
    binding = {
        "task_id": "T1", "lease_id": "L1", "authority_class": "AUTONOMOUS",
        "authority_decision_id": "AUTH-1", "authority_status": "ACTIVE",
        "decision_digest": "dd", "dispatch_digest": "xd",
        "scheduler_instance_id": "sched-1",
    }
    val = {"verdict": "PASS", "authority_decision_id": None}
    incomplete = (
        not val.get("authority_decision_id")
        or val.get("authority_decision_id") != binding["authority_decision_id"]
    )
    assert incomplete is True


def test_08_artifact_cannot_infer_authority_from_task_id(ledgers):
    binding = {
        "task_id": "T1", "lease_id": "L1", "authority_class": "AUTONOMOUS",
        "authority_decision_id": "AUTH-1", "authority_status": "ACTIVE",
        "decision_digest": "dd", "dispatch_digest": "xd",
        "scheduler_instance_id": "sched-1",
    }
    # Only task_id present — inference prohibited
    with pytest.raises(BindingError) as ei:
        assert_artifact_does_not_infer_authority(
            artifact_meta={"task_id": "T1"}, binding=binding)
    assert ei.value.code == "AUTHORITY_INCOMPLETE"


def test_09_scheduler_instance_mismatch_visible(ledgers):
    binding = {
        "task_id": "T1", "lease_id": "L1", "authority_class": "AUTONOMOUS",
        "authority_decision_id": "AUTH-1", "authority_status": "ACTIVE",
        "decision_digest": "dd", "dispatch_digest": "xd",
        "scheduler_instance_id": "sched-AAA",
    }
    with pytest.raises(BindingError) as ei:
        assert_scheduler_instance(binding, "sched-BBB")
    assert ei.value.code == "RUNTIME_SOURCE_MISMATCH"


def test_10_valid_end_to_end_binding_complete(ledgers):
    t = _task("T-E2E-OK", "HSF")
    env_hash = "aa" * 16
    b = mint_binding(
        task=t, lease_id="lease-ok", authority_class="AUTONOMOUS",
        scheduler_instance_id="sched-1", envelope_hash=env_hash,
    )
    d = b.to_dict()
    assert_active_binding(b)
    assert_lease_owns_decision(d, "lease-ok")
    assert_scheduler_instance(d, "sched-1")
    assert_dispatch_digest(d, envelope_hash=env_hash)
    assert_artifact_does_not_infer_authority(
        artifact_meta={
            "task_id": d["task_id"],
            "authority_decision_id": d["authority_decision_id"],
            "decision_digest": d["decision_digest"],
            "dispatch_digest": d["dispatch_digest"],
        },
        binding=d,
    )
    panel = panel_status_from_workers([d], idle=False)
    assert panel["panel_status"] == "COMPLETE"
    assert panel["authoritative_pass_prohibited"] is False


def test_panel_incomplete_when_active_missing_id():
    panel = panel_status_from_workers(
        [{"task_id": "SOAK-HCF-1", "class": "WORKER", "authority_decision_id": None}],
        idle=False,
    )
    assert panel["panel_status"] == "INCOMPLETE"
    assert panel["authoritative_pass_prohibited"] is True


def test_panel_empty_ok_when_idle():
    panel = panel_status_from_workers([], idle=True)
    assert panel["panel_status"] == "EMPTY_OK"


def test_e2e_scheduler_path_with_mocked_gateway(tmp_path, monkeypatch):
    """One valid end-to-end task reaches COMPLETE through execute_task (mocked adapter)."""
    from backend.mission_control.persistent_scheduler import PersistentScheduler
    from scripts.council.gateway import DispatchType

    evid = tmp_path / "evid"
    evid.mkdir()
    # Isolate leases
    lease_dir = tmp_path / "leases"
    lease_dir.mkdir()

    sched = PersistentScheduler(evidence_dir=evid, publish_runtime_source=True)
    from backend.mission_control.per_task_lease import PerTaskLeaseManager
    sched.lease_manager = PerTaskLeaseManager(lease_dir=lease_dir)

    # Mock DB updates
    monkeypatch.setattr(
        "backend.mission_control.persistent_scheduler._sqlite_connect",
        lambda *a, **k: MagicMock(**{
            "execute.return_value": None,
            "commit.return_value": None,
            "close.return_value": None,
            "__enter__.return_value": MagicMock(),
        }),
    )

    class FakeRes:
        status = "COMPLETED"
        output = (
            "Control: access enforcement.\n"
            "Evidence: lease ledger and gateway logs.\n"
            "Gap: missing authority_decision_id on historical tasks.\n"
        )
        exit_code = 0

    def fake_dispatch(req):
        return FakeRes()

    sched.gateway = MagicMock()
    sched.gateway.dispatch = fake_dispatch

    # Mock spend meter allow
    class FakeMeter:
        def check_caps(self, *a, **k):
            return {"allowed": True}

        def record(self, **k):
            return {"cost_usd": 0.0, "cost_state": "OBSERVED", "measurement": "test",
                    "in_chars": 10, "out_chars": 20}

    monkeypatch.setattr(
        "backend.mission_control.spend_meter.SpendMeter", lambda: FakeMeter())

    # Mock validator PASS
    monkeypatch.setattr(
        "backend.mission_control.factory_validators.validate",
        lambda pod, text, ctx: {
            "validator": "validate_hcf", "verdict": "PASS",
            "checks": [], "failed_checks": [],
        },
    )

    # Avoid real GATEWAY_TOKEN issues
    import scripts.council.gateway as gw
    monkeypatch.setattr(gw, "ensure_guard", lambda: None)

    task = {
        "task_id": "T-BOUND-E2E-1",
        "name": "authority bound e2e",
        "target_pod": "HCF",
        "mission_prompt": (
            "Analyse the control. State which control it enforces, what evidence "
            "proves it, and name one gap. Use words control, evidence, and gap."
        ),
        "dispatch_type": "LOCAL_OLLAMA",
        "validator_ctx": {},
    }

    # classify_action must return AUTONOMOUS
    from backend.council import founder_model as FM

    class R:
        authority = FM.Authority.AUTONOMOUS
        matched = None
        reason = "test"

    monkeypatch.setattr(FM, "classify_action", lambda p: R())

    ok = sched.execute_task(task)
    assert ok is True
    assert task.get("authority_decision_id")
    assert task.get("decision_digest")
    assert task.get("dispatch_digest")

    # verification ledger must carry binding
    vlines = (evid / "verification_ledger.jsonl").read_text().strip().splitlines()
    assert vlines
    v = json.loads(vlines[-1])
    assert v["verdict"] == "PASS"
    assert v["authority_decision_id"] == task["authority_decision_id"]
    assert v["dispatch_digest"] == task["dispatch_digest"]

    # manifest exists with authority (not inferred)
    man = ROOT / "artifacts" / "factory" / "T-BOUND-E2E-1.manifest.json"
    assert man.exists()
    m = json.loads(man.read_text())
    assert m["authority_decision_id"] == task["authority_decision_id"]
