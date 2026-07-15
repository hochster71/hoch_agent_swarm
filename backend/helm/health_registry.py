"""HELM service health registry — runtime truth for "what is actually alive right now".

DOCTRINE (same as backend/helm_live_api.py)
--------------------------------------------
Every entry here is OBSERVED at request time by an actual probe:

    listeners   <- `lsof -iTCP -sTCP:LISTEN -P -n`      (real OS socket table, if available)
    liveness    <- a real TCP connect (+ HTTP GET where the port speaks HTTP)

There are NO fallbacks and NOTHING is inferred from a static file. A curated
port map exists ONLY to attach a human-readable name/description to a port —
it never substitutes for a probe. A port that is in the curated map but does
not respond is DOWN, exactly like an unlisted one. A port that cannot be
probed at all (permission denied, probe mechanism itself failed) is UNKNOWN —
never assumed healthy. Fail-closed, always.

This module is intentionally self-contained (imports nothing from
backend.helm_live_api) so it can be included there with a two-line
route-registration block, per the source-tree coordination guard's rule of
keeping edits to that hot file minimal.
"""
from __future__ import annotations

import datetime
import json
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[2]
CONTROL_PLANE_UI = ROOT / "frontend_live" / "control_plane.html"

UNKNOWN = "UNKNOWN"
CONFIRMED_LIVE = "CONFIRMED_LIVE"
DOWN = "DOWN"

TCP_TIMEOUT_SECONDS = 0.6
HTTP_TIMEOUT_SECONDS = 1.5
LSOF_TIMEOUT_SECONDS = 4.0

# ---------------------------------------------------------------------------
# Curated port map. Labels ONLY — never a substitute for a live probe.
# Compiled from launchd plists, docker-compose*.yml, backend/*.py uvicorn
# bindings, and config/port_hardening_audit.json (repo history, 2026-06-26).
# ~19 known HELM-family services across the ALPHA node + worker mesh.
KNOWN_PORTS: Dict[int, Dict[str, str]] = {
    8770: {"name": "helm_live_api", "http_path": "/api/v1/helm/wall",
           "description": "HELM Live API — runtime-truth API + PERT wall (this service)"},
    8765: {"name": "pert_server", "http_path": "/api/pert/data",
           "description": "Authoritative PERT/CPM computation API"},
    8777: {"name": "has_live_truth_sidecar", "http_path": "/api/live",
           "description": "Anti-fake-green live truth telemetry sidecar"},
    8010: {"name": "widget_static_server", "http_path": "/",
           "description": "Static widget/frontend file server (python -m http.server)"},
    8000: {"name": "backend_main", "http_path": "/",
           "description": "Main HELM API / control-plane (FastAPI, backend/main.py)"},
    8080: {"name": "has_ui_tool_service", "http_path": "/",
           "description": "HAS UI / alternate swarm tool service"},
    8788: {"name": "reserved_unconfirmed", "http_path": "/",
           "description": "Curated placeholder — no confirmed process found in repo history; probe decides"},
    8789: {"name": "hasf_mesh_studio", "http_path": "/",
           "description": "Hasf Mesh Studio mesh console (Node dev server)"},
    3000: {"name": "swarm_frontend_dev", "http_path": "/",
           "description": "hoch-agent-swarm frontend dev server (Node)"},
    3012: {"name": "remote_relay_api", "http_path": "/",
           "description": "Remote relay API (Tailscale-reachable)"},
    8086: {"name": "hochster_operator_health", "http_path": "/",
           "description": "Hochster app operator health endpoint"},
    8443: {"name": "live_cockpit", "http_path": "/",
           "description": "Live cockpit binding (TLS)"},
    8787: {"name": "hochster_api", "http_path": "/",
           "description": "Hochster API control plane"},
    8797: {"name": "family_ops_dashboard", "http_path": "/",
           "description": "Legacy family-ops dashboard (may be unloaded)"},
    8810: {"name": "dell_worker_pull_server", "http_path": "/",
           "description": "Dell worker pull server (mesh node)"},
    8820: {"name": "neo_worker_pull_server", "http_path": "/",
           "description": "Neo worker pull server (mesh node)"},
    8830: {"name": "imac_worker_pull_server", "http_path": "/",
           "description": "iMac worker pull server (mesh node)"},
    8898: {"name": "temp_http_file_server", "http_path": "/",
           "description": "Temporary HTTP file server"},
    9090: {"name": "prometheus", "http_path": "/-/healthy",
           "description": "Prometheus metrics (cloud mirror only)"},
}


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _git_commit() -> str:
    """Best-effort HEAD sha. Never raises; UNKNOWN if git is unavailable."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=str(ROOT), timeout=3)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return UNKNOWN


# ---------------------------------------------------------------------------
# lsof-based discovery — real OS listener table.
def discover_listeners() -> Tuple[Dict[int, str], bool, Optional[str]]:
    """Parse `lsof -iTCP -sTCP:LISTEN -P -n`.

    Returns (port -> process_label, ok, error). ok=False means the discovery
    mechanism itself failed (binary missing, permission, timeout) — callers
    MUST treat that as "we don't know", not as "nothing is listening".
    """
    try:
        res = subprocess.run(
            ["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"],
            capture_output=True, text=True, timeout=LSOF_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return {}, False, "lsof binary not found on PATH"
    except subprocess.TimeoutExpired:
        return {}, False, "lsof timed out"
    except Exception as e:
        return {}, False, f"lsof failed: {type(e).__name__}: {e}"

    if res.returncode not in (0, 1):
        # lsof returns 1 when it finds nothing to report, which is a valid empty result,
        # not a failure. Anything else is treated as an unreliable read.
        return {}, False, f"lsof exited {res.returncode}: {res.stderr.strip()[:200]}"

    out: Dict[int, str] = {}
    for line in res.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 9:
            continue
        proc_name = parts[0]
        name_field = parts[8]  # e.g. "127.0.0.1:8770" or "*:8080"
        if ":" not in name_field:
            continue
        port_str = name_field.rsplit(":", 1)[-1]
        try:
            port = int(port_str)
        except ValueError:
            continue
        out[port] = proc_name
    return out, True, None


# ---------------------------------------------------------------------------
# Live probes.
def _tcp_probe(port: int, host: str = "127.0.0.1") -> Tuple[str, str]:
    """Real TCP connect. Returns (state, detail).

    REFUSED (nothing listening) is the ONLY case that proves DOWN. Anything
    else we can't be sure about, so it stays UNKNOWN rather than being
    silently called healthy or dead.
    """
    try:
        with socket.create_connection((host, port), timeout=TCP_TIMEOUT_SECONDS):
            return "OPEN", "tcp connect succeeded"
    except ConnectionRefusedError:
        return "REFUSED", "connection actively refused — nothing listening"
    except socket.timeout:
        return "TIMEOUT", "tcp connect timed out — cannot confirm either way"
    except OSError as e:
        return "ERROR", f"tcp connect error: {e}"
    except Exception as e:
        return "ERROR", f"unexpected probe error: {type(e).__name__}: {e}"


def _http_probe(port: int, path: str, host: str = "127.0.0.1") -> Tuple[Optional[int], str]:
    """Best-effort HTTP GET on a port already known to accept TCP connections.

    Returns (status_code_or_None, detail). A None status means the socket
    accepted the connection but did not speak HTTP the way we asked (still
    real signal — the port is open, just not confirmed as this HTTP service).
    """
    url = f"http://{host}:{port}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "helm-health-registry/1.0"})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            return resp.status, "http probe ok"
    except urllib.error.HTTPError as e:
        # A real HTTP response (even 4xx/5xx) proves the service is alive and speaking HTTP.
        return e.code, f"http error response ({e.code})"
    except Exception as e:
        return None, f"http probe failed: {type(e).__name__}: {e}"


def probe_service(port: int, meta: Dict[str, str], listeners: Dict[int, str],
                   lsof_ok: bool) -> Dict[str, Any]:
    """Fail-closed liveness classification for one port.

    CONFIRMED_LIVE — a real TCP connect succeeded (HTTP details attached if available).
    DOWN           — a real TCP connect was actively refused.
    UNKNOWN        — anything else: timeout, permission error, ambiguous probe state.
    """
    checked_at = _now_iso()
    tcp_state, tcp_detail = _tcp_probe(port)
    process_label = listeners.get(port)
    discovered_via_lsof = port in listeners

    if tcp_state == "OPEN":
        http_status, http_detail = _http_probe(port, meta.get("http_path", "/"))
        detail = tcp_detail if http_status is None else f"{tcp_detail}; {http_detail}"
        state = CONFIRMED_LIVE
    elif tcp_state == "REFUSED":
        http_status, http_detail = None, None
        detail = tcp_detail
        state = DOWN
    else:
        http_status, http_detail = None, None
        detail = tcp_detail
        state = UNKNOWN

    return {
        "port": port,
        "name": meta.get("name", f"port_{port}"),
        "description": meta.get("description", ""),
        "curated": True,
        "discovered_via_lsof": discovered_via_lsof,
        "process": process_label,
        "state": state,
        "detail": detail,
        "http_status": http_status,
        "checked_at": checked_at,
    }


def build_registry() -> Dict[str, Any]:
    """Discover + probe every known HELM port, plus any extra listener lsof finds
    that is not in the curated map (labeled but never assumed healthy)."""
    t0 = time.time()
    listeners, lsof_ok, lsof_error = discover_listeners()

    services: List[Dict[str, Any]] = []
    for port, meta in sorted(KNOWN_PORTS.items()):
        services.append(probe_service(port, meta, listeners, lsof_ok))

    # Any listener lsof found that ISN'T in the curated map — surface it too,
    # rather than hiding real listening sockets the map doesn't know about yet.
    extra_ports = sorted(set(listeners) - set(KNOWN_PORTS))
    for port in extra_ports:
        meta = {"name": f"undocumented:{listeners[port]}", "http_path": "/",
                "description": "listening socket found via lsof; not in the curated HELM port map"}
        entry = probe_service(port, meta, listeners, lsof_ok)
        entry["curated"] = False
        services.append(entry)

    summary = {
        "total": len(services),
        "confirmed_live": sum(1 for s in services if s["state"] == CONFIRMED_LIVE),
        "down": sum(1 for s in services if s["state"] == DOWN),
        "unknown": sum(1 for s in services if s["state"] == UNKNOWN),
        "curated_count": len(KNOWN_PORTS),
        "undocumented_listeners": len(extra_ports),
    }

    return {
        "truth_class": "HELM_SERVICE_HEALTH_TRUTH",
        "source": "backend.helm.health_registry (lsof + curated port map + tcp/http probes)",
        "observed_at": _now_iso(),
        "freshness_seconds": round(time.time() - t0, 3),
        "tested_commit": _git_commit(),
        "data": {
            "lsof_available": lsof_ok,
            "lsof_error": lsof_error,
            "services": services,
            "summary": summary,
        },
    }


# ---------------------------------------------------------------------------
# Router — included in backend/helm_live_api.py with a two-line edit.
health_router = APIRouter()


@health_router.get("/api/v1/helm/health")
def api_v1_helm_health() -> JSONResponse:
    try:
        return JSONResponse(build_registry())
    except Exception as e:
        # Fail-closed on the endpoint itself too — never a bare 500 with no shape.
        return JSONResponse(status_code=200, content={
            "truth_class": "HELM_SERVICE_HEALTH_TRUTH",
            "source": "backend.helm.health_registry",
            "observed_at": _now_iso(),
            "freshness_seconds": None,
            "tested_commit": _git_commit(),
            "data": {"state": UNKNOWN, "reason": f"registry build failed: {type(e).__name__}: {e}",
                     "services": [], "summary": {}},
        })


@health_router.get("/control", response_class=HTMLResponse)
def serve_control_plane() -> str:
    """Unified control-plane shell — same-origin, dark theme, links the 5 consoles
    plus the live health board and cross-link integrity strip."""
    if CONTROL_PLANE_UI.exists():
        return CONTROL_PLANE_UI.read_text()
    return "<h1>control_plane.html missing</h1>"
