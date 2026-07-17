"""API hardening for the HELM LIVE control-plane API (backend/helm_live_api.py).

Remediates the mission-assurance audit findings against uvicorn :8770:

  * R-CORS : permissive ``allow_origins=["*"]`` on a credentialed control plane.
  * R-AUTH : an unauthenticated sensitive GET/POST surface.

DOCTRINE — nothing breaks today
-------------------------------
Every enforcement here is FLAGGED and default-OFF, so importing/mounting this
module changes NOTHING about the behaviour of the currently-running server or the
founder's open dashboards until an env flag is deliberately set and the server is
restarted by the founder.

  HELM_REQUIRE_AUTH=1        -> deny-by-default bearer-token gate on the sensitive
                               API surface. Requires ``Authorization: Bearer <tok>``
                               where ``tok == HELM_API_TOKEN``. Default off ==
                               transparent passthrough (behaviour unchanged).
  HELM_API_TOKEN=<secret>    -> the expected bearer token. NEVER hardcoded; read
                               from env only. If auth is enabled but this is empty
                               the gate FAILS CLOSED (401 for everything gated).
  HELM_CORS_ALLOWLIST=a,b,c  -> comma-separated CORS origin allowlist. Falls back
                               to the legacy HELM_CORS_ORIGINS, then to a safe
                               loopback default. Never ``*``.
  HELM_CORS_ALLOW_TSNET=1    -> additionally allow any ``*.ts.net`` (Tailscale)
                               origin via a strict regex.
  HELM_RATE_LIMIT_ENABLED=1  -> per-client-IP fixed-window rate limiter on /api/*.
  HELM_RATE_LIMIT_RPM=<n>    -> requests/minute/IP (default 600).
  HELM_MAX_BODY_BYTES=<n>    -> reject bodies over this size with 413 (default 2MB).

Security response headers (X-Content-Type-Options, X-Frame-Options,
Referrer-Policy) are applied UNCONDITIONALLY — they are non-breaking for the
dashboards and improve posture immediately.

The flags read here are intentionally re-read from ``os.environ`` on EACH request
so a single mounted instance responds to env changes at restart without any code
change, and so tests can exercise both postures against one app.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
from typing import Awaitable, Callable, Dict, List, Tuple

# --------------------------------------------------------------------------- env
_TRUTHY = {"1", "true", "yes", "on", "enabled"}


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in _TRUTHY


# Default CORS allowlist: loopback + common local FE ports. Explicitly NEVER "*".
_DEFAULT_CORS_ORIGINS: List[str] = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8770",
    "https://127.0.0.1:8770",
    "http://localhost:8770",
    "https://localhost:8770",
    "http://127.0.0.1:8788",
    "http://localhost:8788",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "null",  # file:// and some embedded webviews
]

# Strict Tailscale magic-DNS origin: scheme://<host>.ts.net[:port] only.
_TSNET_REGEX = r"^https?://[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9-]+)*\.ts\.net(?::\d+)?$"

# CORS request headers the consoles legitimately send.
_CORS_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Helm-Read-Token",
    "X-HELM-Read-Token",
]
_CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]


def resolve_cors_origins(env: dict | None = None) -> List[str]:
    """Return the concrete CORS origin allowlist. NEVER contains ``*``."""
    e = os.environ if env is None else env
    raw = (e.get("HELM_CORS_ALLOWLIST") or e.get("HELM_CORS_ORIGINS") or "").strip()
    if raw == "":
        origins = list(_DEFAULT_CORS_ORIGINS)
    else:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
    # Hard guarantee: a wildcard is never honoured on a credentialed control plane.
    origins = [o for o in origins if o != "*"]
    return origins


def cors_middleware_kwargs(env: dict | None = None) -> dict:
    """kwargs for ``app.add_middleware(CORSMiddleware, **kwargs)``.

    allow_credentials is False (with credentials off, browsers still let the
    dashboards read same-origin data; we never pair credentials with a wildcard).
    """
    e = os.environ if env is None else env
    kwargs: dict = {
        "allow_origins": resolve_cors_origins(e),
        "allow_methods": _CORS_ALLOW_METHODS,
        "allow_headers": _CORS_ALLOW_HEADERS,
        "allow_credentials": False,
    }
    if _truthy(e.get("HELM_CORS_ALLOW_TSNET")):
        kwargs["allow_origin_regex"] = _TSNET_REGEX
    return kwargs


# ------------------------------------------------------------------- auth policy
# Paths that stay OPEN even when HELM_REQUIRE_AUTH is on:
#   * the liveness/health probe
#   * the founder gate endpoints (they enforce their OWN founder-token gate; adding
#     the API bearer on top would break the founder's phone approval flow)
# Everything else under /api/ is sensitive and requires the bearer token.
_AUTH_OPEN_EXACT = {
    "/api/helm/live",
    "/api/founder/queue",
    "/api/founder/decide",
}
_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def _is_sensitive(method: str, path: str) -> bool:
    """Deny-by-default over the API surface; static UI + health stay open."""
    if not path.startswith("/api/"):
        return False  # static UI / HTML shells / JS helpers
    if path in _AUTH_OPEN_EXACT:
        return False
    # All remaining /api/* reads AND every mutating verb are sensitive.
    return True if (path.startswith("/api/") or method in _MUTATING) else False


def _bearer_from_headers(headers: List[Tuple[bytes, bytes]]) -> str | None:
    for k, v in headers:
        if k.lower() == b"authorization":
            val = v.decode("latin-1")
            if val[:7].lower() == "bearer ":
                return val[7:].strip()
    return None


# ------------------------------------------------------------- in-memory limiter
class _RateLimiter:
    """Fixed-window per-IP counter. Deliberately simple, process-local."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: Dict[Tuple[str, int], int] = {}
        self._last_gc = 0.0

    def check(self, ip: str, limit_per_min: int) -> bool:
        now = time.time()
        window = int(now // 60)
        key = (ip, window)
        with self._lock:
            # cheap periodic GC of stale windows
            if now - self._last_gc > 120:
                self._buckets = {k: c for k, c in self._buckets.items() if k[1] >= window - 1}
                self._last_gc = now
            count = self._buckets.get(key, 0) + 1
            self._buckets[key] = count
            return count <= limit_per_min


_LIMITER = _RateLimiter()

_SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"SAMEORIGIN"),
    (b"referrer-policy", b"no-referrer"),
]


class ApiHardeningMiddleware:
    """Pure-ASGI middleware: payload limit + rate limit + bearer gate + headers.

    Wrapping order (outermost recommended): add this LAST so it short-circuits
    before the heavy handlers and stamps security headers on every response.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        headers = scope.get("headers", [])

        # 1) Payload-size limit (always on; generous default). GET has no body.
        max_body = _int_env("HELM_MAX_BODY_BYTES", 2_000_000)
        clen = _content_length(headers)
        if clen is not None and clen > max_body:
            await self._reject(send, 413, "PAYLOAD_TOO_LARGE",
                               "request body exceeds HELM_MAX_BODY_BYTES")
            return

        # 2) Rate limit (flagged) — only over the /api/ surface.
        if path.startswith("/api/") and _truthy(os.environ.get("HELM_RATE_LIMIT_ENABLED")):
            rpm = _int_env("HELM_RATE_LIMIT_RPM", 600)
            ip = self._client_ip(scope)
            if not _LIMITER.check(ip, rpm):
                await self._reject(send, 429, "RATE_LIMITED",
                                   "too many requests", retry_after=60)
                return

        # 3) Bearer auth gate (flagged, deny-by-default). OPTIONS/preflight exempt.
        if method != "OPTIONS" and _truthy(os.environ.get("HELM_REQUIRE_AUTH")):
            if _is_sensitive(method, path):
                configured = os.environ.get("HELM_API_TOKEN", "")
                presented = _bearer_from_headers(headers)
                ok = bool(configured) and bool(presented) and hmac.compare_digest(presented, configured)
                if not ok:
                    await self._reject(send, 401, "UNAUTHORIZED",
                                       "sensitive endpoint requires a valid bearer token",
                                       www_authenticate=True)
                    return

        # 4) Pass through, stamping security headers on the response start.
        await self._app_with_headers(scope, receive, send)

    # -- helpers -----------------------------------------------------------
    async def _app_with_headers(self, scope, receive, send):
        async def _send(event):
            if event.get("type") == "http.response.start":
                hdrs = list(event.get("headers") or [])
                present = {k.lower() for k, _ in hdrs}
                for k, v in _SECURITY_HEADERS:
                    if k not in present:
                        hdrs.append((k, v))
                event = {**event, "headers": hdrs}
            await send(event)

        await self.app(scope, receive, _send)

    @staticmethod
    def _client_ip(scope) -> str:
        client = scope.get("client")
        if client and isinstance(client, (list, tuple)) and client:
            return str(client[0])
        return "unknown"

    async def _reject(self, send: Callable[[dict], Awaitable[None]], status: int,
                      state: str, message: str, *, retry_after: int | None = None,
                      www_authenticate: bool = False):
        body = json.dumps({"ok": False, "state": state, "message": message}).encode()
        hdrs = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        hdrs.extend(_SECURITY_HEADERS)
        if retry_after is not None:
            hdrs.append((b"retry-after", str(retry_after).encode()))
        if www_authenticate:
            hdrs.append((b"www-authenticate", b'Bearer realm="helm-api"'))
        await send({"type": "http.response.start", "status": status, "headers": hdrs})
        await send({"type": "http.response.body", "body": body})


def _content_length(headers: List[Tuple[bytes, bytes]]) -> int | None:
    for k, v in headers:
        if k.lower() == b"content-length":
            try:
                return int(v.decode("latin-1").strip())
            except Exception:
                return None
    return None


def _int_env(name: str, default: int) -> int:
    try:
        return int(str(os.environ.get(name, default)).strip())
    except Exception:
        return default


# ------------------------------------------------------ optional route dependency
def bearer_auth_dependency(authorization: str | None = None) -> None:
    """FastAPI dependency form of the bearer gate, for per-route opt-in use.

    The ApiHardeningMiddleware already enforces deny-by-default globally when
    HELM_REQUIRE_AUTH=1; this helper is provided for routes that want an explicit
    ``Depends(...)`` marker. Raises fastapi.HTTPException(401) on failure.

    Usage:
        from fastapi import Depends, Header
        @app.get("/x", dependencies=[Depends(require_bearer)])

    where ``require_bearer`` wraps this with a Header(...) parameter.
    """
    from fastapi import HTTPException

    if not _truthy(os.environ.get("HELM_REQUIRE_AUTH")):
        return None
    configured = os.environ.get("HELM_API_TOKEN", "")
    token = None
    if authorization and authorization[:7].lower() == "bearer ":
        token = authorization[7:].strip()
    if not (configured and token and hmac.compare_digest(token, configured)):
        raise HTTPException(status_code=401, detail="unauthorized")
    return None
