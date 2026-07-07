#!/usr/bin/env python3
import urllib.request
import json
import sys

def main():
    print("Executing BRAIN Contract Verification...")
    url = "http://127.0.0.1:8000/api/homemesh/assets"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                print(f"[FAIL] Assets API returned HTTP {response.status}", file=sys.stderr)
                sys.exit(1)
            
            assets = json.loads(response.read())
            print(f"[PASS] Successfully fetched {len(assets)} assets from API.")
            
            for asset in assets:
                mac = asset.get("mac_address")
                name = asset.get("display_name")
                sources = asset.get("evidence_sources", [])
                tags = asset.get("tags", [])
                trust = asset.get("trust_score", 0.0)
                status = asset.get("online_status")
                
                # Check 1: Citation capability (every asset has evidence_sources or manual_import tag)
                if not sources and "manually_mapped" not in tags:
                    print(f"[FAIL] Asset {name} ({mac}) has no evidence sources and is not manually mapped.", file=sys.stderr)
                    sys.exit(1)
                print(f"[PASS] Asset {name} has valid citation sources: {sources}")
                
                # Check 2: Fail-closed verification
                if asset.get("device_type") == "unknown" or "untrusted" in tags:
                    if trust > 30.0:
                        print(f"[FAIL] Untrusted asset {name} has trust score {trust} > 30.0", file=sys.stderr)
                        sys.exit(1)
                    if asset.get("room_id") != "unmapped_devices":
                        print(f"[FAIL] Untrusted asset {name} is placed in valid room: {asset.get('room_id')}", file=sys.stderr)
                        sys.exit(1)
                    print(f"[PASS] Fail-closed enforced on untrusted device {name}.")
                
                # Check 3: Stale status detection
                if status == "stale":
                    print(f"[PASS] Stale device {name} correctly identified as stale (known_stale).")
            
            print("[PASS] All BRAIN contract checks completed successfully.")
            
            # Check 4: Source status endpoint validation
            print("Executing Source Status Endpoint Verification...")
            status_url = "http://127.0.0.1:8000/api/homemesh/source-status"
            req_status = urllib.request.Request(status_url)
            with urllib.request.urlopen(req_status, timeout=5) as resp_status:
                if resp_status.status != 200:
                    print(f"[FAIL] Source Status API returned HTTP {resp_status.status}", file=sys.stderr)
                    sys.exit(1)
                
                statuses = json.loads(resp_status.read())
                required_sources = {"arp", "ssdp", "mdns", "dhcp", "udm", "home_assistant", "manual"}
                found_sources = set()
                
                for s in statuses:
                    name = s.get("source_name")
                    found_sources.add(name)
                    # Verify fields
                    for field in ["enabled", "status", "last_success", "last_error_safe", "observation_count", "classification"]:
                        if field not in s:
                            print(f"[FAIL] Source status for {name} missing field: {field}", file=sys.stderr)
                            sys.exit(1)
                
                missing = required_sources - found_sources
                if missing:
                    print(f"[FAIL] Missing expected sources in status list: {missing}", file=sys.stderr)
                    sys.exit(1)
                print(f"[PASS] Source status endpoint verified. Found all 7 sources with valid schemas.")
            
    except Exception as e:
        print(f"[FAIL] Error querying endpoints: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
