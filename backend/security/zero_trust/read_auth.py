"""ReadAuthMiddleware — a fail-closed read-token gate on GET endpoints.

Doctrine
--------
Today the POST founder-decision path (``/api/founder/decide``) is token-gated and
returns 401 on a bad ``HELM_FOUNDER_TOKEN``. Every GET/read endpoint is ungated.
This middleware adds IA-2 identification + AC-3 access enforcement on the read
path — but it is DISABLED BY DEFAULT so that turning it on is a deliberate,
founder-approved act and nothing breaks in the meantime.

Behaviour
---------
* ``config.read_auth_enabled is False``  -> transparent passthrough. The request
  reaches the wrapped app exactly as before. This is the state at import time and
  the state during the soak until cutover.
* ``config.read_auth_enabled is True``   -> a GET whose path is not on the
  allowlist must present the read token (header ``X-HELM-Read-Token`` or
  ``Authorization: Bearer <token>``). A missing/bad token yields 401 and never
  reaches the app. Non-GET methods are NOT touched here (POST keeps its own
  founder-token gate, unchanged).

Constant-time comparison (``hmac.compare_digest``) avoids a timing oracle. If the
gate is enabled but no token is configured, the gate fails CLOSED (401 for
everything non-allowlisted) rather than silently allowing all — never fail open.
"""

from __future__ import annotations

import hmac
import json
from typing import Awaitable, Callable

from .config import HardenedConfig


class ReadAuthMiddleware:
    """Pure-ASGI middleware. Wrapping order: ReadAuthMiddleware(app, config)."""

    def __init__(self, app, config: HardenedConfig | None = None):
        self.app = app
        self.config = config or HardenedConfig.from_env()

    # -- token extraction --------------------------------------------------
    def _present_token(self, headers: list[tuple[bytes, bytes]]) -> str | None:
        want = self.config.read_token_header.lower().encode()
        for k, v in headers:
            if k.lower() == want:
                return v.decode("latin-1")
        for k, v in headers:
            if k.lower() == b"authorization":
                val = v.decode("latin-1")
                if val.lower().startswith("bearer "):
                    return val[7:].strip()
        return None

    def _is_allowlisted(self, path: str) -> bool:
        return path in self.config.read_auth_allowlist

    def authorized(self, path: str, headers: list[tuple[bytes, bytes]]) -> bool:
        if self._is_allowlisted(path):
            return True
        token = self._present_token(headers)
        configured = self.config.read_token
        if not configured:
            return False  # fail closed: enabled gate with no token trusts no one
        return bool(token) and hmac.compare_digest(token, configured)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        # Transparent passthrough unless explicitly enabled.
        if not self.config.read_auth_enabled:
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET").upper()
        if method != "GET":
            # POST/PUT/etc keep their own gates (e.g. founder token). Untouched.
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        headers = scope.get("headers", [])
        if self.authorized(path, headers):
            await self.app(scope, receive, send)
            return
        await self._reject(send)

    async def _reject(self, send: Callable[[dict], Awaitable[None]]):
        body = json.dumps(
            {
                "ok": False,
                "state": "UNAUTHORIZED",
                "message": "read access requires HELM read token (IA-2/AC-3)",
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b'Bearer realm="helm-read"'),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
