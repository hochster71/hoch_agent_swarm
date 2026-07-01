import json
import socket
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

def ping_host(ip: str) -> bool:
    try:
        # Run ping command with 1 second timeout and 2 packets
        res = subprocess.run(["ping", "-c", "2", "-t", "2", ip], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def check_port(ip: str, port: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=1.5):
            return True
    except Exception:
        return False

def http_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as r:
            body = r.read().decode("utf-8", errors="replace")
            return True, json.loads(body)
    except Exception as exc:
        return False, {"error": str(exc)}

def main():
    config_path = Path("config/known_assets.json")
    if not config_path.exists():
        print(json.dumps({"error": "config/known_assets.json not found"}))
        return

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assets = data.get("assets", [])

    results = []
    summary = {
        "total_assets": len(assets),
        "online_assets": 0,
        "offline_assets": 0,
        "lmstudio_runtimes_active": 0
    }

    # Ports we want to probe on each asset
    probe_ports = [1234, 8000, 8080, 11434, 5000]

    for asset in assets:
        name = asset.get("name")
        ip = asset.get("ip")
        role = asset.get("role")
        
        ping_ok = ping_host(ip)
        open_ports = []
        for port in probe_ports:
            if check_port(ip, port):
                open_ports.append(port)

        services = {}
        
        # Checking if 1234 is open for LM Studio API checks
        lmstudio_ok, lmstudio_data = (False, None)
        lmstudio_native_ok, lmstudio_native_data = (False, None)
        if 1234 in open_ports:
            # LM Studio native v1 REST API
            lmstudio_native_ok, lmstudio_native_data = http_json(f"http://{ip}:1234/api/v1/models")
            services["lmstudio_api_v1_models"] = {
                "reachable": lmstudio_native_ok,
                "model_count": len(lmstudio_native_data.get("data", [])) if isinstance(lmstudio_native_data, dict) else 0,
                "raw_keys": sorted(list(lmstudio_native_data.keys())) if isinstance(lmstudio_native_data, dict) else []
            }
            # OpenAI-compatible endpoint
            lmstudio_ok, lmstudio_data = http_json(f"http://{ip}:1234/v1/models")
            services["openai_compatible_v1_models"] = {
                "reachable": lmstudio_ok,
                "model_count": len(lmstudio_data.get("data", [])) if isinstance(lmstudio_data, dict) else 0,
                "raw_keys": sorted(list(lmstudio_data.keys())) if isinstance(lmstudio_data, dict) else []
            }
            lmstudio_ok = lmstudio_ok or lmstudio_native_ok

        # Determine status
        status = "OFFLINE"
        if ping_ok:
            status = "ONLINE"
            summary["online_assets"] += 1
        else:
            summary["offline_assets"] += 1

        if lmstudio_ok:
            summary["lmstudio_runtimes_active"] += 1

        results.append({
            "name": name,
            "ip": ip,
            "role": role,
            "ping": ping_ok,
            "open_ports": open_ports,
            "services": services,
            "status": status
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "results": results,
        "summary": summary
    }

    report_path = Path("artifacts/qa/known_assets/known_asset_probe_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print JSON output to stdout
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
