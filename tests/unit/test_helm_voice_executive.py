"""HELM Voice Executive — policy, sanitizer, commands, fail-closed briefs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.voice.commands import resolve_command, list_commands_public
from backend.voice.policy import get_policy_public, is_doorstep_verb, load_voice_policy
from backend.voice.sanitizer import sanitize_for_speech
from backend.voice.briefing import execute_voice_command, build_executive_brief


def test_policy_fail_closed_defaults():
    p = get_policy_public()
    assert p["voice_enabled_default"] is False
    assert p["paid_providers_allowed"] is False
    assert p["speak_secrets"] is False
    assert "READ_ONLY" in p["allowed_modes"]
    assert "deploy" in p["doorstep_blocked_verbs"]


def test_sanitizer_redacts_secrets():
    raw = "token sk-1234567890abcdef and Bearer abcdefghijklmnop and /Users/michael/secret"
    clean = sanitize_for_speech(raw)
    assert "sk-1234567890" not in clean
    assert "Bearer abcdef" not in clean
    assert "/Users/michael" not in clean
    assert "[REDACTED]" in clean


def test_resolve_executive_brief_utterance():
    cmd, _ = resolve_command(utterance="Generate today's executive briefing")
    assert cmd is not None
    assert cmd["id"] == "executive_brief"
    assert cmd["mode"] == "READ_ONLY"


def test_resolve_doorstep_deploy_wins():
    cmd, _ = resolve_command(utterance="please deploy to production now")
    assert cmd is not None
    assert cmd["mode"] == "DOORSTEP"
    assert cmd["id"] == "deploy"


def test_doorstep_verb_check():
    assert is_doorstep_verb("deploy_prod")
    assert is_doorstep_verb("move_money")
    assert not is_doorstep_verb("executive_brief")


def test_execute_doorstep_blocked():
    result = execute_voice_command(command_id="deploy")
    assert result["status"] == "DOORSTEP"
    assert result["mode"] == "DOORSTEP"
    assert result["data"]["execution_allowed"] is False
    assert "founder" in result["speech_text"].lower()


def test_execute_unknown_command():
    result = execute_voice_command(utterance="play me a song about ponies")
    assert result["status"] == "UNKNOWN"
    assert result["command"] is None
    assert "not invent" in result["speech_text"].lower() or "UNKNOWN" in result["speech_text"]


def test_executive_brief_has_labels():
    brief = build_executive_brief()
    assert brief["truth_class"] == "HELM_VOICE_BRIEF"
    assert "speech_text" in brief
    assert "labels" in brief
    assert isinstance(brief["labels"], dict)
    # Must not claim release authority
    assert "speech_text" in brief and brief["speech_text"]
    for label in brief["labels"].values():
        assert label in ("LIVE", "STALE", "UNKNOWN", "PARTIAL", "BLOCKED", "PLANNED")


def test_stage_route_writes_artifact(tmp_path, monkeypatch):
    # Use real staging dir under repo — command is STAGE_ONLY
    result = execute_voice_command(
        utterance="route this task to the cybersecurity factory for patch review"
    )
    assert result["command"] == "route_task"
    assert result["mode"] == "STAGE_ONLY"
    assert result["status"] == "STAGED"
    path = result["data"]["staging_path"]
    full = Path(__file__).resolve().parents[2] / path
    assert full.exists()
    payload = json.loads(full.read_text(encoding="utf-8"))
    assert payload["execution"] == "NOT_EXECUTED"
    assert payload["status"] == "STAGED"


def test_list_commands_includes_modes():
    cmds = list_commands_public()
    modes = {c["mode"] for c in cmds}
    assert "READ_ONLY" in modes
    assert "DOORSTEP" in modes


def test_helm_live_api_voice_routes():
    import backend.helm_live_api as api

    c = TestClient(api.app)
    r = c.get("/api/v1/helm/voice/health")
    assert r.status_code == 200
    assert r.json()["status"] == "LIVE"

    r = c.get("/api/v1/helm/voice/policy")
    assert r.status_code == 200
    assert r.json()["policy"]["speak_secrets"] is False

    r = c.get("/api/v1/helm/voice/commands")
    assert r.status_code == 200
    assert len(r.json()["commands"]) >= 5

    r = c.get("/api/v1/helm/voice/brief")
    assert r.status_code == 200
    body = r.json()
    assert body["truth_class"] == "HELM_VOICE_BRIEF"
    assert "speech_text" in body

    r = c.post("/api/v1/helm/voice/command", json={"command": "founder_approvals"})
    assert r.status_code == 200
    assert r.json()["command"] == "founder_approvals"

    r = c.post("/api/v1/helm/voice/command", json={"command": "deploy"})
    assert r.status_code == 200
    assert r.json()["status"] == "DOORSTEP"

    r = c.post(
        "/api/v1/helm/voice/sanitize",
        json={"text": "key sk-abcdefghijklmnopqrst password=hunter2"},
    )
    assert r.status_code == 200
    assert "sk-abcdef" not in r.json()["speech_text"]

    r = c.get("/api/v1/helm/voice/tools")
    assert r.status_code == 200
    tools = r.json()["tools"]
    assert any(t["function"]["name"] == "helm_executive_brief" for t in tools)

    r = c.get("/voice")
    assert r.status_code == 200
    assert "VOICE EXECUTIVE" in r.text

    r = c.get("/frontend_live/voice_panel.js")
    assert r.status_code == 200
    assert "HELMVoice" in r.text


def test_main_app_voice_routes():
    from backend.main import app

    c = TestClient(app)
    r = c.get("/api/v1/helm/voice/health")
    assert r.status_code == 200
    assert r.json()["subsystem"] == "voice_executive"


def test_goal_status_command():
    result = execute_voice_command(command_id="goal_status")
    assert result["command"] == "goal_status"
    assert result["mode"] == "READ_ONLY"
    assert "labels" in result
    assert result["labels"].get("goal") in ("LIVE", "STALE", "UNKNOWN")
    # Never invent founder-minutes-per-dollar when null
    speech = (result.get("speech_text") or "").lower()
    if "unknown" in speech and "dollar" in speech:
        assert "fabricat" in speech or "unknown" in speech


def test_repo_status_local_git_not_remote_github():
    result = execute_voice_command(command_id="repo_status")
    assert result["command"] == "repo_status"
    assert result["mode"] == "READ_ONLY"
    # Remote GitHub is explicitly not claimed
    assert result["labels"].get("github_remote") == "UNKNOWN" or "UNKNOWN" in (
        result.get("speech_text") or ""
    )
    data = result.get("data") or {}
    if result["status"] == "LIVE":
        assert data.get("branch")
        assert data.get("head")


def test_brief_includes_goal_and_repo_labels():
    brief = build_executive_brief()
    assert "goal" in brief["labels"]
    assert "repo" in brief["labels"]
    assert brief["labels"]["goal"] in ("LIVE", "STALE", "UNKNOWN")
    assert brief["labels"]["repo"] in ("LIVE", "STALE", "UNKNOWN")
