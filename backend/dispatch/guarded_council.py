"""Guarded council dispatch — routes every council model call through HELM's OWN
CouncilDispatchGateway (scripts/council/gateway.py), not a parallel path.

This is the security-correct dispatch: local-first, cost-capped, allowlisted, ledgered.
Each council lane maps to a local Ollama model and runs as LOCAL_OLLAMA — which the
gateway policy authorizes (free, guarded, environment=local_only). The zero-trust egress
guard is satisfied because the call goes through the sanctioned gateway, not raw urllib.

Frontier (API_OPENAI/API_ANTHROPIC) is intentionally founder-gated by the gateway policy
(metered_api_allowed=false); this module does not try to bypass that. Council runs on the
local brain by default — exactly the total-local-brain, guarded, 24/7-capable design.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Lane → local model. Chosen from the founder's installed Ollama set for a balance of
# capability and responsiveness. Every one is overridable by env without a code change.
# Light-by-default: 7–8B (3B for Local) so the council never locks the machine. Heavier
# models (qwen3:30b, gpt-oss:20b, deepseek-r1:32b, llama3.3:70b) are available anytime via
# the HELM_COUNCIL_MODEL_* env overrides when you want more depth and can spare the RAM/CPU.
LANE_MODEL = {
    "orchestrator": os.environ.get("HELM_COUNCIL_MODEL_ORCHESTRATOR", "qwen3:8b"),
    "builder":      os.environ.get("HELM_COUNCIL_MODEL_BUILDER",      "qwen2.5-coder:7b"),
    "auditor":      os.environ.get("HELM_COUNCIL_MODEL_AUDITOR",      "llama3.1:8b"),
    "local":        os.environ.get("HELM_COUNCIL_MODEL_LOCAL",        "llama3.2:3b"),
}
_DEFAULT_MODEL = os.environ.get("HELM_COUNCIL_MODEL_DEFAULT", "llama3.2:3b")

# Lanes that run the frontier Claude (Opus) via the `claude` CLI through the guarded gateway
# (CLI_CLAUDE). Founder-enabled: set HELM_COUNCIL_CLAUDE_LANES="builder" (or a comma list).
# Empty by default → the council stays fully local/free until the founder opts a lane in.
_CLAUDE_LANES = {x.strip().lower() for x in
                 os.environ.get("HELM_COUNCIL_CLAUDE_LANES", "").split(",") if x.strip()}

# Per-lane PROVIDER — honors HELM's role bindings (role_bindings.json):
#   auditor → Grok (xai)   builder → Claude (anthropic)   orchestrator → (openai, gated)
# Grok + Gemini CLIs are already authorized by the gateway policy (no founder grant).
# Claude (CLI_CLAUDE) stays founder-gated via HELM_COUNCIL_CLAUDE_LANES. Openai API is
# blocked by policy, so the orchestrator defaults to the local reasoning model until granted.
LANE_PROVIDER = {
    "orchestrator": os.environ.get("HELM_COUNCIL_PROVIDER_ORCHESTRATOR", "local"),
    "builder":      os.environ.get("HELM_COUNCIL_PROVIDER_BUILDER",      "local"),
    "auditor":      os.environ.get("HELM_COUNCIL_PROVIDER_AUDITOR",      "grok"),   # DESIGN: Grok
    "local":        "local",
}
# provider → (adapter name, CLI dispatch type). Local handled separately.
_FRONTIER_CLI = {"grok": "CLI_GROK", "gemini": "CLI_GEMINI", "claude": "CLI_CLAUDE"}

_GW = None


def provider_for(lane: str) -> str:
    lane = (lane or "").lower()
    if lane in _CLAUDE_LANES:
        return "claude"
    return LANE_PROVIDER.get(lane, "local")


def _gateway():
    global _GW
    if _GW is None:
        from scripts.council.gateway import CouncilDispatchGateway
        _GW = CouncilDispatchGateway()
    return _GW


def model_for(lane: str) -> str:
    p = provider_for(lane)
    if p == "claude":
        return "claude·opus"
    if p == "grok":
        return "grok (xai)"
    if p == "gemini":
        return "gemini"
    return LANE_MODEL.get((lane or "").lower(), _DEFAULT_MODEL)


def is_frontier_lane(lane: str) -> bool:
    return provider_for(lane) in _FRONTIER_CLI


def _guarded_frontier_cli(lane: str, prompt: str, provider: str, *, pert_node: str,
                          timeout: int) -> Dict[str, Any]:
    """Fire a role-bound FRONTIER lane (grok/gemini/claude) via its CLI through the guarded
    gateway. Grok + Gemini are policy-authorized (no grant); Claude is founder-gated."""
    from scripts.council.gateway import GatewayRequest, DispatchType
    lane = lane.lower()
    if provider == "claude":
        # Force Claude Code onto the flat Max plan (not per-token API billing): a set
        # ANTHROPIC_API_KEY makes the claude CLI bill via the API and overrides the Max login.
        os.environ.pop("ANTHROPIC_API_KEY", None)
    dtype = getattr(DispatchType, _FRONTIER_CLI[provider])
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    cap = float(os.environ.get("HELM_COUNCIL_FRONTIER_TASK_CAP_USD", "0.50"))
    req = GatewayRequest(
        task_id=f"COUNCIL-{lane.upper()}-{provider.upper()}-{ts}",
        pert_node=pert_node,
        caller_identity="helm_council_ui",
        dispatch_type=dtype,
        prompt=prompt,
        scope="read-only",
        environment="local_only",
        frontier_required=True,
        frontier_justification=f"HELM role-bound {lane} lane → {provider}",
        per_task_cap_usd=cap,
        timeout_seconds=timeout,
        metadata={"lane": lane, "provider": provider},
    )
    try:
        r = _gateway().dispatch(req)
    except Exception as e:
        return {"ok": False, "status": "GATEWAY_ERROR", "model": provider, "message": str(e)[:300]}
    label = "claude·opus" if provider == "claude" else f"{provider} ({'xai' if provider=='grok' else provider})"
    if r.status == "COMPLETED" and r.decision_status == "ALLOWED":
        return {"ok": True, "status": "SOLVED", "provider": f"{provider}·guarded", "model": label,
                "text": (r.output or "").strip(), "cost": r.estimated_cost,
                "latency_ms": r.latency_ms, "dispatch_id": r.dispatch_id}
    reason = ", ".join(r.blocks) if r.blocks else (r.stderr or "").strip()[:200] or r.status
    return {"ok": False, "status": r.decision_status or r.status, "model": label,
            "message": reason, "blocks": r.blocks, "dispatch_id": r.dispatch_id}


def _guarded_claude(lane: str, prompt: str, *, pert_node: str, timeout: int) -> Dict[str, Any]:
    """Fire the frontier Claude (Opus) lane via the `claude` CLI through the guarded gateway
    (CLI_CLAUDE — frontier, cost-capped, ledgered). Uses the founder's existing Claude auth;
    no API key handled here. Requires the founder policy grant (CLI_CLAUDE authorized)."""
    from scripts.council.gateway import GatewayRequest, DispatchType
    lane = lane.lower()
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    req = GatewayRequest(
        task_id=f"COUNCIL-{lane.upper()}-CLAUDE-{ts}",
        pert_node=pert_node,
        caller_identity="helm_council_ui",
        dispatch_type=DispatchType.CLI_CLAUDE,
        prompt=prompt,
        scope="read-only",
        environment="local_only",
        frontier_required=True,
        frontier_justification=f"Founder-approved Council frontier lane ({lane}) — Opus for high-value reasoning",
        per_task_cap_usd=float(os.environ.get("HELM_COUNCIL_CLAUDE_TASK_CAP_USD", "0.50")),
        timeout_seconds=timeout,
        metadata={"lane": lane, "model": "claude-opus"},
    )
    try:
        r = _gateway().dispatch(req)
    except Exception as e:
        return {"ok": False, "status": "GATEWAY_ERROR", "model": "claude·opus", "message": str(e)[:300]}
    if r.status == "COMPLETED" and r.decision_status == "ALLOWED":
        return {"ok": True, "status": "SOLVED", "provider": "claude·guarded", "model": "claude·opus",
                "text": (r.output or "").strip(), "cost": r.estimated_cost,
                "latency_ms": r.latency_ms, "dispatch_id": r.dispatch_id}
    reason = ", ".join(r.blocks) if r.blocks else (r.stderr or "").strip()[:200] or r.status
    return {"ok": False, "status": r.decision_status or r.status, "model": "claude·opus",
            "message": reason, "blocks": r.blocks, "dispatch_id": r.dispatch_id}


def guarded_dispatch(lane: str, prompt: str, *, pert_node: str = "COUNCIL",
                     timeout: int = 300) -> Dict[str, Any]:
    """Fire one lane's local model through the guarded gateway. Never raises — returns a
    structured result the UI can render (COMPLETED text, or a typed gateway block)."""
    from scripts.council.gateway import GatewayRequest, DispatchType
    lane = (lane or "local").lower()
    provider = provider_for(lane)
    if provider in _FRONTIER_CLI:   # role-bound frontier lane (auditor→grok, builder→claude, …)
        return _guarded_frontier_cli(lane, prompt, provider, pert_node=pert_node, timeout=timeout)
    model = LANE_MODEL.get(lane, _DEFAULT_MODEL)
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    req = GatewayRequest(
        task_id=f"COUNCIL-{lane.upper()}-{ts}",
        pert_node=pert_node,
        caller_identity="helm_council_ui",
        dispatch_type=DispatchType.LOCAL_OLLAMA,
        prompt=prompt,
        scope="read-only",
        environment="local_only",
        per_task_cap_usd=0.0,          # local is free
        timeout_seconds=timeout,
        metadata={"model": model, "lane": lane},
    )
    try:
        r = _gateway().dispatch(req)
    except Exception as e:  # gateway itself failed (import/policy) — honest, not fake
        return {"ok": False, "status": "GATEWAY_ERROR", "model": model, "message": str(e)[:300]}

    if r.status == "COMPLETED" and r.decision_status == "ALLOWED":
        return {"ok": True, "status": "SOLVED", "provider": "local·guarded", "model": model,
                "text": (r.output or "").strip(), "cost": r.estimated_cost,
                "latency_ms": r.latency_ms, "dispatch_id": r.dispatch_id}
    # blocked or failed — surface the gateway's typed reason honestly
    reason = ", ".join(r.blocks) if r.blocks else (r.stderr or "").strip()[:200] or r.status
    return {"ok": False, "status": r.decision_status or r.status, "model": model,
            "message": reason, "blocks": r.blocks, "dispatch_id": r.dispatch_id}


def guarded_ready() -> Dict[str, Any]:
    """Is the guarded local path usable? (ollama on PATH + policy authorizes LOCAL_OLLAMA).
    Presence/authorization only — no dispatch, no cost."""
    from scripts.council.gateway import GatewayRequest, DispatchType
    try:
        gw = _gateway()
        probe = GatewayRequest(task_id="COUNCIL-PROBE", pert_node="COUNCIL",
            caller_identity="helm_council_ui", dispatch_type=DispatchType.LOCAL_OLLAMA,
            prompt="probe", environment="local_only", per_task_cap_usd=0.0,
            metadata={"model": _DEFAULT_MODEL})
        d = gw.authorize(probe)
        return {"ready": d.allowed, "reason": None if d.allowed else ", ".join(d.blocks),
                "policy_local_first": bool(gw.policy.get("local_first")),
                "authorized_types": gw.policy.get("authorized_dispatch_types", [])}
    except Exception as e:
        return {"ready": False, "reason": f"gateway_unavailable: {str(e)[:160]}"}
