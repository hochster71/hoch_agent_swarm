"""DOORSTEP posture regression tests.

Verifies the founder directive: under execution_posture=DOORSTEP, all HAS/factory
automation runs to the pre-purchase door — prep tasks execute, door-crossing tasks
(payment/publish/keys/outreach/investor) are STAGED for the founder instead of being
silently dropped, and genuinely unsafe tasks (destructive) remain hard-blocked and are
NOT staged. No money/credential/publish gate is ever crossed by staging.
"""
import json
import pytest
from pathlib import Path

import scripts.ag_execution_lease_manager as lm_module
import scripts.ag_execution_runner as runner_module
import scripts.ag_operator_hold as hold_module


@pytest.fixture
def doorstep_env(tmp_path, monkeypatch):
    p = {n: tmp_path / f"{n}.json" for n in [
        "queue", "control", "log", "state", "hold", "retry", "policy",
        "proof_index", "handoff", "leases", "lock",
    ]}
    failures = tmp_path / "failures.jsonl"

    monkeypatch.setattr(runner_module, "QUEUE_FILE", p["queue"])
    monkeypatch.setattr(runner_module, "CONTROL_FILE", p["control"])
    monkeypatch.setattr(runner_module, "LOG_FILE", p["log"])
    monkeypatch.setattr(runner_module, "STATE_FILE", p["state"])
    monkeypatch.setattr(runner_module, "HOLD_FILE", p["hold"])
    monkeypatch.setattr(runner_module, "RETRY_POLICY_FILE", p["retry"])
    monkeypatch.setattr(runner_module, "POLICY_FILE", p["policy"])
    monkeypatch.setattr(runner_module, "FAILURES_FILE", failures)
    monkeypatch.setattr(runner_module, "PROOF_INDEX_FILE", p["proof_index"])
    monkeypatch.setattr(runner_module, "HANDOFF_QUEUE_FILE", p["handoff"])
    monkeypatch.setattr(runner_module, "ROOT", tmp_path)
    monkeypatch.setattr(lm_module, "LEASES_FILE", p["leases"])
    monkeypatch.setattr(lm_module, "LOCK_FILE", p["lock"])
    monkeypatch.setattr(hold_module, "HOLD_FILE", p["hold"])

    door_categories = [
        "blocked_release", "blocked_monetization", "blocked_secret_handling",
        "blocked_external_outreach", "blocked_investor_engagement",
    ]
    p["control"].write_text(json.dumps({
        "allow_ag_execution": True,
        "allow_provider_api_calls": False,
        "allow_founder_gated_execution": False,
        "execution_posture": "DOORSTEP",
        "doorstep_policy": {
            "door": "PRE_PURCHASE",
            "door_categories": door_categories,
            "hard_block_categories": ["blocked_destructive_action"],
            "exit_condition": "FOUNDER_ACTIVATES_REVENUE",
        },
    }))
    p["hold"].write_text(json.dumps({"operator_hold_active": False}))
    p["retry"].write_text(json.dumps({"max_retries": 3, "non_retryable_categories": []}))
    p["policy"].write_text(json.dumps({
        "policy_categories": {
            "allowed_internal_task": {"action_prefixes": ["read_", "analyze_"], "risk_tier_max": "R2"},
            "blocked_monetization": {"keywords": ["stripe", "billing", "pricing"], "risk_tier_max": "R4"},
            "blocked_release": {"keywords": ["publish", "deploy_prod"], "risk_tier_max": "R4"},
            "blocked_destructive_action": {"keywords": ["delete", "drop", "rm -rf"], "risk_tier_max": "R4"},
        },
        "doorstep_door_categories": door_categories,
        "doorstep_hard_block_categories": ["blocked_destructive_action"],
    }))
    return p


def _run(queue_file, tasks):
    queue_file.write_text(json.dumps(tasks))
    runner_module.run_executor()
    return {t["task_id"]: t for t in json.loads(queue_file.read_text())}


def _task(tid, name):
    return {"task_id": tid, "task_name": name, "task_class": "factory",
            "status": "PENDING", "allowed_agent": "hasf_builder_agent", "attempts": 0}


def test_prep_task_executes(doorstep_env):
    q = _run(doorstep_env["queue"], [_task("t-prep", "analyze_market_data")])
    assert q["t-prep"]["status"] == "completed"
    # prep work must NOT be parked at the door (handoff file need not even exist)
    hq = json.loads(doorstep_env["handoff"].read_text()) if doorstep_env["handoff"].exists() else {"staged": []}
    assert all(s["task_id"] != "t-prep" for s in hq.get("staged", []))


def test_door_task_is_staged_not_dropped(doorstep_env):
    q = _run(doorstep_env["queue"], [_task("t-pay", "setup_stripe_billing")])
    assert q["t-pay"]["status"] == "STAGED_FOR_FOUNDER"
    hq = json.loads(doorstep_env["handoff"].read_text())
    parked = {s["task_id"]: s for s in hq["staged"]}
    assert "t-pay" in parked
    assert parked["t-pay"]["status"] == "READY_FOR_FOUNDER"
    assert parked["t-pay"]["policy_category"] == "blocked_monetization"
    assert parked["t-pay"]["exit_condition"] == "FOUNDER_ACTIVATES_REVENUE"


def test_publish_task_is_staged(doorstep_env):
    q = _run(doorstep_env["queue"], [_task("t-pub", "publish_ios_build")])
    assert q["t-pub"]["status"] == "STAGED_FOR_FOUNDER"
    hq = json.loads(doorstep_env["handoff"].read_text())
    assert any(s["task_id"] == "t-pub" for s in hq["staged"])


def test_destructive_task_hard_blocked_not_staged(doorstep_env):
    q = _run(doorstep_env["queue"], [_task("t-del", "delete_production_db")])
    assert q["t-del"]["status"] == "BLOCKED"
    hq = json.loads(doorstep_env["handoff"].read_text()) if doorstep_env["handoff"].exists() else {"staged": []}
    assert all(s["task_id"] != "t-del" for s in hq.get("staged", []))


def test_staging_is_idempotent(doorstep_env):
    _run(doorstep_env["queue"], [_task("t-pay", "setup_stripe_billing")])
    # second cycle with the same still-pending task id must not duplicate
    runner_module.stage_for_founder({"task_id": "t-pay", "task_name": "setup_stripe_billing"},
                                    "blocked_monetization", "retry")
    hq = json.loads(doorstep_env["handoff"].read_text())
    assert len([s for s in hq["staged"] if s["task_id"] == "t-pay"]) == 1
