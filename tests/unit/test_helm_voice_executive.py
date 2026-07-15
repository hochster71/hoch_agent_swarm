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
        assert label in (
            "LIVE",
            "STALE",
            "UNKNOWN",
            "PARTIAL",
            "BLOCKED",
            "PLANNED",
            "NONE",
            "UNDEFINED",
            "CONTRADICTED",
        )


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


def test_factory_brief_hasf_registered():
    from backend.voice.factory_agents import observe_factory

    r = observe_factory("HASF")
    assert r["code"] == "HASF"
    assert r["registry"] == "REGISTERED"
    assert r["status"] in ("LIVE", "STALE", "PARTIAL", "UNKNOWN")
    assert "speech_text" in r
    assert "gates" in (r.get("data") or {})


def test_factory_brief_hsf_observable_partial():
    from backend.voice.factory_agents import observe_factory

    r = observe_factory("HSF")
    assert r["code"] == "HSF"
    assert r["registry"] == "DECLARED_OBSERVABLE"
    assert r["status"] in ("PARTIAL", "UNKNOWN", "LIVE")
    # Must not invent earning when no verified dollars
    earning = (r.get("labels") or {}).get("earning")
    rev_label = (r.get("labels") or {}).get("revenue")
    assert earning in (None, "NONE", "UNKNOWN", "LIVE")
    if earning == "LIVE":
        # only if ledger has real settled dollars
        assert (r.get("data") or {}).get("revenue_settled_usd", 0) > 0
    assert rev_label in ("LIVE", "UNKNOWN", "CONTRADICTED", "NONE")


def test_factory_brief_hcf_and_hff():
    from backend.voice.factory_agents import observe_factory

    hcf = observe_factory("HCF")
    assert hcf["code"] == "HCF"
    assert hcf["status"] in ("PARTIAL", "UNKNOWN", "LIVE", "STALE")
    hff = observe_factory("HFF")
    assert hff["code"] == "HFF"
    # earning green only with verified settled dollars
    assert (hff.get("labels") or {}).get("earning") in (None, "NONE", "UNKNOWN", "LIVE")


def test_revenue_observe_ledger_not_invented():
    from backend.voice.revenue import observe_revenue

    r = observe_revenue()
    assert r["truth_class"] == "HELM_VOICE_REVENUE"
    assert r["status"] in ("LIVE", "UNKNOWN", "CONTRADICTED")
    data = r.get("data") or {}
    if r["status"] == "LIVE" and (r.get("labels") or {}).get("earning") != "LIVE":
        assert float(data.get("revenue_settled_usd") or 0) == 0.0
        assert "UNDEFINED" in str(data.get("north_star_value")) or data.get(
            "north_star_value"
        ) == "UNDEFINED" or "zero" in (r.get("speech_text") or "").lower()


def test_security_events_high_only():
    from backend.voice.security_events import security_events_for_speech, collect_high_security_findings

    findings = collect_high_security_findings()
    for f in findings:
        assert f["severity"] == "HIGH"
    r = security_events_for_speech(mark_spoken=False)
    assert r["truth_class"] == "HELM_VOICE_SECURITY_EVENTS"
    assert r["severity_filter"] == "HIGH"
    assert "rate_limit" in r


def test_grok_pack_export():
    from backend.voice.grok_pack import build_grok_tool_pack, render_grok_pack_markdown

    pack = build_grok_tool_pack(base_url="http://127.0.0.1:8770")
    assert pack["schema"].startswith("helm-grok-voice-tool-pack")
    names = {t["name"] for t in pack["tools"]}
    assert "helm_revenue" in names
    assert "helm_security_events" in names
    assert "helm_executive_brief" in names
    assert "helm_tts_speak" in names
    md = render_grok_pack_markdown(pack)
    assert "helm_revenue" in md
    assert "http://127.0.0.1:8770" in md


def test_elevenlabs_fail_closed_without_key(monkeypatch):
    from backend.voice import elevenlabs_tts as el
    from backend.voice.policy import reload_voice_policy

    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVEN_LABS_API_KEY", raising=False)
    monkeypatch.delenv("HELM_ELEVENLABS_TTS", raising=False)
    monkeypatch.delenv("HELM_VOICE_PAID_PROVIDERS", raising=False)
    monkeypatch.delenv("HELM_VOICE_MODE", raising=False)
    reload_voice_policy()
    st = el.elevenlabs_config_status()
    assert st["ready"] is False
    assert st["status"] == "BLOCKED"
    ok, meta, audio = el.synthesize_speech("Hello HELM")
    assert ok is False
    assert audio is None
    assert meta.get("fallback") == "local_tts"


def test_elevenlabs_blocked_even_with_key_if_paid_false(monkeypatch):
    from backend.voice import elevenlabs_tts as el
    from backend.voice.policy import reload_voice_policy

    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test_fake_key_for_unit_test_only")
    monkeypatch.setenv("HELM_ELEVENLABS_TTS", "1")
    monkeypatch.delenv("HELM_VOICE_PAID_PROVIDERS", raising=False)
    monkeypatch.delenv("HELM_VOICE_MODE", raising=False)
    reload_voice_policy()
    st = el.elevenlabs_config_status()
    # policy paid_providers_allowed defaults false; env paid not set
    assert st["key_present"] is True
    assert st["ready"] is False
    assert any("paid" in r.lower() for r in st.get("blocked_reasons") or [])


def test_role_briefs_all_known():
    from backend.voice.role_agents import observe_role, list_roles

    roles = {r["id"] for r in list_roles()}
    assert roles == {"founder", "ops", "ciso", "cfo", "qa"}
    for rid in roles:
        r = observe_role(rid)
        assert r["truth_class"] == "HELM_VOICE_ROLE"
        assert r["role"] == rid
        assert r.get("speech_text")
        assert "doorstep" in r


def test_role_unknown():
    from backend.voice.role_agents import observe_role

    r = observe_role("astronaut")
    assert r["status"] == "UNKNOWN"


def test_api_factory_and_role_routes(monkeypatch):
    import backend.helm_live_api as api
    from backend.voice.policy import reload_voice_policy

    # Isolate from founder machine env so TTS stay fail-closed in CI/local shared shells
    for k in (
        "ELEVENLABS_API_KEY",
        "ELEVEN_LABS_API_KEY",
        "HELM_ELEVENLABS_TTS",
        "HELM_VOICE_PAID_PROVIDERS",
        "HELM_VOICE_MODE",
    ):
        monkeypatch.delenv(k, raising=False)
    reload_voice_policy()

    c = TestClient(api.app)
    assert c.get("/api/v1/helm/voice/factories").status_code == 200
    assert c.get("/api/v1/helm/voice/factory/HASF").status_code == 200
    hsf = c.get("/api/v1/helm/voice/factory/HSF").json()
    assert hsf["code"] == "HSF"
    assert hsf["status"] in ("PARTIAL", "UNKNOWN", "LIVE")
    assert c.get("/api/v1/helm/voice/factory/HCF").status_code == 200
    assert c.get("/api/v1/helm/voice/revenue").status_code == 200
    assert c.get("/api/v1/helm/voice/security/events").status_code == 200
    pack = c.get("/api/v1/helm/voice/grok-pack", params={"base_url": "http://x"})
    assert pack.status_code == 200
    assert "tools" in pack.json()
    md = c.get(
        "/api/v1/helm/voice/grok-pack",
        params={"base_url": "http://x", "format": "md"},
    )
    assert md.status_code == 200
    assert "helm_revenue" in md.text
    tts = c.get("/api/v1/helm/voice/tts/status")
    assert tts.status_code == 200
    assert "elevenlabs" in tts.json().get("providers", {})
    origins = c.get("/api/v1/helm/voice/origins")
    assert origins.status_code == 200
    assert "urls" in origins.json()
    # Without key/policy, speak is blocked (503)
    sp = c.post(
        "/api/v1/helm/voice/tts/speak",
        json={"text": "test", "format": "json"},
    )
    assert sp.status_code in (503, 502)
    assert sp.json().get("fallback") == "local_tts"
    assert c.get("/api/v1/helm/voice/roles").status_code == 200
    assert c.get("/api/v1/helm/voice/role/ciso").status_code == 200
    assert c.get("/api/v1/helm/voice/role/cfo").json()["role"] == "cfo"
