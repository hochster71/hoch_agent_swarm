from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


SCAN_PATH = Path("artifacts/network_discovery/ai_runtime_scan.json")

EXPECTED_AI_RUNTIMES = [
    {
        "id": "10.0.0.8:1234",
        "label": "NEO LM Studio",
        "ip": "10.0.0.8",
        "port": 1234,
        "kind": "LM_STUDIO",
        "expected": True,
    }
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_scan() -> Dict[str, Any]:
    if not SCAN_PATH.exists():
        return {
            "generated_at": None,
            "summary": {},
            "findings": [],
            "missing_scan_artifact": True,
        }

    try:
        return json.loads(SCAN_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "generated_at": None,
            "summary": {},
            "findings": [],
            "scan_read_error": str(exc),
        }


def _runtime_kind(port: int, raw_kind: str | None = None) -> str:
    text = (raw_kind or "").lower()
    if port == 1234 or "lmstudio" in text or "openai" in text:
        return "LM_STUDIO"
    if port == 11434 or "ollama" in text:
        return "OLLAMA"
    return (raw_kind or "UNKNOWN").upper()


def _models_from_finding(finding: Dict[str, Any]) -> List[str]:
    models = finding.get("models") or []
    names: List[str] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("id") or model.get("name") or model.get("model")
        if name:
            names.append(str(name))
    return sorted(set(names))


def build_mesh_sentinel_map() -> Dict[str, Any]:
    scan = _read_scan()
    generated_at = _utc_now()
    scan_generated_at = scan.get("generated_at")
    findings = scan.get("findings") or []

    nodes: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []
    unexpected_exposures: List[Dict[str, Any]] = []
    missing_assets: List[Dict[str, Any]] = []

    seen_ids = set()

    for finding in findings:
        if not isinstance(finding, dict):
            continue

        host = str(finding.get("host") or finding.get("ip") or "").strip()
        port = int(finding.get("port") or 0)
        if not host or not port:
            continue

        kind = _runtime_kind(port, str(finding.get("kind") or ""))
        node_id = f"{host}:{port}"
        seen_ids.add(node_id)

        models = _models_from_finding(finding)
        truth = "LIVE" if finding.get("open", True) else "DEGRADED"

        if port not in (1234, 11434):
            # Non-model ports are observed services by default.
            # They become unexpected exposure only when the same host also has a verified
            # model-serving runtime or the port is explicitly promoted by policy.
            model_hosts = {
                str(item.get("host") or item.get("ip") or "").strip()
                for item in findings
                if isinstance(item, dict)
                and int(item.get("port") or 0) in (1234, 11434)
                and bool(item.get("open", True))
            }

            if host in model_hosts:
                truth = "UNEXPECTED_EXPOSURE"
                alert = {
                    "id": f"unexpected-{node_id}",
                    "severity": "MEDIUM",
                    "family": "discovery",
                    "message": f"Verified model host exposed additional port: {node_id}",
                    "node_id": node_id,
                    "source": "/api/v1/discovery/ai-runtimes",
                    "created_at": generated_at,
                }
                alerts.append(alert)
                unexpected_exposures.append(alert)
            else:
                truth = "OBSERVED_SERVICE"

        nodes.append(
            {
                "id": node_id,
                "label": f"{kind} {host}:{port}",
                "kind": kind,
                "ip": host,
                "port": port,
                "reachable": bool(finding.get("open", True)),
                "truth": truth,
                "source": "/api/v1/discovery/ai-runtimes",
                "last_scanned": scan_generated_at or generated_at,
                "model_count": len(models),
                "models": models,
            }
        )

    for expected in EXPECTED_AI_RUNTIMES:
        node_id = expected["id"]
        if node_id in seen_ids:
            continue

        missing = {
            "id": node_id,
            "label": expected["label"],
            "kind": expected["kind"],
            "ip": expected["ip"],
            "port": expected["port"],
            "reachable": False,
            "truth": "MISSING_FROM_SCAN",
            "source": "/api/v1/discovery/ai-runtimes",
            "last_scanned": scan_generated_at or generated_at,
            "model_count": 0,
            "models": [],
            "expected": True,
        }
        nodes.append(missing)
        missing_assets.append(missing)

    truth = "LIVE"
    if scan.get("missing_scan_artifact"):
        truth = "EMPTY"
    if scan.get("scan_read_error"):
        truth = "ERROR"
    if missing_assets or unexpected_exposures:
        truth = "DEGRADED"

    return {
        "truth": truth,
        "generated_at": generated_at,
        "source": [
            "/api/v1/discovery/ai-runtimes",
            "/api/v1/detections/events",
            "/api/v1/runtime/local-supervisor/status",
        ],
        "scan_generated_at": scan_generated_at,
        "nodes": nodes,
        "edges": [],
        "alerts": alerts,
        "missing_assets": missing_assets,
        "unexpected_exposures": unexpected_exposures,
        "summary": {
            "node_count": len(nodes),
            "live_runtimes": len([n for n in nodes if n.get("truth") == "LIVE"]),
            "missing_assets": len(missing_assets),
            "unexpected_exposures": len(unexpected_exposures),
            "lmstudio_hosts": sorted(
                [n["id"] for n in nodes if n.get("kind") == "LM_STUDIO" and n.get("reachable")]
            ),
            "ollama_hosts": sorted(
                [n["id"] for n in nodes if n.get("kind") == "OLLAMA" and n.get("reachable")]
            ),
        },
    }
