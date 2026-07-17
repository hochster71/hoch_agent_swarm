"""Security remediation tests for the HELM LIVE control-plane API.

Covers the mission-assurance audit findings (R-AUTH, R-CORS) and the flagged,
default-OFF hardening in backend/security/api_hardening.py.

Contract under test
-------------------
* Flag OFF (default): nothing is required. A sensitive route returns 200 exactly
  as it does today — the running server and the founder's dashboards do not break.
* HELM_REQUIRE_AUTH=1: a sensitive route returns 401 WITHOUT a bearer token and
  200 WITH the correct HELM_API_TOKEN. Health (/api/helm/live) stays open.
* CORS allowlist: a disallowed Origin is NOT reflected in
  Access-Control-Allow-Origin; an allowlisted Origin IS. Never "*".
* Security headers are present on responses regardless of flag state.

Run:
    python -m pytest tests/test_helm_live_api_security.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.helm_live_api import app  # noqa: E402  (path set above)
from backend.security import api_hardening  # noqa: E402

# A sensitive endpoint that is fail-soft (returns 200 by design even if a data
# source is missing) so the "flag off -> 200" contract is deterministic.
SENSITIVE = "/api/v1/helm/pert"
HEALTH = "/api/helm/live"
TOKEN = "test-secret-token-do-not-ship"

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Every test starts from the default (all flags OFF) posture."""
    for k in ("HELM_REQUIRE_AUTH", "HELM_API_TOKEN",
              "HELM_RATE_LIMIT_ENABLED", "HELM_RATE_LIMIT_RPM",
              "HELM_MAX_BODY_BYTES"):
        monkeypatch.delenv(k, raising=False)
    yield


# --------------------------------------------------------------- auth: flag OFF
def test_flag_off_sensitive_route_is_open():
    """Default posture: no auth required, sensitive route returns 200."""
    r = client.get(SENSITIVE)
    assert r.status_code == 200, r.text


def test_flag_off_no_401_anywhere():
    assert client.get(HEALTH).status_code == 200


# ---------------------------------------------------------------- auth: flag ON
def test_flag_on_sensitive_route_401_without_token(monkeypatch):
    monkeypatch.setenv("HELM_REQUIRE_AUTH", "1")
    monkeypatch.setenv("HELM_API_TOKEN", TOKEN)
    r = client.get(SENSITIVE)
    assert r.status_code == 401, r.text
    body = r.json()
    assert body.get("state") == "UNAUTHORIZED"
    # No internal detail leaked.
    assert "Traceback" not in r.text and "Exception" not in r.text


def test_flag_on_sensitive_route_200_with_token(monkeypatch):
    monkeypatch.setenv("HELM_REQUIRE_AUTH", "1")
    monkeypatch.setenv("HELM_API_TOKEN", TOKEN)
    r = client.get(SENSITIVE, headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200, r.text


def test_flag_on_wrong_token_is_401(monkeypatch):
    monkeypatch.setenv("HELM_REQUIRE_AUTH", "1")
    monkeypatch.setenv("HELM_API_TOKEN", TOKEN)
    r = client.get(SENSITIVE, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401, r.text


def test_flag_on_health_stays_open(monkeypatch):
    monkeypatch.setenv("HELM_REQUIRE_AUTH", "1")
    monkeypatch.setenv("HELM_API_TOKEN", TOKEN)
    r = client.get(HEALTH)
    assert r.status_code == 200, r.text


def test_flag_on_but_no_token_configured_fails_closed(monkeypatch):
    """Enabled gate with an empty HELM_API_TOKEN must trust no one (fail closed)."""
    monkeypatch.setenv("HELM_REQUIRE_AUTH", "1")
    monkeypatch.delenv("HELM_API_TOKEN", raising=False)
    r = client.get(SENSITIVE, headers={"Authorization": "Bearer anything"})
    assert r.status_code == 401, r.text


def test_flag_on_static_ui_stays_open(monkeypatch):
    monkeypatch.setenv("HELM_REQUIRE_AUTH", "1")
    monkeypatch.setenv("HELM_API_TOKEN", TOKEN)
    r = client.get("/")
    # HTML shell must load without a token so it can attach the token to /api fetches.
    assert r.status_code == 200


# ------------------------------------------------------------------------- CORS
def test_cors_rejects_disallowed_origin():
    evil = "https://evil.example.com"
    r = client.get(HEALTH, headers={"Origin": evil})
    acao = r.headers.get("access-control-allow-origin")
    assert acao != evil
    assert acao != "*"


def test_cors_allows_allowlisted_origin():
    good = "http://127.0.0.1:8770"
    r = client.get(HEALTH, headers={"Origin": good})
    assert r.headers.get("access-control-allow-origin") == good


def test_resolve_cors_never_wildcard():
    origins = api_hardening.resolve_cors_origins({"HELM_CORS_ALLOWLIST": "*,https://a.ts.net"})
    assert "*" not in origins
    assert "https://a.ts.net" in origins


def test_resolve_cors_allowlist_takes_precedence():
    origins = api_hardening.resolve_cors_origins(
        {"HELM_CORS_ALLOWLIST": "https://x.example", "HELM_CORS_ORIGINS": "https://legacy"}
    )
    assert origins == ["https://x.example"]


def test_cors_tsnet_regex_matches():
    import re
    assert re.match(api_hardening._TSNET_REGEX, "https://helm-mac.tail1234.ts.net")
    assert re.match(api_hardening._TSNET_REGEX, "http://box.ts.net:8770")
    assert not re.match(api_hardening._TSNET_REGEX, "https://evil.example.com")


# -------------------------------------------------------------- security headers
def test_security_headers_present():
    r = client.get(HEALTH)
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "SAMEORIGIN"
    assert r.headers.get("referrer-policy") == "no-referrer"


# -------------------------------------------------------------- payload / limits
def test_payload_over_limit_rejected(monkeypatch):
    monkeypatch.setenv("HELM_MAX_BODY_BYTES", "10")
    # POST a body larger than 10 bytes to a real POST route.
    r = client.post("/api/founder/decide", content=b"x" * 100,
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 413, r.text


def test_sensitivity_classifier():
    assert api_hardening._is_sensitive("GET", "/api/v1/helm/tasks") is True
    assert api_hardening._is_sensitive("POST", "/api/v1/helm/jspace/cycle") is True
    assert api_hardening._is_sensitive("GET", "/api/helm/live") is False
    assert api_hardening._is_sensitive("GET", "/") is False
    assert api_hardening._is_sensitive("GET", "/brain") is False
