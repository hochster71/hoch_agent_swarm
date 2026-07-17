"""HELM live dispatch — the layer that lets HELM invoke the frontier + local models.

New files only. The frozen audit target (backend/helm_runtime/*, verification_target
d8d5139a) is NOT modified: live adapters subclass the frozen ProviderAdapter and are
INJECTED into the existing DispatchGateway via composition.

Fail-closed and founder-gated: a live call happens only when BOTH
  - HELM_DISPATCH_ENABLED is set (founder turns dispatch on — money gate), and
  - the provider's API key is present in the environment.
Otherwise every invoke raises DispatchNotEnabledError. No secret is ever logged.
"""
from backend.dispatch.live_gateway import live_gateway, dispatch, dispatch_enabled

__all__ = ["live_gateway", "dispatch", "dispatch_enabled"]
