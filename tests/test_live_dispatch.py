"""Tests for the live dispatch layer — fail-closed, founder-gated, no secret leak.

The frozen audit target is not imported-for-modification here; live adapters are new
files that subclass the frozen ProviderAdapter. Live network calls are never made in
tests (no flag / no key) — every path must fail closed.
"""
from __future__ import annotations

import pytest

from backend.helm_runtime.dispatch_gateway import DispatchNotEnabledError, DispatchRequest
from backend.dispatch.live_adapters import (
    LiveOpenAIAdapter, LiveAnthropicAdapter, LiveXAIAdapter, LiveLocalAdapter,
    dispatch_globally_enabled,
)
from backend.dispatch.live_gateway import live_gateway, dispatch


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for v in ("HELM_DISPATCH_ENABLED", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
              "XAI_API_KEY", "HELM_LOCAL_MODEL_URL"):
        monkeypatch.delenv(v, raising=False)


def test_disabled_by_default():
    assert dispatch_globally_enabled() is False


def test_invoke_fails_closed_without_flag():
    for cls in (LiveOpenAIAdapter, LiveAnthropicAdapter, LiveXAIAdapter, LiveLocalAdapter):
        with pytest.raises(DispatchNotEnabledError):
            cls().invoke(DispatchRequest(role="auditor", prompt="x"))


def test_flag_set_but_no_key_still_fails_closed(monkeypatch):
    monkeypatch.setenv("HELM_DISPATCH_ENABLED", "1")
    with pytest.raises(DispatchNotEnabledError):
        LiveXAIAdapter().invoke(DispatchRequest(role="auditor", prompt="x"))


def test_health_reports_body_present_but_blocked():
    h = LiveXAIAdapter().health()
    assert h["dispatch_implemented"] is True          # live body exists
    assert h["status"] == "BLOCKED"                    # but gated off
    assert h["configured"] is False


def test_gateway_dispatch_fails_closed():
    with pytest.raises(DispatchNotEnabledError):
        dispatch(role="auditor", capability="verification", prompt="verify")


def test_capability_routes_to_auditor_provider():
    # Even fail-closed, resolution must reach the xai (auditor) adapter, not another.
    from backend.helm_runtime.capability_registry import route_capability
    assert route_capability("verification")["role"] == "auditor"


def test_no_secret_in_health(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "sk-should-never-appear")
    h = LiveXAIAdapter().health()
    assert "sk-should-never-appear" not in str(h)
