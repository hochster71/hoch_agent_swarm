"""staged_server — the founder-approved cutover launcher (NOT auto-run).

This is the ONLY place that would actually change the live posture, and it is not
invoked by any supervisor, plist, or script. It exists so that AFTER founder
approval a human runs exactly one documented command (see
docs/HELM_ZERO_TRUST_CUTOVER.md) to bring up a hardened instance:

    * binds 127.0.0.1 (or a VPN iface) — NOT 0.0.0.0            (SC-7 / AC-4)
    * terminates TLS with the self-signed dev cert              (SC-8)
    * wraps the live app in the read-token gate                 (AC-3 / IA-2)

It imports the UNMODIFIED live app (``backend.helm_live_api:app``) and wraps it.
The live API source file is never edited. If run without a port override it will
REFUSE to bind the same :8770 the soak uses, to avoid a collision — the operator
must pass an explicit staging port for pre-cutover validation.
"""

from __future__ import annotations

import sys

from .config import HardenedConfig
from .read_auth import ReadAuthMiddleware


def build_hardened_app(config: HardenedConfig | None = None):
    """Wrap the live app with the read-auth gate. Pure composition, no I/O."""
    from backend.helm_live_api import app as live_app  # unmodified source

    cfg = config or HardenedConfig.from_env()
    return ReadAuthMiddleware(live_app, cfg)


def _preflight(cfg: HardenedConfig, staging_port: int | None) -> list[str]:
    reasons = cfg.validate_fail_closed()
    if staging_port is None and cfg.bind_port == 8770:
        reasons.append(
            "refusing to bind :8770 (the live soak port) without an explicit "
            "--staging-port; validate on a separate port first"
        )
    return reasons


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    staging_port = None
    if "--staging-port" in argv:
        staging_port = int(argv[argv.index("--staging-port") + 1])

    cfg = HardenedConfig.from_env()
    if staging_port is not None:
        cfg.bind_port = staging_port

    reasons = _preflight(cfg, staging_port)
    if reasons:
        print("STAGED CUTOVER BLOCKED (fail-closed):")
        for r in reasons:
            print(f"  - {r}")
        print("\nResolve every reason above and obtain founder approval before cutover.")
        return 2

    # Only reached when a human has set a safe, explicit config AND passed a
    # staging port. Even here we require --confirm to actually bind.
    if "--confirm" not in argv:
        print("Preflight OK. Re-run with --confirm to bind. Posture:")
        for k, v in cfg.summary().items():
            print(f"  {k}: {v}")
        return 0

    import uvicorn

    ssl_kwargs = {}
    if cfg.tls_enabled:
        from .dev_cert import CERT_PATH, KEY_PATH, generate_dev_cert

        cert = cfg.tls_cert or str(CERT_PATH)
        key = cfg.tls_key or str(KEY_PATH)
        generate_dev_cert()
        ssl_kwargs = {"ssl_certfile": cert, "ssl_keyfile": key}

    app = build_hardened_app(cfg)
    print(f"Binding hardened HELM on {cfg.bind_host}:{cfg.bind_port} (TLS={cfg.tls_enabled})")
    uvicorn.run(app, host=cfg.bind_host, port=cfg.bind_port, **ssl_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
