from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SCAN_PATH = Path("artifacts/qa/device_swarm/latest_device_swarm_scan.json")
CHAT_LOG_PATH = Path("artifacts/qa/device_swarm/agent_chat_log.jsonl")

DEFAULT_PORTS = [1234, 11434, 8000, 8080, 3000, 5173, 7860, 5000, 5001, 8188, 8888, 9090]
MODEL_PORTS = {1234: "LM_STUDIO", 11434: "OLLAMA"}

EXPECTED_DEVICES = [
    {"name": "Control Plane MacBook", "ip": "10.0.0.6", "role": "control-plane"},
    {"name": "NEO / HOCH-MESH MacBook", "ip": "10.0.0.8", "role": "model-runtime"},
    {"name": "Possible WebUI Node 10.0.0.22", "ip": "10.0.0.22", "role": "service-node"},
    {"name": "Possible WebUI Node 10.0.0.26", "ip": "10.0.0.26", "role": "service-node"},
    {"name": "Ollama Candidate 10.0.0.115", "ip": "10.0.0.115", "role": "model-runtime"},
    {"name": "Ollama Model Host 10.0.0.241", "ip": "10.0.0.241", "role": "model-runtime"},
    {"name": "iPhone / Wi-Fi Device Candidate", "ip": None, "role": "mobile-device"},
    {"name": "iPad / Tablet Candidate", "ip": None, "role": "mobile-device"},
    {"name": "TV / Media Device Candidate", "ip": None, "role": "display-device"},
    {"name": "Printer / IoT / Home Device Candidate", "ip": None, "role": "iot-device"},
]


def now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_cmd(args: List[str], timeout: int = 5) -> str:
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL, timeout=timeout).decode("utf-8", "ignore")
    except Exception:
        return ""


def parse_arp() -> List[Dict[str, Any]]:
    text = run_cmd(["arp", "-a"], timeout=5)
    devices: List[Dict[str, Any]] = []

    for line in text.splitlines():
        ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
        mac_match = re.search(r" at ([0-9a-fA-F:]+) ", line)
        if not ip_match:
            continue

        name = line.split(" ")[0].strip() or "unknown"
        ip = ip_match.group(1)
        mac = mac_match.group(1).lower() if mac_match else None

        devices.append({
            "ip": ip,
            "name": name,
            "mac": mac,
            "source": "arp -a",
        })

    return devices


def reverse_dns(ip: str) -> Optional[str]:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except Exception:
        return None


def http_get_json(url: str, timeout: float = 1.25) -> Optional[Any]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read(4_000_000)
            return json.loads(raw.decode("utf-8", "ignore"))
    except Exception:
        return None


def tcp_open(ip: str, port: int, timeout: float = 0.45) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def probe_lmstudio(ip: str) -> Dict[str, Any]:
    data = http_get_json(f"http://{ip}:1234/v1/models", timeout=1.75)
    models: List[str] = []
    if isinstance(data, dict):
        for item in data.get("data", []):
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("name")
                if model_id:
                    models.append(str(model_id))
    return {
        "runtime": "LM_STUDIO",
        "port": 1234,
        "reachable": bool(data is not None),
        "models": sorted(set(models)),
        "proof_endpoint": f"http://{ip}:1234/v1/models",
        "truth_state": "LIVE" if data is not None else "MISSING_FROM_SCAN",
    }


def probe_ollama(ip: str) -> Dict[str, Any]:
    data = http_get_json(f"http://{ip}:11434/api/tags", timeout=1.75)
    models: List[str] = []
    if isinstance(data, dict):
        for item in data.get("models", []):
            if isinstance(item, dict):
                name = item.get("name") or item.get("model")
                if name:
                    models.append(str(name))
    return {
        "runtime": "OLLAMA",
        "port": 11434,
        "reachable": bool(data is not None),
        "models": sorted(set(models)),
        "proof_endpoint": f"http://{ip}:11434/api/tags",
        "truth_state": "LIVE" if data is not None else "MISSING_FROM_SCAN",
    }


def classify_device(name: str, ip: str, open_ports: List[int], runtimes: List[Dict[str, Any]]) -> str:
    text = f"{name} {ip}".lower()
    if any(rt.get("reachable") for rt in runtimes):
        return "AI_MODEL_RUNTIME"
    if 8000 in open_ports:
        return "HOCH_CONTROL_OR_API"
    if 8080 in open_ports or 3000 in open_ports or 5173 in open_ports:
        return "WEB_UI_OR_LOCAL_SERVICE"
    if "iphone" in text:
        return "IPHONE"
    if "ipad" in text:
        return "IPAD"
    if "apple" in text or "macbook" in text or "imac" in text:
        return "APPLE_COMPUTE"
    if "tv" in text or "roku" in text or "samsung" in text or "lg" in text:
        return "TV_MEDIA"
    return "WIFI_DEVICE"


def score_device(device: Dict[str, Any]) -> int:
    score = 0
    if device.get("runtime_count", 0):
        score += 1000
    if device.get("open_ports"):
        score += 100
    if device.get("ip") in {"10.0.0.6", "10.0.0.8", "10.0.0.115", "10.0.0.241"}:
        score += 50
    if device.get("name") and device.get("name") != "?":
        score += 10
    return score


def probe_device(base: Dict[str, Any]) -> Dict[str, Any]:
    ip = str(base.get("ip"))
    name = base.get("name") or reverse_dns(ip) or "unknown"
    rdns = reverse_dns(ip)

    open_ports = []
    for port in DEFAULT_PORTS:
        if tcp_open(ip, port):
            open_ports.append(port)

    lm = probe_lmstudio(ip)
    ol = probe_ollama(ip)
    runtimes = [rt for rt in [lm, ol] if rt["reachable"] or ip in {"10.0.0.8", "127.0.0.1"}]

    model_names: List[str] = []
    for rt in runtimes:
        model_names.extend(rt.get("models", []))

    device_type = classify_device(rdns or name, ip, open_ports, runtimes)
    truth_state = "LIVE" if open_ports or any(rt.get("reachable") for rt in runtimes) else "OBSERVED_NO_AI_RUNTIME"

    agents = []
    if any(rt.get("reachable") for rt in runtimes):
        agents.extend([
            "Mission Commander",
            "Model Router",
            "QA Auditor",
            "Code Solver",
            "Cyber Commoner",
            "ConMon Watcher",
        ])
    elif open_ports:
        agents.extend(["Asset Scout", "Footprint Sentinel", "Service Classifier"])
    else:
        agents.extend(["Asset Scout"])

    return {
        "id": ip,
        "ip": ip,
        "name": rdns or name,
        "mac": base.get("mac"),
        "device_type": device_type,
        "truth_state": truth_state,
        "source": base.get("source", "expected/scan"),
        "open_ports": open_ports,
        "runtime_count": len([rt for rt in runtimes if rt.get("reachable")]),
        "runtimes": runtimes,
        "models": sorted(set(model_names)),
        "model_count": len(set(model_names)),
        "agents_available": sorted(set(agents)),
        "last_scanned": now_z(),
    }


def build_candidates() -> List[Dict[str, Any]]:
    by_ip: Dict[str, Dict[str, Any]] = {}

    for item in parse_arp():
        ip = item.get("ip")
        if ip:
            by_ip[ip] = item

    for item in EXPECTED_DEVICES:
        ip = item.get("ip")
        if ip and ip not in by_ip:
            by_ip[ip] = {
                "ip": ip,
                "name": item["name"],
                "mac": None,
                "source": "expected_devices",
            }

    return list(by_ip.values())


def scan_device_swarm(limit: int = 10) -> Dict[str, Any]:
    candidates = build_candidates()
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=48) as pool:
        futures = [pool.submit(probe_device, item) for item in candidates]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({
                    "id": f"error-{len(results)}",
                    "truth_state": "SCAN_ERROR",
                    "error": str(exc),
                    "last_scanned": now_z(),
                })

    results = sorted(results, key=score_device, reverse=True)

    named: List[Dict[str, Any]] = []
    seen = set()
    for item in results:
        if item.get("ip") in seen:
            continue
        seen.add(item.get("ip"))
        named.append(item)
        if len(named) >= limit:
            break

    while len(named) < limit:
        placeholder = EXPECTED_DEVICES[len(named) % len(EXPECTED_DEVICES)]
        named.append({
            "id": f"expected-{len(named)+1}",
            "ip": placeholder.get("ip") or "UNKNOWN",
            "name": placeholder["name"],
            "mac": None,
            "device_type": placeholder["role"].upper(),
            "truth_state": "MISSING_FROM_SCAN",
            "source": "expected_placeholder",
            "open_ports": [],
            "runtime_count": 0,
            "runtimes": [],
            "models": [],
            "model_count": 0,
            "agents_available": ["Asset Scout"],
            "last_scanned": now_z(),
        })

    summary = {
        "device_count": len(named),
        "model_runtime_count": len([d for d in named if d.get("runtime_count", 0) > 0]),
        "model_count": sum(int(d.get("model_count", 0)) for d in named),
        "live_devices": len([d for d in named if d.get("truth_state") == "LIVE"]),
        "missing_devices": len([d for d in named if d.get("truth_state") == "MISSING_FROM_SCAN"]),
        "agents_available": sorted(set(a for d in named for a in d.get("agents_available", []))),
    }

    payload = {
        "schema": "hoch.device_swarm.prototype.v1",
        "truth": "LIVE",
        "generated_at": now_z(),
        "source": [
            "arp -a",
            "tcp probe",
            "LM Studio /v1/models",
            "Ollama /api/tags",
            "expected device registry",
        ],
        "summary": summary,
        "devices": named,
    }

    SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCAN_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def get_cached_or_scan(limit: int = 10, max_age_seconds: int = 90) -> Dict[str, Any]:
    if SCAN_PATH.exists():
        try:
            data = json.loads(SCAN_PATH.read_text(encoding="utf-8"))
            generated_at = data.get("generated_at")
            if generated_at:
                return data
        except Exception:
            pass
    return scan_device_swarm(limit=limit)


def agent_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt", "")).strip()
    target = str(payload.get("target", "swarm")).strip()
    agent = str(payload.get("agent", "Mission Commander")).strip()

    if not prompt:
        return {
            "truth": "REJECTED",
            "reason": "Prompt is empty.",
            "created_at": now_z(),
        }

    scan = get_cached_or_scan(limit=10)
    devices = scan.get("devices", [])

    response = {
        "truth": "STAGED",
        "created_at": now_z(),
        "agent": agent,
        "target": target,
        "prompt": prompt,
        "action_plan": [
            "Map prompt to candidate agent roles.",
            "Select target device by runtime proof and role.",
            "Require approval for high-risk write, scan, external, or privileged operations.",
            "Execute read-only discovery first.",
            "Emit evidence artifact and update device/agent truth state.",
        ],
        "available_devices": [
            {
                "ip": d.get("ip"),
                "name": d.get("name"),
                "truth_state": d.get("truth_state"),
                "models": d.get("models", []),
                "agents_available": d.get("agents_available", []),
            }
            for d in devices
        ],
        "execution_status": "NOT_EXECUTED_REQUIRES_OPERATOR_APPROVAL",
    }

    CHAT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHAT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(response) + "\n")

    return response
