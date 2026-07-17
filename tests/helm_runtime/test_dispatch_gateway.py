"""Tests for EDR-0002 Dispatch Gateway skeleton — fail-closed, honest health.

Proves: no fake dispatch, adapters blocked without credentials, capability
routing resolves to a role, mission_health reports the honest projection.
"""
from __future__ import annotations

import pytest

from backend.helm_runtime import capability_registry as capreg
from backend.helm_runtime.dispatch_gateway import (
    DispatchGateway,
    DispatchNotEnabledError,
    DispatchRequest,
    AnthropicAdapter,
    LocalAdapter,
)


@pytest.fixture()
def gateway(monkeypatch):
    # Ensure no provider creds leak in from the host env for a deterministic test.
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY", "HELM_LOCAL_MODEL_URL"):
        monkeypatch.delenv(var, raising=False)
    return DispatchGateway()


# ---- Honest health / no fake green -------------------------------------------

def test_all_providers_blocked_without_credentials(gateway):
    ws = gateway.worker_status()
    assert ws["configured"] == 0
    assert ws["available"] == []
    assert set(ws["blocked"]) == {"openai", "anthropic", "xai", "local"}


def test_invoke_fails_closed_no_fake_success(gateway):
    with pytest.raises(DispatchNotEnabledError):
        gateway.dispatch(DispatchRequest(role="builder", prompt="build X"))


def test_adapter_invoke_directly_fails_closed():
    with pytest.raises(DispatchNotEnabledError):
        AnthropicAdapter().invoke(DispatchRequest(role="builder"))


def test_health_reports_dispatch_not_implemented(gateway):
    for h in gateway.health():
        assert h["status"] == "BLOCKED"
        assert h["dispatch_implemented"] is False


# ---- Credential presence flips status (still no dispatch body) ----------------

def test_credential_presence_flips_status_only(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "present-not-read")
    a = AnthropicAdapter()
    assert a.credential_present() is True
    assert a.health()["status"] == "READY"
    # But dispatch body still absent -> invoke must still fail closed.
    with pytest.raises(DispatchNotEnabledError):
        a.invoke(DispatchRequest(role="builder"))


def test_local_adapter_needs_endpoint(monkeypatch):
    monkeypatch.delenv("HELM_LOCAL_MODEL_URL", raising=False)
    assert LocalAdapter().credential_present() is False
    monkeypatch.setenv("HELM_LOCAL_MODEL_URL", "http://localhost:1234")
    assert LocalAdapter().credential_present() is True


# ---- Capability routing (brand-agnostic) -------------------------------------

def test_capability_routes_to_role():
    assert capreg.route_capability("python")["role"] == "builder"
    assert capreg.route_capability("red_team")["role"] == "auditor"
    assert capreg.route_capability("planning")["role"] == "orchestrator"


def test_unknown_capability_unresolved():
    r = capreg.route_capability("time_travel")
    assert r["resolved"] is False


def test_dispatch_by_capability_resolves_then_fails_closed(gateway):
    # Resolves python -> builder -> anthropic adapter, then fails closed (no creds).
    with pytest.raises(DispatchNotEnabledError):
        gateway.dispatch(DispatchRequest(role="", capability="python", prompt="x"))


# ---- Mission Health projection -----------------------------------------------

def test_mission_health_shape(gateway):
    h = gateway.mission_health()
    assert h["engine"] == "dispatch_gateway"
    assert h["is_actor"] is False
    assert h["runtime"]["dispatch"] == "READY"
    assert h["runtime"]["governance"] == "ENFORCED"
    assert h["workers"]["configured"] == 0
    assert h["founder_gate"] == "PENDING"
    assert h["reason"] == "Provider credentials unavailable"


def test_worker_role_health_distinguishes_roles(gateway):
    rows = gateway.worker_role_health()
    roles = {r["role"] for r in rows}
    assert roles == {"orchestrator", "builder", "auditor"}
    for r in rows:
        assert "configured" in r and "reachable" in r and "dispatch_enabled" in r
        assert "binding" in r
        assert r["dispatch_enabled"] is False
        assert r["status"] == "BLOCKED"
