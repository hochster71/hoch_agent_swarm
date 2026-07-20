#!/usr/bin/env python3
import json
import urllib.request
import ssl
import sys
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def test_api_freshness():
    print("=== RUNNING FRESHNESS TEST ===")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    url = "https://127.0.0.1:8770/api/v1/helm/live-run"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
            body = r.read().decode("utf-8")
            data = json.loads(body)
            print(f"✓ API response loaded successfully.")
            print(f"✓ Generated at: {data['generated_at']}")
            print(f"✓ Freshness seconds: {data['freshness_seconds']}")
            print(f"✓ Truth status: {data['truth_status']}")
            assert data["freshness_seconds"] < 10.0, f"Freshness is too high: {data['freshness_seconds']}"
            print("✓ Freshness test PASSED.")
    except Exception as e:
        print(f"✗ Freshness test FAILED: {e}")
        sys.exit(1)

def test_stale_state():
    print("=== RUNNING STALE STATE NEGATIVE TEST ===")
    import scripts.helm_live_run_collector as collector
    
    # Read the original result file
    orig_content = collector.CONFIRMATION_RESULT_FILE.read_text(encoding="utf-8")
    orig_find_active = collector.find_active_processes
    try:
        # Mock active processes to return empty to isolate result testing
        collector.find_active_processes = lambda: []
        
        # Temporarily change the candidate_commit_sha in result file to simulate stale data
        res_data = json.loads(orig_content)
        res_data["candidate_commit_sha"] = "stale_commit_hash_1234567"
        collector.CONFIRMATION_RESULT_FILE.write_text(json.dumps(res_data), encoding="utf-8")
        
        # Run collection
        state = collector.collect()
        print(f"✓ Simulating stale commit. Truth status returned: {state['truth_status']}")
        assert state["truth_status"] == "STALE", f"Expected STALE, got {state['truth_status']}"
        print("✓ Stale-state negative test PASSED.")
    finally:
        # Restore original find_active_processes and result file
        collector.find_active_processes = orig_find_active
        collector.CONFIRMATION_RESULT_FILE.write_text(orig_content, encoding="utf-8")

def test_process_death():
    print("=== RUNNING PROCESS DEATH NEGATIVE TEST ===")
    import scripts.helm_live_run_collector as collector
    orig_find_active = collector.find_active_processes
    try:
        collector.find_active_processes = lambda: []
        state = collector.collect()
        print(f"✓ Collected truth status under simulated process death: {state['truth_status']}")
        assert state["truth_status"] not in ("RUNNING", "VALIDATING"), f"Expected inactive process status, got {state['truth_status']}"
        print("✓ Process-death negative test PASSED.")
    finally:
        collector.find_active_processes = orig_find_active

if __name__ == "__main__":
    test_api_freshness()
    print()
    test_stale_state()
    print()
    test_process_death()
    print()
    print("All live-run verification tests PASSED.")
