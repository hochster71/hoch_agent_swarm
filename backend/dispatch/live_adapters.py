"""Live provider adapters — real HTTP calls, fail-closed and founder-gated.

Each adapter subclasses the FROZEN ProviderAdapter (imported from the audit target,
never modified) and implements a real ``invoke`` body. A call only fires when
``HELM_DISPATCH_ENABLED`` is set AND the provider key is present; otherwise it raises
DispatchNotEnabledError (no fake success). Keys are read from the environment at call
time and used only as auth headers — never printed, logged, or returned.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional

# Import from the FROZEN target — do not modify those files.
from backend.helm_runtime.dispatch_gateway import (
    ProviderAdapter,
    DispatchRequest,
    DispatchNotEnabledError,
)
from backend.helm_runtime.provider_router import PROVIDER_KEY_ENV, resolve_worker

DISPATCH_FLAG = "HELM_DISPATCH_ENABLED"
_TIMEOUT = 60


def dispatch_globally_enabled() -> bool:
    """Founder money-gate: live dispatch is OFF unless this env flag is set."""
    return bool(os.environ.get(DISPATCH_FLAG))


class _LiveAdapter(ProviderAdapter):
    """Base for real adapters. health() reports dispatch_implemented=True."""

    api_base: str = ""

    def health(self) -> Dict[str, Any]:
        present = self.credential_present()
        enabled = dispatch_globally_enabled()
        live = present and enabled
        return {
            "provider": self.provider,
            "configured": present,
            "dispatch_enabled_flag": enabled,
            "status": "READY" if live else "BLOCKED",
            "reason": None if live else (
                "HELM_DISPATCH_ENABLED not set (founder money-gate)" if present
                else "provider credential unavailable (founder-gated)"),
            "dispatch_implemented": True,  # live body present
        }

    def _key(self) -> Optional[str]:
        env = PROVIDER_KEY_ENV.get(self.provider)
        return os.environ.get(env) if env else None

    def _guard(self) -> str:
        if not dispatch_globally_enabled():
            raise DispatchNotEnabledError(
                f"{self.provider}: dispatch disabled — set {DISPATCH_FLAG}=1 (founder money-gate)")
        key = self._key()
        if self.provider != "local" and not key:
            raise DispatchNotEnabledError(f"{self.provider}: no API key present")
        return key or ""

    def _model(self, request: DispatchRequest) -> str:
        m = (request.metadata or {}).get("model")
        if m:
            return m
        # resolve from the role binding if a role is given
        if request.role:
            b = resolve_worker(request.role)
            if b.get("model"):
                return b["model"]
        return {"openai": "gpt-4o", "anthropic": "claude-3-5-sonnet-latest",
                "xai": "grok-2-latest", "local": "llama3"}[self.provider]

    def _post(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return json.loads(r.read().decode())

    def stream(self, request: DispatchRequest):  # streaming not in v1
        raise DispatchNotEnabledError(f"{self.provider}: streaming not implemented (v1)")

    def cancel(self, handle: str) -> Dict[str, Any]:
        raise DispatchNotEnabledError(f"{self.provider}: cancel not implemented (v1)")


class LiveOpenAIAdapter(_LiveAdapter):
    provider = "openai"

    def invoke(self, request: DispatchRequest) -> Dict[str, Any]:
        key = self._guard()
        model = self._model(request)
        out = self._post(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {key}"},
            {"model": model, "messages": [{"role": "user", "content": request.prompt}]},
        )
        text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return {"provider": "openai", "model": model, "text": text, "usage": out.get("usage")}


class LiveAnthropicAdapter(_LiveAdapter):
    provider = "anthropic"

    def invoke(self, request: DispatchRequest) -> Dict[str, Any]:
        key = self._guard()
        model = self._model(request)
        out = self._post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            {"model": model, "max_tokens": 4096,
             "messages": [{"role": "user", "content": request.prompt}]},
        )
        text = "".join(b.get("text", "") for b in (out.get("content") or []))
        return {"provider": "anthropic", "model": model, "text": text, "usage": out.get("usage")}


class LiveXAIAdapter(_LiveAdapter):
    provider = "xai"

    def invoke(self, request: DispatchRequest) -> Dict[str, Any]:
        key = self._guard()
        model = self._model(request)
        out = self._post(
            "https://api.x.ai/v1/chat/completions",
            {"Authorization": f"Bearer {key}"},
            {"model": model, "messages": [{"role": "user", "content": request.prompt}]},
        )
        text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return {"provider": "xai", "model": model, "text": text, "usage": out.get("usage")}


class LiveLocalAdapter(_LiveAdapter):
    provider = "local"

    def invoke(self, request: DispatchRequest) -> Dict[str, Any]:
        self._guard()
        base = os.environ.get("HELM_LOCAL_MODEL_URL")
        if not base:
            raise DispatchNotEnabledError("local: HELM_LOCAL_MODEL_URL not set")
        model = self._model(request)
        out = self._post(
            base.rstrip("/") + "/api/generate", {},
            {"model": model, "prompt": request.prompt, "stream": False},
        )
        return {"provider": "local", "model": model, "text": out.get("response", "")}


LIVE_ADAPTERS = (LiveOpenAIAdapter, LiveAnthropicAdapter, LiveXAIAdapter, LiveLocalAdapter)
