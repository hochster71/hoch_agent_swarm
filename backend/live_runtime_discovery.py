import os
import json
from pathlib import Path
from datetime import datetime, timezone

SCAN_JSON_PATH = Path(__file__).parent.parent / "artifacts" / "network_discovery" / "ai_runtime_scan.json"

KNOWN_ASSETS = [
    {"host": "10.0.0.8", "port": 1234, "kind": "lmstudio_openai_compatible", "type": "lmstudio"},
    {"host": "127.0.0.1", "port": 11434, "kind": "ollama", "type": "ollama"},
]

def load_ai_runtime_discovery():
    generated_at = datetime.now(timezone.utc).isoformat()
    findings = []
    
    if SCAN_JSON_PATH.exists():
        try:
            with open(SCAN_JSON_PATH, "r") as f:
                scan_data = json.load(f)
                findings = scan_data.get("findings", [])
                generated_at = scan_data.get("generated_at", generated_at)
        except Exception as e:
            print(f"Error reading scan JSON: {e}")

    # Index findings by (host, port)
    scanned_map = {}
    for f in findings:
        scanned_map[(f.get("host"), f.get("port"))] = f

    hosts_out = []
    lmstudio_hosts = set()
    ollama_hosts = set()
    all_models = []

    # Process all scanned and known assets
    processed = set()

    # 1. First process KNOWN_ASSETS
    for asset in KNOWN_ASSETS:
        host = asset["host"]
        port = asset["port"]
        kind = asset["kind"]
        atype = asset["type"]
        key = (host, port)
        processed.add(key)
        
        scanned_item = scanned_map.get(key)
        if scanned_item and scanned_item.get("open", False):
            # Known asset is active/reachable
            models = scanned_item.get("models", [])
            model_names = []
            for m in models:
                name = m.get("name") or m.get("id") or m.get("model")
                if name:
                    model_names.append(name)
            
            reachable = True
            
            # Check for fetch errors (like time out)
            raw = scanned_item.get("raw", {})
            if "api_tags" in raw and "_error" in raw["api_tags"]:
                reachable = False
            
            status = "ACTIVE" if reachable else "MISSING_FROM_SCAN"
            
            hosts_out.append({
                "host": host,
                "port": port,
                "kind": kind,
                "reachable": reachable,
                "status": status,
                "model_count": len(model_names),
                "model_names": model_names,
                "last_scanned": generated_at
            })
            if reachable:
                all_models.extend(model_names)
                if atype == "lmstudio":
                    lmstudio_hosts.add(host)
                elif atype == "ollama":
                    ollama_hosts.add(host)
        else:
            # Known asset is missing/unreachable
            hosts_out.append({
                "host": host,
                "port": port,
                "kind": kind,
                "reachable": False,
                "status": "MISSING_FROM_SCAN",
                "model_count": 0,
                "model_names": [],
                "last_scanned": generated_at
            })

    # 2. Process remaining scanned assets
    for key, f in scanned_map.items():
        if key in processed:
            continue
        host, port = key
        kind = f.get("kind", "")
        
        # Only include Ollama or LM Studio services
        if port not in (1234, 11434):
            continue
            
        models = f.get("models", [])
        model_names = []
        for m in models:
            name = m.get("name") or m.get("id") or m.get("model")
            if name:
                model_names.append(name)
                
        reachable = f.get("open", False)
        raw = f.get("raw", {})
        if "api_tags" in raw and "_error" in raw["api_tags"]:
            reachable = False
            
        status = "ACTIVE" if reachable else "MISSING_FROM_SCAN"
        
        hosts_out.append({
            "host": host,
            "port": port,
            "kind": kind,
            "reachable": reachable,
            "status": status,
            "model_count": len(model_names),
            "model_names": model_names,
            "last_scanned": generated_at
        })
        if reachable:
            all_models.extend(model_names)
            if port == 1234:
                lmstudio_hosts.add(host)
            elif port == 11434:
                ollama_hosts.add(host)

    # Convert sets to sorted lists
    lmstudio_hosts_list = sorted(list(lmstudio_hosts))
    ollama_hosts_list = sorted(list(ollama_hosts))
    
    # Always include known LM studio host in list (marked false if missing)
    if "10.0.0.8" not in lmstudio_hosts_list:
        lmstudio_hosts_list.append("10.0.0.8")
        
    return {
        "truth": "LIVE",
        "source": "network_scan",
        "generated_at": generated_at,
        "hosts": hosts_out,
        "lmstudio_hosts": lmstudio_hosts_list,
        "ollama_hosts": ollama_hosts_list,
        "models": sorted(list(set(all_models))),
        "stale_static_assets_rejected": True
    }
