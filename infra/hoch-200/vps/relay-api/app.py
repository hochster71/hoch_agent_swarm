"""
HOCH-200 Relay API
==================
Tailscale-internal relay service for hoch-relay-001.
Port 3012 — only reachable via Tailscale IP 100.87.18.15.

Endpoints:
  GET  /            → Serve dashboard HTML
  GET  /health      → Health check (JSON)
  GET  /api/status  → Full status payload
  GET  /api/registry → Worker registry
  POST /api/heartbeat → Accept agent heartbeat
"""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse,  HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HOCH-200 Relay API",
    version="1.0.0",
    docs_url=None,   # disable swagger in prod
    redoc_url=None,
)

STATIC_DIR = Path(__file__).parent / "static"
REGISTRY_PATH = Path("/data/worker_registry.json")
HEARTBEAT_PATH = Path("/data/heartbeats.jsonl")

# Mount static dashboard if the directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_registry() -> dict[str, Any]:
    """Load worker registry from disk or return built-in bootstrap."""
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except Exception:
            pass
    # Bootstrap registry — always reflects this node
    return {
        "schema_version": "1.0",
        "generated_at": _now_iso(),
        "workers": [
            {
                "id": "HAS-WORKER-RELAY-001",
                "hostname": "hoch-relay-001",
                "public_ipv4": "50.116.41.183",
                "tailscale_ip": "100.87.18.15",
                "role": "relay",
                "status": "ONLINE",
                "capabilities": ["relay", "heartbeat", "api"],
                "last_seen": _now_iso(),
            }
        ],
    }


def _relay_worker() -> dict[str, Any]:
    registry = _load_registry()
    for w in registry.get("workers", []):
        if w.get("id") == "HAS-WORKER-RELAY-001":
            return w
    return {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard() -> HTMLResponse:
    """Serve the relay dashboard."""
    dashboard = STATIC_DIR / "index.html"
    if dashboard.exists():
        return HTMLResponse(content=dashboard.read_text(), status_code=200)
    return HTMLResponse(
        content="<h1>HOCH-200 Relay API</h1><p>Dashboard not found.</p>",
        status_code=200,
    )


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    worker = _relay_worker()
    return JSONResponse(
        {
            "status": "ok",
            "worker": "HAS-WORKER-RELAY-001",
            "worker_status": worker.get("status", "UNKNOWN"),
            "hostname": socket.gethostname(),
            "ts": _now_iso(),
        }
    )


@app.get("/api/status")
async def api_status() -> JSONResponse:
    """Full relay status payload."""
    registry = _load_registry()
    worker = _relay_worker()
    return JSONResponse(
        {
            "epic": "HOCH-200",
            "relay_node": "hoch-relay-001",
            "tailscale_ip": "100.87.18.15",
            "public_ipv4": "50.116.41.183",
            "port": 3012,
            "port_public_exposed": False,
            "worker_status": worker.get("status", "UNKNOWN"),
            "worker_id": "HAS-WORKER-RELAY-001",
            "registry_worker_count": len(registry.get("workers", [])),
            "ts": _now_iso(),
        }
    )


@app.get("/api/registry")
async def api_registry() -> JSONResponse:
    """Return worker registry."""
    return JSONResponse(_load_registry())


@app.post("/api/heartbeat")
async def api_heartbeat(request: Request) -> JSONResponse:
    """Accept a heartbeat ping from an agent."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    entry = {
        "received_at": _now_iso(),
        "source_ip": request.client.host if request.client else "unknown",
        "payload": body,
    }

    # Persist to JSONL
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HEARTBEAT_PATH.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")

    return JSONResponse({"accepted": True, "ts": entry["received_at"]})


# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """Ensure /data directory exists on startup."""
    Path("/data").mkdir(parents=True, exist_ok=True)
    # Write bootstrap registry if none exists
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(json.dumps(_load_registry(), indent=2))


@app.get("/")
def dashboard_root():
    return FileResponse("/app/static/index.html")
