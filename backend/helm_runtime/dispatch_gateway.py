"""Dispatch Gateway (skeleton) — the layer between Mission Runtime and providers.

Per EDR-0002: the Provider Router must NOT invoke providers directly. All
cross-provider communication concerns — retries, timeouts, rate limiting,
streaming, cancellation, budgeting, metrics, circuit breakers, auth,
normalization — live here, behind one interface, so they never leak into the
runtime.

STATUS: skeleton. No provider SDK is imported, no network call is made, no
secret is read. Every adapter reports its honest health (BLOCKED until
founder-supplied credentials exist) and every ``invoke`` fails CLOSED with
``DispatchNotEnabledError``. There is no stubbed success anywhere — the system
can honestly report "architecturally ready, 0 workers configured" without ever
faking dispatch.

Enabling real dispatch is a later, founder-gated step (supply credentials +
implement adapter bodies), tracked as EDR-0002 follow-on work.
"""
from __future__ import annotations

import abc
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.helm_runtime.capability_registry import route_capability
from backend.helm_runtime.provider_router import PROVIDER_KEY_ENV, resolve_worker


class DispatchNotEnabledError(RuntimeError):
    """Raised when a caller attempts dispatch that is not yet enabled.

    Fail-closed by design: dispatch is architecturally present but no provider
    is credentialed/implemented, so invocation must error rather than pretend.
    """


@dataclass
class DispatchRequest:
    role: str
    capability: Optional[str] = None
    prompt: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProviderAdapter(abc.ABC):
    """One provider = one plugin behind the gateway.

    Concrete adapters (OpenAI/Anthropic/xAI/Local) implement these. In the
    skeleton, invoke/stream/cancel fail closed; only health/capabilities report.
    """

    provider: str = "abstract"

    def __init__(self, *, env_key: Optional[str] = None) -> None:
        # Presence-only credential awareness — the value is never read.
        self.env_key = env_key if env_key is not None else PROVIDER_KEY_ENV.get(self.provider)

    def credential_present(self) -> bool:
        if self.provider == "local":
            # Local provider is "present" only if an endpoint is configured.
            return bool(os.environ.get("HELM_LOCAL_MODEL_URL"))
        return bool(self.env_key and os.environ.get(self.env_key))

    def health(self) -> Dict[str, Any]:
        present = self.credential_present()
        return {
            "provider": self.provider,
            "configured": present,
            "status": "READY" if present else "BLOCKED",
            "reason": None if present else "provider credential unavailable (founder-gated)",
            "dispatch_implemented": False,  # skeleton — no live invoke body yet
        }

    def capabilities(self) -> List[str]:
        return []

    @abc.abstractmethod
    def invoke(self, request: DispatchRequest) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def stream(self, request: DispatchRequest):
        ...

    @abc.abstractmethod
    def cancel(self, handle: str) -> Dict[str, Any]:
        ...


class _SkeletonAdapter(ProviderAdapter):
    """Registered but not enabled: fails closed on any dispatch attempt."""

    def _blocked(self) -> Dict[str, Any]:
        raise DispatchNotEnabledError(
            f"{self.provider}: dispatch not enabled (skeleton; no credential/adapter body)"
        )

    def invoke(self, request: DispatchRequest) -> Dict[str, Any]:
        return self._blocked()

    def stream(self, request: DispatchRequest):
        return self._blocked()

    def cancel(self, handle: str) -> Dict[str, Any]:
        return self._blocked()


class OpenAIAdapter(_SkeletonAdapter):
    provider = "openai"


class AnthropicAdapter(_SkeletonAdapter):
    provider = "anthropic"


class XAIAdapter(_SkeletonAdapter):
    provider = "xai"


class LocalAdapter(_SkeletonAdapter):
    provider = "local"


DEFAULT_ADAPTERS = (OpenAIAdapter, AnthropicAdapter, XAIAdapter, LocalAdapter)


class DispatchGateway:
    """Registers adapters and reports honest worker/mission health. No dispatch."""

    def __init__(self, adapters: Optional[List[ProviderAdapter]] = None) -> None:
        self._adapters: Dict[str, ProviderAdapter] = {}
        for a in adapters if adapters is not None else [cls() for cls in DEFAULT_ADAPTERS]:
            self._adapters[a.provider] = a

    def providers(self) -> List[str]:
        return list(self._adapters.keys())

    def health(self) -> List[Dict[str, Any]]:
        return [a.health() for a in self._adapters.values()]

    def worker_status(self) -> Dict[str, Any]:
        """Honest {configured, available, blocked} projection (runtime-truth aligned)."""
        available, blocked = [], []
        for prov, a in self._adapters.items():
            (available if a.credential_present() else blocked).append(prov)
        return {
            "configured": len(available),
            "available": available,
            "blocked": blocked,
            "total": len(self._adapters),
        }

    def worker_role_health(self) -> List[Dict[str, Any]]:
        """Per-role worker health — distinct from raw provider health.

        Distinguishes configured vs unconfigured, reachable vs not, dispatch
        enabled vs intentionally disabled. Reachability is NOT probed on the
        network in the skeleton (would be a side-effect); it is reported false
        until dispatch is enabled and a live probe exists.
        """
        from backend.helm_runtime.provider_router import VALID_ROLES, resolve_worker

        rows: List[Dict[str, Any]] = []
        for role in VALID_ROLES:
            binding = resolve_worker(role)
            provider = (binding.get("provider") or "").lower()
            adapter = self._adapters.get(provider) if provider else None
            configured = bool(binding.get("configured"))
            # Skeleton: dispatch never enabled; reachable stays false without live probe.
            dispatch_enabled = bool(
                adapter is not None
                and configured
                and adapter.health().get("dispatch_implemented") is True
            )
            if adapter is None:
                reason = f"No adapter registered for provider {provider!r}" if provider else "No provider binding"
            elif not configured:
                reason = "Provider credentials unavailable"
            elif not adapter.health().get("dispatch_implemented"):
                reason = "Adapter body not implemented (dispatch skeleton; fail-closed)"
            else:
                reason = None
            rows.append(
                {
                    "role": role,
                    "binding": provider or None,
                    "model": binding.get("model"),
                    "display_name": binding.get("display_name"),
                    "configured": configured,
                    "reachable": False if not dispatch_enabled else False,  # no live probe yet
                    "dispatch_enabled": dispatch_enabled,
                    "status": "AVAILABLE" if dispatch_enabled else "BLOCKED",
                    "reason": reason,
                }
            )
        return rows

    def dispatch(self, request: DispatchRequest) -> Dict[str, Any]:
        """Resolve capability→role→provider then attempt invoke (fails closed today)."""
        role = request.role
        if request.capability:
            r = route_capability(request.capability)
            if not r.get("resolved"):
                raise DispatchNotEnabledError(f"unroutable capability: {request.capability}")
            role = r["role"]
        binding = resolve_worker(role)
        provider = (binding.get("provider") or "").lower()
        adapter = self._adapters.get(provider)
        if adapter is None:
            raise DispatchNotEnabledError(f"no adapter registered for provider {provider!r}")
        # Fails closed here until credentials + adapter bodies are supplied.
        return adapter.invoke(request)

    def mission_health(self) -> Dict[str, Any]:
        """Executive Mission Health projection for the dark UI panel."""
        from backend.helm_runtime.mission_store import read_mission

        doc = read_mission()
        mission_active = doc.get("error") != "MISSION_ABSENT" and doc.get("mission_version") is not None
        ws = self.worker_status()
        founder_gate = "CLEARED" if ws["configured"] > 0 else "PENDING"
        return {
            "engine": "dispatch_gateway",
            "is_actor": False,
            "runtime": {
                "mission_runtime": "ACTIVE" if mission_active else "UNKNOWN",
                "runtime_truth": "AVAILABLE",
                "governance": "ENFORCED",
                "dispatch": "READY",  # gateway present; adapters registered
            },
            "workers": ws,
            "founder_gate": founder_gate,
            "reason": None if ws["configured"] else "Provider credentials unavailable",
            "doctrine": "architecturally ready; no fake dispatch until founder-supplied credentials",
        }


def default_gateway() -> DispatchGateway:
    return DispatchGateway()
