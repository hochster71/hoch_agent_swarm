"""Tests for HELM Executive Mission role ownership + loader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.mission_control.executive_mission import (
    assert_role_may_write,
    load_executive_mission,
    load_ownership,
    mission_summary,
    normalize_role,
    record_write,
)


def test_executive_mission_file_exists_and_schema():
    doc = load_executive_mission()
    assert doc.get("schema") in ("HELM_EXECUTIVE_MISSION_v1", "HELM_EXECUTIVE_MISSION_v2")
    roles = doc.get("roles") or {}
    assert "orchestrator" in roles
    assert "builder" in roles
    assert "auditor" in roles
    assert "authoritative_truth" not in roles  # truth is not a role
    assert (doc.get("platform") or {}).get("is_actor") is False


def test_role_aliases():
    assert normalize_role("ChatGPT Agent") == "orchestrator"
    assert normalize_role("Claude") == "builder"
    assert normalize_role("Grok") == "auditor"


def test_ownership_orchestrator_may_route_not_verdict():
    assert assert_role_may_write("orchestrator", "mission.routing") is True
    assert assert_role_may_write("orchestrator", "mission.task_queue") is True
    # auditor verdict is not orchestrator-owned
    assert assert_role_may_write("orchestrator", "mission.auditor_verdict") is False


def test_ownership_builder_and_auditor_split():
    assert assert_role_may_write("builder", "mission.engineering_status") is True
    assert assert_role_may_write("builder", "mission.auditor_verdict") is False
    assert assert_role_may_write("auditor", "mission.auditor_verdict") is True
    assert assert_role_may_write("auditor", "mission.routing") is False


def test_record_write_enforces_ownership(tmp_path):
    src = Path("coordination/goal/executive_mission.json")
    doc = json.loads(src.read_text())
    p = tmp_path / "executive_mission.json"
    p.write_text(json.dumps(doc, indent=2))
    with pytest.raises(PermissionError):
        record_write("builder", ["mission.auditor_verdict"], path=p, note="should fail")
    entry = record_write(
        "auditor",
        ["mission.assurance_status"],
        path=p,
        actor="Grok",
        correlation_id="TEST-OWNERSHIP",
        note="allowed",
        recompute_truth=False,
    )
    assert entry.get("ok") is True
    reloaded = json.loads(p.read_text())
    assert reloaded["last_writes"][-1]["correlation_id"] == "TEST-OWNERSHIP"


def test_mission_summary_shape():
    s = mission_summary()
    assert s.get("mission_id")
    assert "roles" in s
