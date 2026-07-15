"""HardenedConfig — the intended Zero-Trust posture, read from the environment.

CRITICAL: constructing this object changes NOTHING at runtime. It only *describes*
the posture a founder-approved launcher would apply at cutover. Every default is
chosen so that if a launcher were run without any extra configuration it would be
strictly SAFER than today (loopback bind) yet still TRANSPARENT on the read path
(read-auth disabled), so the Phase-C soak and the founder's phone keep working
until the token is deliberately provisioned and enabled.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[3]

# Env flag names (documented in the cutover runbook).
ENV_BIND_HOST = "HELM_HARDENED_BIND_HOST"
ENV_BIND_PORT = "HELM_HARDENED_BIND_PORT"
ENV_READ_AUTH_ENABLED = "HELM_READ_AUTH_ENABLED"
ENV_READ_TOKEN = "HELM_READ_TOKEN"
ENV_TLS_ENABLED = "HELM_TLS_ENABLED"
ENV_TLS_CERT = "HELM_TLS_CERT"
ENV_TLS_KEY = "HELM_TLS_KEY"


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on", "enabled")


@dataclass
class HardenedConfig:
    """Declarative, side-effect-free description of the staged posture."""

    # SC-7 / AC-4: default to loopback, NOT 0.0.0.0. A VPN (Tailscale) iface can be
    # substituted at cutover, but never all-interfaces.
    bind_host: str = "127.0.0.1"
    bind_port: int = 8770

    # AC-3 / IA-2: read-token gate on GET endpoints. DISABLED by default so nothing
    # breaks until the founder provisions a token to the phone and flips the flag.
    read_auth_enabled: bool = False
    read_token: str = ""
    # GET paths that stay reachable WITHOUT a token even when the gate is enabled
    # (so a health probe and the login-less HTML shell can still load). Fetches the
    # page then makes are still gated.
    read_auth_allowlist: List[str] = field(
        default_factory=lambda: ["/api/v1/helm/wall"]
    )
    read_token_header: str = "x-helm-read-token"

    # SC-8: TLS termination. Disabled by default because the running service is
    # plain HTTP and TLS is a cutover-only security change.
    tls_enabled: bool = False
    tls_cert: str = ""
    tls_key: str = ""

    @classmethod
    def from_env(cls, env: dict | None = None) -> "HardenedConfig":
        e = dict(os.environ if env is None else env)
        return cls(
            bind_host=e.get(ENV_BIND_HOST, "127.0.0.1"),
            bind_port=int(e.get(ENV_BIND_PORT, "8770") or "8770"),
            read_auth_enabled=_truthy(e.get(ENV_READ_AUTH_ENABLED)),
            read_token=e.get(ENV_READ_TOKEN, ""),
            tls_enabled=_truthy(e.get(ENV_TLS_ENABLED)),
            tls_cert=e.get(ENV_TLS_CERT, ""),
            tls_key=e.get(ENV_TLS_KEY, ""),
        )

    # ------------------------------------------------------------------ safety
    def binds_all_interfaces(self) -> bool:
        return self.bind_host in ("0.0.0.0", "::", "")

    def validate_fail_closed(self) -> list[str]:
        """Return a list of reasons this config is NOT safe to cut over.

        Empty list == safe to proceed (still requires human approval). This is a
        fail-closed check: any doubt is surfaced as a blocking reason.
        """
        reasons: list[str] = []
        if self.binds_all_interfaces():
            reasons.append(
                f"bind_host={self.bind_host!r} exposes all interfaces (violates SC-7/AC-4)"
            )
        if self.read_auth_enabled and not self.read_token:
            reasons.append(
                "read_auth_enabled but no read_token set — would lock out every reader (fail-closed)"
            )
        if self.tls_enabled and (not self.tls_cert or not self.tls_key):
            reasons.append("tls_enabled but cert/key path missing")
        if self.tls_enabled and self.tls_cert and not Path(self.tls_cert).exists():
            reasons.append(f"tls_cert not found at {self.tls_cert}")
        if self.tls_enabled and self.tls_key and not Path(self.tls_key).exists():
            reasons.append(f"tls_key not found at {self.tls_key}")
        return reasons

    def summary(self) -> dict:
        return {
            "bind_host": self.bind_host,
            "bind_port": self.bind_port,
            "binds_all_interfaces": self.binds_all_interfaces(),
            "read_auth_enabled": self.read_auth_enabled,
            "read_token_configured": bool(self.read_token),
            "tls_enabled": self.tls_enabled,
            "staged_only": True,
            "hot_applied": False,
        }
