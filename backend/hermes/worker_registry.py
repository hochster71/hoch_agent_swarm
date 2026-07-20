"""HERMES Worker Registry — the one place a worker's manifest lives.

WHAT THIS IS: manifests (what a worker can do, what it costs) + OBSERVED availability.
WHAT THIS IS NOT: a discovery scanner, a dispatcher, a queue, or a second event bus.

REUSE (no duplication — HELM doctrine):
  * local discovery      → scripts/scan_ai_runtimes.py          (existing probe, called, not reimplemented)
  * local model health   → backend/model_health_monitor.MONITOR (existing)
  * frozen role bindings → backend/helm_runtime/provider_router (frozen; read-only)
  * dispatch execution   → scripts/council/gateway.py via backend/dispatch/guarded_council
                           (HERMES never dispatches here — see hermes/dispatcher.py)

NO FAKE GREEN: availability is UNKNOWN until observed. A manifest never asserts a worker
is up; only a probe (local) or credential/CLI presence (remote) can move it to AVAILABLE.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "coordination" / "hermes" / "workers.json"

# Remote workers are reachable only if their CLI/credential is actually present.
_CLI_FOR = {"claude_code": "claude", "grok_cli": "grok", "gemini_cli": "gemini"}
_ENV_FOR = {"openai_api": "OPENAI_API_KEY"}


def _load(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"workers": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"workers": {}}


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _observe(wid: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Observe availability. Returns {availability, evidence} — never guesses."""
    loc = (spec.get("locality") or "").lower()
    if loc == "local":
        port = ((spec.get("discovery") or {}).get("port"))
        if not port:
            return {"availability": "UNKNOWN", "evidence": "no discovery probe declared"}
        up = _port_open(int(port))
        return {"availability": "AVAILABLE" if up else "UNREACHABLE",
                "evidence": f"tcp 127.0.0.1:{port} {'open' if up else 'closed'}"}
    # remote: CLI on PATH, or credential env present
    cli = _CLI_FOR.get(wid)
    if cli:
        p = shutil.which(cli) or shutil.which(str(Path.home() / f".{cli}" / "bin" / cli))
        return {"availability": "AVAILABLE" if p else "NOT_CONFIGURED",
                "evidence": f"cli '{cli}' {'on PATH' if p else 'not found'}"}
    env = _ENV_FOR.get(wid)
    if env:
        return {"availability": "AVAILABLE" if os.environ.get(env) else "NOT_CONFIGURED",
                "evidence": f"env {env} {'present' if os.environ.get(env) else 'absent'}"}
    return {"availability": "UNKNOWN", "evidence": "no observation method"}


def list_workers(*, observe: bool = True) -> List[Dict[str, Any]]:
    """All worker manifests, with OBSERVED availability when observe=True."""
    out: List[Dict[str, Any]] = []
    for wid, spec in (_load().get("workers") or {}).items():
        rec: Dict[str, Any] = {"id": wid, **spec}
        rec.update(_observe(wid, spec) if observe else
                   {"availability": "UNOBSERVED", "evidence": "observe=False"})
        out.append(rec)
    return out


def get_worker(worker_id: str, *, observe: bool = True) -> Optional[Dict[str, Any]]:
    for w in list_workers(observe=observe):
        if w["id"] == worker_id:
            return w
    return None


def discover_local(*, register: bool = False) -> Dict[str, Any]:
    """Local model discovery — REUSES scripts/scan_ai_runtimes.py rather than
    re-implementing a scanner. Returns the models each local runtime is serving."""
    found: Dict[str, Any] = {"ollama": [], "lmstudio": [], "source": "scripts/scan_ai_runtimes.py"}
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from scripts.scan_ai_runtimes import fetch_json  # reuse, do not duplicate
        if _port_open(11434):
            d = fetch_json("http://127.0.0.1:11434/api/tags") or {}
            found["ollama"] = [m.get("name") for m in (d.get("models") or []) if m.get("name")]
        if _port_open(1234):
            d = fetch_json("http://127.0.0.1:1234/v1/models") or {}
            found["lmstudio"] = [m.get("id") for m in (d.get("data") or []) if m.get("id")]
    except Exception as e:  # fail-closed, honest
        found["error"] = f"{type(e).__name__}: {e}"
    found["observed_models"] = len(found["ollama"]) + len(found["lmstudio"])
    return found


def registry_health() -> Dict[str, Any]:
    """Honest rollup for projections/UI."""
    ws = list_workers()
    by = lambda s: [w["id"] for w in ws if w["availability"] == s]  # noqa: E731
    return {
        "schema": "HERMES_REGISTRY_HEALTH_v1",
        "total": len(ws),
        "available": by("AVAILABLE"),
        "not_configured": by("NOT_CONFIGURED"),
        "unreachable": by("UNREACHABLE"),
        "unknown": by("UNKNOWN"),
        "local_discovery": discover_local(),
        "doctrine": "availability observed, never asserted",
    }
