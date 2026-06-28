from __future__ import annotations

import json
import os
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


OUT_PATH = Path("artifacts/qa/network_discovery/ssh_model_inventory.json")

# Optional override:
# export HOCH_SSH_HOSTS="michael@10.0.0.8,hoch@10.0.0.115,hoch@10.0.0.241"
DEFAULT_HOSTS = [
    "10.0.0.8",
    "10.0.0.115",
    "10.0.0.241",
    "10.0.0.6",
    "10.0.0.22",
    "10.0.0.26",
]


REMOTE_SCRIPT = r'''
set +e

echo "===HOCH_HOSTNAME==="
hostname 2>/dev/null || scutil --get ComputerName 2>/dev/null || echo unknown

echo "===HOCH_UNAME==="
uname -a 2>/dev/null || true

echo "===HOCH_IPS==="
if command -v ip >/dev/null 2>&1; then ip -o -4 addr show 2>/dev/null; fi
if command -v ifconfig >/dev/null 2>&1; then ifconfig 2>/dev/null | grep "inet " || true; fi

echo "===HOCH_PORTS==="
if command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E "11434|1234|8000|8080|5000|5001|3000|5173|7860|8188|8888" || true
fi
if command -v ss >/dev/null 2>&1; then
  ss -ltnp 2>/dev/null | grep -E "11434|1234|8000|8080|5000|5001|3000|5173|7860|8188|8888" || true
fi
if command -v netstat >/dev/null 2>&1; then
  netstat -an 2>/dev/null | grep -E "11434|1234|8000|8080|5000|5001|3000|5173|7860|8188|8888" || true
fi

echo "===HOCH_OLLAMA_WHICH==="
command -v ollama 2>/dev/null || true

echo "===HOCH_OLLAMA_LIST==="
ollama list 2>/dev/null || true

echo "===HOCH_OLLAMA_TAGS==="
curl -s --max-time 3 http://127.0.0.1:11434/api/tags 2>/dev/null || true

echo "===HOCH_LMSTUDIO_MODELS==="
curl -s --max-time 3 http://127.0.0.1:1234/v1/models 2>/dev/null || true

echo "===HOCH_STORAGE==="
df -h 2>/dev/null || true

echo "===HOCH_BACKUP_HINTS==="
ls -la ~/ 2>/dev/null | grep -Ei "backup|backups|Time Machine|timemachine|ollama|models|hoch|agent" || true
find ~/ -maxdepth 3 -iname "*backup*" -o -iname "*ollama*" -o -iname "*models*" 2>/dev/null | head -n 80 || true
'''


def now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_hosts() -> List[str]:
    raw = os.getenv("HOCH_SSH_HOSTS", "").strip()
    if raw:
        return [h.strip() for h in raw.split(",") if h.strip()]

    ssh_config = Path.home() / ".ssh" / "config"
    hosts: List[str] = []
    if ssh_config.exists():
        for line in ssh_config.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line.lower().startswith("host "):
                continue
            for h in line.split()[1:]:
                if "*" not in h and "?" not in h and h not in {"github.com"}:
                    hosts.append(h)

    # Preserve defaults after config aliases.
    for h in DEFAULT_HOSTS:
        if h not in hosts:
            hosts.append(h)

    return hosts


def run_ssh(host: str) -> Dict[str, Any]:
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=accept-new",
        host,
        "bash",
        "-lc",
        shlex.quote(REMOTE_SCRIPT),
    ]

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=35)
        out = proc.stdout or ""
        err = proc.stderr or ""
        ok = proc.returncode == 0
    except Exception as exc:
        return {
            "host": host,
            "reachable": False,
            "error": str(exc),
            "models": [],
            "model_count": 0,
            "ports": [],
            "storage": [],
            "raw": "",
        }

    sections = parse_sections(out)
    models = parse_models(sections)
    ports = parse_ports(sections)
    storage = parse_storage(sections)

    return {
        "host": host,
        "reachable": ok,
        "returncode": proc.returncode,
        "stderr": err[-1000:],
        "hostname": first_line(sections.get("HOCH_HOSTNAME", "")),
        "uname": first_line(sections.get("HOCH_UNAME", "")),
        "models": models,
        "model_count": len(models),
        "ports": ports,
        "ollama_cli_present": bool(sections.get("HOCH_OLLAMA_WHICH", "").strip()),
        "ollama_tags_raw_present": bool(sections.get("HOCH_OLLAMA_TAGS", "").strip().startswith("{")),
        "lmstudio_models_raw_present": bool(sections.get("HOCH_LMSTUDIO_MODELS", "").strip().startswith("{")),
        "storage": storage,
        "backup_hints": sections.get("HOCH_BACKUP_HINTS", "").splitlines()[:80],
        "raw_sections": sections,
    }


def parse_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("===HOCH_") and line.endswith("==="):
            current = line.strip("=").strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def first_line(text: str) -> str:
    return next((x for x in text.splitlines() if x.strip()), "")


def parse_models(sections: Dict[str, str]) -> List[str]:
    found = set()

    # ollama list format: NAME ID SIZE MODIFIED
    for line in sections.get("HOCH_OLLAMA_LIST", "").splitlines():
        line = line.strip()
        if not line or line.lower().startswith("name "):
            continue
        first = line.split()[0]
        if ":" in first:
            found.add(first)

    # /api/tags JSON
    raw = sections.get("HOCH_OLLAMA_TAGS", "").strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            for item in data.get("models", []):
                if isinstance(item, dict):
                    name = item.get("name") or item.get("model")
                    if name:
                        found.add(str(name))
        except Exception:
            pass

    raw = sections.get("HOCH_LMSTUDIO_MODELS", "").strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            for item in data.get("data", []):
                if isinstance(item, dict):
                    name = item.get("id") or item.get("name")
                    if name:
                        found.add(str(name))
        except Exception:
            pass

    return sorted(found)


def parse_ports(sections: Dict[str, str]) -> List[int]:
    text = "\n".join([
        sections.get("HOCH_PORTS", ""),
        sections.get("HOCH_OLLAMA_TAGS", ""),
        sections.get("HOCH_LMSTUDIO_MODELS", ""),
    ])
    ports = set()
    for p in [11434, 1234, 8000, 8080, 5000, 5001, 3000, 5173, 7860, 8188, 8888]:
        if str(p) in text:
            ports.add(p)
    return sorted(ports)


def parse_storage(sections: Dict[str, str]) -> List[Dict[str, str]]:
    rows = []
    for line in sections.get("HOCH_STORAGE", "").splitlines():
        parts = line.split()
        if len(parts) >= 6 and not parts[0].lower().startswith("filesystem"):
            rows.append({
                "filesystem": parts[0],
                "size": parts[1],
                "used": parts[2],
                "avail": parts[3],
                "capacity": parts[4],
                "mount": " ".join(parts[5:]),
            })
    return rows


def collect_ssh_model_inventory() -> Dict[str, Any]:
    hosts = get_hosts()
    results = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = {pool.submit(run_ssh, h): h for h in hosts}
        for fut in as_completed(futures):
            results.append(fut.result())

    reachable = [r for r in results if r.get("reachable")]
    model_hosts = [r for r in reachable if r.get("model_count", 0) > 0]

    payload = {
        "schema": "hoch.ssh_model_inventory.v1",
        "generated_at": now_z(),
        "source": "ssh",
        "summary": {
            "hosts_configured": len(hosts),
            "ssh_reachable": len(reachable),
            "model_hosts": len(model_hosts),
            "models_total": sum(r.get("model_count", 0) for r in model_hosts),
        },
        "hosts": sorted(results, key=lambda r: (not r.get("reachable"), r.get("host", ""))),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(collect_ssh_model_inventory(), indent=2))
