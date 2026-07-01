from __future__ import annotations
import concurrent.futures
import json
import socket
import time
from pathlib import Path
from urllib.request import Request, urlopen

SUBNET = "10.0.0."
PORTS = {
    1234: "lmstudio_openai_compatible",
    11434: "ollama",
    8000: "hoch_fastapi",
    8080: "open_webui_or_local_api",
    7860: "gradio_or_local_ai_ui",
}
OUT = Path("artifacts/network_discovery")
OUT.mkdir(parents=True, exist_ok=True)

def tcp_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def fetch_json(url: str, timeout: float = 1.5):
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except Exception as exc:
        return {"_error": str(exc)}

def probe_host(host: str):
    findings = []
    for port, kind in PORTS.items():
        if not tcp_open(host, port):
            continue
        item = {
            "host": host,
            "port": port,
            "kind": kind,
            "open": True,
            "models": [],
            "raw": {},
        }
        if port == 11434:
            data = fetch_json(f"http://{host}:11434/api/tags")
            item["raw"]["api_tags"] = data
            models = data.get("models", []) if isinstance(data, dict) else []
            item["models"] = [
                {
                    "name": m.get("name"),
                    "model": m.get("model"),
                    "modified_at": m.get("modified_at"),
                    "size": m.get("size"),
                    "digest": m.get("digest"),
                }
                for m in models
                if isinstance(m, dict)
            ]
        if port == 1234:
            data = fetch_json(f"http://{host}:1234/v1/models")
            item["raw"]["v1_models"] = data
            models = data.get("data", []) if isinstance(data, dict) else []
            item["models"] = [
                {
                    "id": m.get("id"),
                    "object": m.get("object"),
                    "owned_by": m.get("owned_by"),
                }
                for m in models
                if isinstance(m, dict)
            ]
        if port == 8000:
            item["raw"]["health"] = fetch_json(f"http://{host}:8000/health")
        findings.append(item)
    return findings

def main():
    hosts = ["127.0.0.1"] + [f"{SUBNET}{i}" for i in range(1, 255)]
    started = time.time()
    all_findings = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=96) as ex:
        for findings in ex.map(probe_host, hosts):
            all_findings.extend(findings)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subnet": "10.0.0.0/24",
        "duration_seconds": round(time.time() - started, 2),
        "findings": all_findings,
        "summary": {
            "open_services": len(all_findings),
            "ollama_hosts": sorted({f["host"] for f in all_findings if f["port"] == 11434}),
            "lmstudio_hosts": sorted({f["host"] for f in all_findings if f["port"] == 1234}),
            "hoch_fastapi_hosts": sorted({f["host"] for f in all_findings if f["port"] == 8000}),
            "total_models_seen": sum(len(f.get("models", [])) for f in all_findings),
        },
    }
    out_json = OUT / "ai_runtime_scan.json"
    out_md = OUT / "ai_runtime_scan.md"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# AI Runtime Network Scan",
        "",
        f"Generated: {report['generated_at']}",
        f"Subnet: {report['subnet']}",
        f"Open services: {report['summary']['open_services']}",
        f"LM Studio hosts: {', '.join(report['summary']['lmstudio_hosts']) or 'none'}",
        f"Ollama hosts: {', '.join(report['summary']['ollama_hosts']) or 'none'}",
        f"HOCH FastAPI hosts: {', '.join(report['summary']['hoch_fastapi_hosts']) or 'none'}",
        f"Models seen: {report['summary']['total_models_seen']}",
        "",
        "## Findings",
        "",
    ]
    for f in all_findings:
        lines.append(f"### {f['host']}:{f['port']} — {f['kind']}")
        if f.get("models"):
            for m in f["models"]:
                lines.append(f"- `{m.get('name') or m.get('id') or m.get('model')}`")
        else:
            lines.append("- No model list returned or endpoint not model-serving.")
        lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))

if __name__ == "__main__":
    main()
