#!/usr/bin/env python3
"""HELM credential validator — reports which provider workers are configured.

Reports PRESENCE only (and optional lightweight live validity). NEVER prints, stores,
or logs a key value. Reads whatever env is currently exported (source ~/.helm/helm.env
first). Use to confirm dispatch is ready to enable after the founder supplies keys.

Usage:
  set -a; . ~/.helm/helm.env; set +a
  python3 scripts/helm_validate_credentials.py            # presence only
  python3 scripts/helm_validate_credentials.py --live     # + provider auth probe
"""
from __future__ import annotations
import os, sys, json, urllib.request

PROVIDERS = {
    "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/models"),
    "anthropic": ("ANTHROPIC_API_KEY", "https://api.anthropic.com/v1/models"),
    "xai": ("XAI_API_KEY", "https://api.x.ai/v1/models"),
    "gemini": ("GEMINI_API_KEY", None),
    "local": ("HELM_LOCAL_MODEL_URL", None),
}


def _probe(provider: str, url: str, key: str) -> str:
    try:
        req = urllib.request.Request(url)
        if provider == "anthropic":
            req.add_header("x-api-key", key); req.add_header("anthropic-version", "2023-06-01")
        else:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=8) as r:
            return "VALID" if r.status == 200 else f"HTTP_{r.status}"
    except Exception as e:
        code = getattr(e, "code", None)
        return f"HTTP_{code}" if code else "UNREACHABLE"


def main() -> int:
    # Auto-load the founder-controlled env so presence reflects what HELM will actually see.
    try:
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from backend.dispatch.live_gateway import autoload_env
        autoload_env()
    except Exception:
        pass
    live = "--live" in sys.argv
    rows = []
    for prov, (env, url) in PROVIDERS.items():
        val = os.environ.get(env)
        present = bool(val)
        status = "CONFIGURED" if present else "BLOCKED"
        validity = None
        if live and present and url:
            validity = _probe(prov, url, val)  # key used, never printed
        rows.append({"provider": prov, "env": env, "present": present,
                     "status": status, "live_validity": validity})
    configured = [r["provider"] for r in rows if r["present"]]
    out = {"configured_count": len(configured), "configured": configured,
           "blocked": [r["provider"] for r in rows if not r["present"]],
           "detail": rows, "note": "presence only; no key value is ever printed or stored"}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
