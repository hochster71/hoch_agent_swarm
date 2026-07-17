"""Live gateway — composes the frozen DispatchGateway with LIVE adapters.

HELM invokes the models through this. The frozen DispatchGateway class is reused
unchanged (composition, not modification); only the adapters are swapped for live
ones. Every path is fail-closed unless the founder has enabled dispatch + supplied keys.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.helm_runtime.dispatch_gateway import DispatchGateway, DispatchRequest
from backend.dispatch.live_adapters import LIVE_ADAPTERS, dispatch_globally_enabled


def dispatch_enabled() -> bool:
    return dispatch_globally_enabled()


def live_gateway() -> DispatchGateway:
    """The frozen gateway, but wired with live (real-call) adapters."""
    return DispatchGateway(adapters=[cls() for cls in LIVE_ADAPTERS])


def dispatch(
    *,
    role: Optional[str] = None,
    capability: Optional[str] = None,
    prompt: str = "",
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """HELM fires a model. Resolves capability/role → provider → live adapter → real call.

    Fail-closed: raises DispatchNotEnabledError unless HELM_DISPATCH_ENABLED + key present.
    Returns {provider, model, text, usage} on success. Never logs secrets.
    """
    md = dict(metadata or {})
    if model:
        md["model"] = model
    req = DispatchRequest(role=role or "", capability=capability, prompt=prompt, metadata=md)
    return live_gateway().dispatch(req)
