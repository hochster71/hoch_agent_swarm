"""Live gateway — composes the frozen DispatchGateway with LIVE adapters.

HELM invokes the models through this. The frozen DispatchGateway class is reused
unchanged (composition, not modification); only the adapters are swapped for live
ones. Every path is fail-closed unless the founder has enabled dispatch + supplied keys.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from backend.helm_runtime.dispatch_gateway import DispatchGateway, DispatchRequest
from backend.dispatch.live_adapters import LIVE_ADAPTERS, dispatch_globally_enabled

_HELM_ENV = Path.home() / ".helm" / "helm.env"


def autoload_env() -> None:
    """Load the founder-controlled ~/.helm/helm.env into the process env if present.

    setdefault only — never overrides an already-exported value, never prints a value.
    This means the founder enters keys once (via helm_enable_dispatch.sh) and every HELM
    dispatch picks them up automatically — no re-paste, no manual `source`.
    """
    if not _HELM_ENV.exists():
        return
    try:
        for line in _HELM_ENV.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k and v:
                os.environ.setdefault(k, v)
    except Exception:
        pass  # fail-closed: if the file is unreadable, dispatch just stays gated


def dispatch_enabled() -> bool:
    autoload_env()
    return dispatch_globally_enabled()


def live_gateway() -> DispatchGateway:
    """The frozen gateway, but wired with live (real-call) adapters."""
    return DispatchGateway(adapters=[cls() for cls in LIVE_ADAPTERS])


def dispatch(
    *,
    role: Optional[str] = None,
    capability: Optional[str] = None,
    provider: Optional[str] = None,
    prompt: str = "",
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """HELM fires a model. Resolves capability/role → provider → live adapter → real call,
    or targets a provider directly (e.g. local) when `provider` is given.

    Fail-closed: raises DispatchNotEnabledError unless HELM_DISPATCH_ENABLED + key present.
    Returns {provider, model, text, usage} on success. Never logs secrets.
    """
    from backend.helm_runtime.dispatch_gateway import DispatchNotEnabledError
    autoload_env()  # pick up ~/.helm/helm.env automatically — no manual source needed
    md = dict(metadata or {})
    if model:
        md["model"] = model
    req = DispatchRequest(role=role or "", capability=capability, prompt=prompt, metadata=md)
    gw = live_gateway()
    if provider:  # direct provider targeting (local, or an explicit override)
        ad = gw._adapters.get(provider.lower())
        if ad is None:
            raise DispatchNotEnabledError(f"no adapter registered for provider {provider!r}")
        return ad.invoke(req)
    return gw.dispatch(req)
