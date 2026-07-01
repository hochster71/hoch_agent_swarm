"""
backend/relay_worker_adapter.py
===============================
Relay worker adapter for HAS-WORKER-RELAY-001.

Fetches live health and registry from the HOCH-200 relay API running on
hoch-relay-001 (Tailscale IP 100.87.18.15, port 3012).

Hard constraints enforced here:
  - Returns UNKNOWN on any network error (never synthesises ONLINE).
  - Does NOT bubble exceptions to callers.
  - Reads RELAY_BASE_URL from environment; default is Tailscale address.
  - Timeout is 3 seconds — never blocks the request cycle.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("RelayWorkerAdapter")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RELAY_BASE_URL: str = os.environ.get(
    "RELAY_BASE_URL", "http://100.87.18.15:3012"
).rstrip("/")

RELAY_WORKER_ID = "HAS-WORKER-RELAY-001"
RELAY_TIMEOUT_SEC = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _get_json(path: str) -> "dict[str, Any] | None":
    """
    Perform a GET request to the relay API and return parsed JSON.
    Returns None on any error — callers must treat None as UNKNOWN.
    """
    url = f"{RELAY_BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=RELAY_TIMEOUT_SEC) as resp:
            if resp.status != 200:
                logger.warning("Relay %s returned HTTP %s", path, resp.status)
                return None
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except urllib.error.URLError as exc:
        logger.warning("Relay unreachable at %s%s: %s", RELAY_BASE_URL, path, exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Relay %s returned non-JSON: %s", path, exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error fetching relay %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_relay_health() -> "dict[str, Any] | None":
    """
    Fetch /health from the relay API.

    Returns the parsed JSON dict on success, or None if the relay is
    unreachable or returns an unexpected response.

    Example successful response:
        {
            "status": "ok",
            "worker": "HAS-WORKER-RELAY-001",
            "worker_status": "ONLINE",
            "hostname": "hoch-relay-001",
            "ts": "2026-07-01T05:00:00Z"
        }
    """
    return _get_json("/health")


def fetch_relay_registry() -> "dict[str, Any] | None":
    """
    Fetch /api/registry from the relay API.

    Returns the parsed JSON dict on success, or None if unreachable.
    """
    return _get_json("/api/registry")


def get_relay_worker_status() -> str:
    """
    Return the live status of HAS-WORKER-RELAY-001.

    Possible return values:
        "ONLINE"  — relay reported ONLINE in /health response
        "UNKNOWN" — relay unreachable, returned non-200, or reported any
                    status other than ONLINE

    NEVER returns "PASS", "OK", or any synthetic value.
    """
    health = fetch_relay_health()
    if health is None:
        return "UNKNOWN"
    raw_status = health.get("worker_status", "UNKNOWN")
    # Only accept the literal string ONLINE — anything else is UNKNOWN
    return "ONLINE" if raw_status == "ONLINE" else "UNKNOWN"


def get_relay_worker_node() -> "dict[str, Any]":
    """
    Return a ClusterManager-compatible node dict for HAS-WORKER-RELAY-001.

    The `status` field reflects live relay state: "Active" when ONLINE,
    "Offline" when UNKNOWN. Matches the shape used by ClusterManager.nodes.
    """
    live_status = get_relay_worker_status()
    cm_status = "Active" if live_status == "ONLINE" else "Offline"

    return {
        "id": "RELAY-001",
        "fleet_group": "relay_compute",
        "name": "RELAY (hoch-relay-001)",
        "ip": "100.87.18.15",
        "role": "RELAY WORKER",
        "specs": "1 vCPU, 1GB RAM (Linode Nanode)",
        "status": cm_status,
        "activity": f"Relay worker {live_status} — heartbeat/forward capable",
        "missionDomain": "relay",
        "total_agents": 1,
        "os": "Ubuntu 24.04",
        "cpu_usage": 5,
        "ram_usage": 20,
        "latency_ms": 0.0,
        "agents": [
            {
                "name": RELAY_WORKER_ID,
                "type": "Relay Worker",
                "status": cm_status,
                "description": (
                    f"VPS relay worker on hoch-relay-001. "
                    f"Tailscale IP 100.87.18.15:3012. "
                    f"Live status: {live_status}. "
                    f"Port 3012 public exposure: FALSE."
                ),
            }
        ],
        # Relay-specific metadata
        "relay_worker_id": RELAY_WORKER_ID,
        "relay_status": live_status,
        "tailscale_ip": "100.87.18.15",
        "relay_port": 3012,
        "port_public_exposed": False,
        "epic": "HOCH-200",
        "fetched_at": _now_iso(),
    }


def get_relay_combined_status() -> "dict[str, Any]":
    """
    Return a combined relay status payload for /api/v1/relay/status.

    Merges live /health data with registry data and policy metadata.
    Always includes worker_status — never omits it.
    """
    health = fetch_relay_health()
    registry = fetch_relay_registry()

    worker_status = "UNKNOWN"
    hostname = "hoch-relay-001"
    ts = _now_iso()

    if health is not None:
        raw = health.get("worker_status", "UNKNOWN")
        worker_status = "ONLINE" if raw == "ONLINE" else "UNKNOWN"
        hostname = health.get("hostname", hostname)
        ts = health.get("ts", ts)

    registry_worker_count = 0
    workers = []
    if registry is not None:
        workers = registry.get("workers", [])
        registry_worker_count = len(workers)

    return {
        "epic": "HOCH-200",
        "relay_node": hostname,
        "worker_id": RELAY_WORKER_ID,
        "worker_status": worker_status,          # "ONLINE" | "UNKNOWN" only
        "tailscale_ip": "100.87.18.15",
        "relay_port": 3012,
        "port_public_exposed": False,             # immutable constraint
        "registry_worker_count": registry_worker_count,
        "workers": workers,
        "reachable": health is not None,
        "ts": ts,
        "fetched_at": _now_iso(),
    }
