"""Zero-Trust hardening proofs (STAGED layer).

These tests prove the staged hardening components behave, WITHOUT touching the live
:8770 service, without any external network call, and without binding any real
socket. Everything runs in-process (ASGI TestClient) or against static files.

Covered:
  * bind_audit detects a 0.0.0.0 (all-interfaces) binding — in the real repo config
    AND against a synthetic listener table.
  * bind_audit is fail-closed (FAIL verdict + nonzero exit on any exposure).
  * read-auth is transparent when disabled and rejects (401) when enabled.
  * read-auth POST path is never gated by this middleware (founder token owns it).
  * the self-signed dev TLS cert generates and loads into an SSLContext.
  * HardenedConfig defaults are safe (loopback, read-auth off) and validate fail-closed.
"""

from __future__ import annotations

import ssl
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.security.zero_trust import bind_audit  # noqa: E402
from backend.security.zero_trust.config import HardenedConfig  # noqa: E402
from backend.security.zero_trust.read_auth import ReadAuthMiddleware  # noqa: E402
from backend.security.zero_trust import dev_cert  # noqa: E402


# --------------------------------------------------------------------------- app
def _mini_app():
    """A tiny Starlette app with a GET and a POST — stands in for the live API so we
    never touch :8770."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def read(request):
        return JSONResponse({"ok": True, "kind": "read"})

    async def write(request):
        return JSONResponse({"ok": True, "kind": "write"})

    return Starlette(
        routes=[
            Route("/api/v1/helm/tasks", read, methods=["GET"]),
            Route("/api/v1/helm/wall", read, methods=["GET"]),
            Route("/api/founder/decide", write, methods=["POST"]),
        ]
    )


def _client(app):
    from starlette.testclient import TestClient

    return TestClient(app)


# ------------------------------------------------------------------- bind audit
def test_bind_audit_live_launcher_hardened_but_flags_remaining():
    """Post Zero-Trust cutover (DEC-ZT-CUTOVER-001): the live-API launcher
    helm_autoloop.sh is loopback-bound, so it is NO LONGER flagged. The audit still
    fail-closes (FAIL) because other 0.0.0.0 configs remain in the tree — the retired
    voice launcher scripts (dead: their launchd job is disabled) and separate
    services (docker :8000, relay :8010). That is an honest 'not fully hardened yet'
    verdict; detection of a 0.0.0.0 binding is proven against a synthetic fixture in
    test_bind_audit_flags_synthetic_all_interface_listener."""
    report = bind_audit.run_audit()
    files = {f["file"] for f in report["config"]["all_interface_bindings"]}
    assert not any("helm_autoloop.sh" in f for f in files), (
        f"helm_autoloop.sh must stay loopback-bound after the cutover; found {files}"
    )
    assert report["verdict"] == "FAIL"      # other services / dead scripts still expose 0.0.0.0
    assert report["exit_code"] == 2


def test_bind_audit_flags_synthetic_all_interface_listener(monkeypatch):
    """Prove the runtime lens flags a 0.0.0.0 listener, independent of config."""

    class _Addr:
        ip = "0.0.0.0"
        port = 8770

    class _Conn:
        status = "LISTEN"
        laddr = _Addr()
        pid = None

    import psutil

    monkeypatch.setattr(psutil, "CONN_LISTEN", "LISTEN", raising=False)
    monkeypatch.setattr(psutil, "net_connections", lambda kind="inet": [_Conn()])
    res = bind_audit.enumerate_listeners()
    assert res["available"] is True
    exposed = [l for l in res["listeners"] if l["all_interfaces"]]
    assert exposed and exposed[0]["port"] == 8770


def test_bind_audit_fail_closed_when_runtime_unavailable(monkeypatch):
    """If runtime enumeration is impossible AND config is clean, verdict is UNKNOWN
    (never a silent PASS)."""
    monkeypatch.setattr(
        bind_audit,
        "enumerate_listeners",
        lambda: {"available": False, "reason": "simulated", "listeners": []},
    )
    monkeypatch.setattr(
        bind_audit, "scan_config_bindings", lambda: {"files_scanned": 0, "findings": []}
    )
    report = bind_audit.run_audit()
    assert report["verdict"] == "UNKNOWN"
    assert report["exit_code"] == 3


def test_bind_audit_reports_tls_configured_post_cutover():
    """Post-cutover the live-API launcher terminates TLS at the origin (SC-8)."""
    report = bind_audit.run_audit()
    assert report["tls"]["live_api_tls_configured"] is True


# -------------------------------------------------------------------- read auth
def test_read_auth_transparent_when_disabled():
    cfg = HardenedConfig(read_auth_enabled=False)
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get("/api/v1/helm/tasks")
    assert r.status_code == 200
    assert r.json()["kind"] == "read"


def test_read_auth_rejects_get_without_token_when_enabled():
    cfg = HardenedConfig(read_auth_enabled=True, read_token="s3cret")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get("/api/v1/helm/tasks")
    assert r.status_code == 401
    assert r.json()["state"] == "UNAUTHORIZED"


def test_read_auth_allows_get_with_valid_token():
    cfg = HardenedConfig(read_auth_enabled=True, read_token="s3cret")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get(
        "/api/v1/helm/tasks", headers={"X-HELM-Read-Token": "s3cret"}
    )
    assert r.status_code == 200


def test_read_auth_accepts_bearer_token():
    cfg = HardenedConfig(read_auth_enabled=True, read_token="s3cret")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get(
        "/api/v1/helm/tasks", headers={"Authorization": "Bearer s3cret"}
    )
    assert r.status_code == 200


def test_read_auth_rejects_bad_token():
    cfg = HardenedConfig(read_auth_enabled=True, read_token="s3cret")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get(
        "/api/v1/helm/tasks", headers={"X-HELM-Read-Token": "wrong"}
    )
    assert r.status_code == 401


def test_read_auth_allowlisted_path_open_when_enabled():
    """The wall health path stays reachable so a probe/HTML shell still loads."""
    cfg = HardenedConfig(read_auth_enabled=True, read_token="s3cret")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get("/api/v1/helm/wall")
    assert r.status_code == 200


def test_read_auth_does_not_gate_post():
    """POST keeps its own founder-token gate; this middleware must not touch it."""
    cfg = HardenedConfig(read_auth_enabled=True, read_token="s3cret")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).post("/api/founder/decide", json={})
    # reaches the app (which returns 200 here) — NOT a 401 from the read gate
    assert r.status_code == 200
    assert r.json()["kind"] == "write"


def test_read_auth_enabled_but_no_token_fails_closed():
    """Enabled gate with no configured token trusts no one (never fail open)."""
    cfg = HardenedConfig(read_auth_enabled=True, read_token="")
    app = ReadAuthMiddleware(_mini_app(), cfg)
    r = _client(app).get(
        "/api/v1/helm/tasks", headers={"X-HELM-Read-Token": "anything"}
    )
    assert r.status_code == 401


# -------------------------------------------------------------------------- TLS
def test_dev_cert_generates_and_loads(tmp_path):
    cert = tmp_path / "c.pem"
    key = tmp_path / "k.pem"
    c, k = dev_cert.generate_dev_cert(cert, key)
    assert c.exists() and k.exists()
    ctx = dev_cert.load_ssl_context(cert, key)
    assert isinstance(ctx, ssl.SSLContext)


def test_dev_cert_key_is_gitignored():
    """The cert directory must carry a local .gitignore excluding key material."""
    dev_cert.generate_dev_cert(overwrite=False)
    gi = dev_cert.CERT_DIR / ".gitignore"
    assert gi.exists()
    body = gi.read_text()
    assert "*" in body


# ----------------------------------------------------------------------- config
def test_hardened_config_defaults_are_safe():
    cfg = HardenedConfig()
    assert cfg.bind_host == "127.0.0.1"
    assert cfg.binds_all_interfaces() is False
    assert cfg.read_auth_enabled is False
    assert cfg.validate_fail_closed() == []


def test_hardened_config_flags_all_interfaces():
    cfg = HardenedConfig(bind_host="0.0.0.0")
    assert cfg.binds_all_interfaces() is True
    reasons = cfg.validate_fail_closed()
    assert any("all interfaces" in r for r in reasons)


def test_hardened_config_from_env_stays_safe_by_default():
    cfg = HardenedConfig.from_env(env={})
    assert cfg.bind_host == "127.0.0.1"
    assert cfg.read_auth_enabled is False
    assert cfg.tls_enabled is False
