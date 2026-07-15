"""HELM Zero-Trust hardening layer (STAGED — never hot-applied).

This package is a *staged* Zero-Trust hardening layer for the HELM live API
(``backend/helm_live_api.py``, served on :8770). Nothing in here changes how the
already-running service binds. It is designed to be cut over LATER, only after
explicit founder approval, because the affected settings (bind address, TLS,
read-side authentication) are SECURITY SETTINGS that can break phone access over
Tailscale and the running Phase-C soak if flipped carelessly.

Components
----------
config.py        HardenedConfig — reads intended posture from env; safe defaults
                 (bind 127.0.0.1, read-auth DISABLED) so importing/using it changes
                 nothing until a launcher is explicitly run.
read_auth.py     ReadAuthMiddleware — ASGI gate on GET endpoints. DISABLED by
                 default; transparent passthrough until the env flag is set.
dev_cert.py      Self-signed dev cert generation into a gitignored path. Private
                 keys never leave disk and are never committed.
bind_audit.py    Fail-closed enumeration of live listeners + launch configs; flags
                 any 0.0.0.0 (all-interfaces) binding and the absence of TLS.
staged_server.py The staged launcher that would wrap the live app with the above.
                 It is NOT executed by anything; it exists for the founder-approved
                 cutover only.

NIST mapping (see docs/HELM_ZERO_TRUST_CUTOVER.md for the full matrix):
  AC-3  Access Enforcement            -> read_auth read-token gate
  AC-4  Information Flow Enforcement  -> bind 127.0.0.1 / VPN iface only
  SC-7  Boundary Protection          -> bind_audit + bind 127.0.0.1
  SC-8  Transmission Confidentiality  -> dev_cert TLS termination
  IA-2  Identification & Auth         -> read-token + existing founder token
Framework alignment: NIST SP 800-207 Zero Trust (never trust the network; every
request is authenticated and the boundary is minimized).
"""

from __future__ import annotations

__all__ = [
    "HardenedConfig",
    "ReadAuthMiddleware",
    "bind_audit",
    "dev_cert",
]
