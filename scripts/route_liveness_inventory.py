#!/usr/bin/env python3
import urllib.request
import urllib.error
import json
import sys
import os

def inventory_routes():
    print("==================================================")
    print("P0c: Running Route Liveness Inventory")
    print("==================================================")
    
    # 1. Fetch openapi.json
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/openapi.json") as resp:
            openapi = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Failed to fetch openapi.json: {e}")
        sys.exit(1)
        
    paths = openapi.get("paths", {})
    get_routes = []
    
    for path, methods in paths.items():
        if "get" in methods:
            get_routes.append(path)
            
    print(f"Found {len(get_routes)} GET endpoints in schema.")
    
    results = []
    
    # Pre-defined substitutions for path parameters
    dummy_params = {
        "mission_id": "mission-p0a-fury-bce87dbb",
        "prompt_id": "task_history",
        "formal_preview_id": "preview-001",
        "model_provider_id": "openai",
        "attestation_bundle_id": "bundle-001",
        "candidate_packet_id": "packet-001",
        "seal_dry_run_id": "dryrun-001",
        "incident_id": "incident-001",
        "skill_id": "skill-001",
        "team_id": "qa-team-1"
    }
    
    for path in sorted(get_routes):
        url_path = path
        # Replace parameters
        for param, val in dummy_params.items():
            url_path = url_path.replace(f"{{{param}}}", val)
            
        # Avoid blocking queries
        if "websocket" in url_path.lower():
            continue
            
        full_url = f"http://127.0.0.1:8000{url_path}"
        status_code = None
        classification = "LIVE"
        response_snippet = ""
        
        try:
            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                status_code = resp.status
                body = resp.read().decode("utf-8", errors="ignore")
                response_snippet = body[:100]
        except urllib.error.HTTPError as e:
            status_code = e.code
            response_snippet = e.read().decode("utf-8", errors="ignore")[:100]
        except Exception as e:
            status_code = "ERR"
            response_snippet = str(e)
            
        # Classify
        if status_code == "ERR" or status_code == 500:
            classification = "ERROR"
        elif "mock" in path.lower() or "stub" in path.lower() or "mock" in response_snippet.lower():
            classification = "STUB"
        else:
            classification = "LIVE"
            
        results.append({
            "path": path,
            "substituted_path": url_path,
            "status": status_code,
            "classification": classification,
            "snippet": response_snippet
        })
        print(f"[{classification}] GET {url_path} -> Status {status_code}")
        
    # Write report
    report_path = "docs/evidence/route_liveness_inventory.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# P0c Route Liveness Inventory Report\n\n")
        f.write(f"Executed at: {datetime_str()}\n\n")
        f.write("## Summary\n\n")
        
        live_count = len([r for r in results if r["classification"] == "LIVE"])
        stub_count = len([r for r in results if r["classification"] == "STUB"])
        err_count = len([r for r in results if r["classification"] == "ERROR"])
        
        f.write(f"- **Total GET Routes Checked**: {len(results)}\n")
        f.write(f"- **LIVE Routes**: {live_count}\n")
        f.write(f"- **STUB Routes**: {stub_count}\n")
        f.write(f"- **ERROR Routes**: {err_count}\n\n")
        
        f.write("## Inventory Table\n\n")
        f.write("| Path | Substituted Path | Status Code | Classification |\n")
        f.write("| --- | --- | --- | --- |\n")
        for r in results:
            f.write(f"| `{r['path']}` | `{r['substituted_path']}` | `{r['status']}` | **{r['classification']}** |\n")
            
    print(f"\n🟢 Route inventory completed. Report written to {report_path}")

def datetime_str():
    import datetime
    return datetime.datetime.utcnow().isoformat() + "Z"

if __name__ == "__main__":
    inventory_routes()
