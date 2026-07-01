#!/usr/bin/env python3
import sys
import os
import json
import yaml
import urllib.request
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

POLICY_PATH = os.path.join(PROJECT_ROOT, "config", "telemetry_freshness_policy.yaml")
API_URL = "http://127.0.0.1:8765/api/pert/data"

def main():
    print("==================================================")
    print("RUNNING DYNAMIC TELEMETRY FRESHNESS COMPLIANCE AUDIT")
    print("==================================================")

    # 1. Load Policy
    if not os.path.exists(POLICY_PATH):
        print(f"[FAIL] Freshness policy not found at: {POLICY_PATH}")
        sys.exit(1)
        
    with open(POLICY_PATH, "r") as f:
        policy = yaml.safe_load(f)
    thresholds = policy.get("freshness_thresholds", {})
    print("[PASS] Telemetry freshness policy loaded successfully.")

    # 2. Fetch API Data
    try:
        req = urllib.request.Request(API_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[FAIL] Failed to fetch data from PERT server: {e}")
        sys.exit(1)
    print("[PASS] Fetched PERT cockpit API payload successfully.")

    # 3. Check freshness_authority exists in payload
    fa = data.get("freshness_authority")
    if not fa:
        print("[FAIL] 'freshness_authority' is missing from the payload.")
        sys.exit(1)
    print("[PASS] Found 'freshness_authority' block in payload.")

    # 4. Check all 8 timestamps exist
    required_timestamps = [
        "dashboard_render_time",
        "global_last_full_verification_time",
        "worker_last_probe_time",
        "worker_last_dispatch_time",
        "device_last_seen_time",
        "evidence_ledger_last_scan_time",
        "playwright_scoped_spec_last_run_time",
        "playwright_full_suite_last_run_time"
    ]

    failed = False
    now = datetime.now(timezone.utc)

    # Parse dashboard render time to anchor calculations
    render_time_str = fa.get("dashboard_render_time")
    if not render_time_str:
        print("[FAIL] 'dashboard_render_time' is missing from freshness_authority.")
        sys.exit(1)
    
    try:
        render_time = datetime.fromisoformat(render_time_str.rstrip("Z").split("+")[0]).replace(tzinfo=timezone.utc)
    except Exception as e:
        print(f"[FAIL] Failed to parse dashboard_render_time '{render_time_str}': {e}")
        sys.exit(1)

    for ts_name in required_timestamps:
        val = fa.get(ts_name)
        if not val:
            print(f"[FAIL] Timestamp '{ts_name}' is missing in freshness_authority.")
            failed = True
            continue
        print(f"[PASS] Timestamp '{ts_name}' exists: {val}")

        # Check freshness state per panel
        state_key = f"{ts_name}_state"
        state_val = fa.get(state_key)
        if not state_val:
            print(f"[FAIL] Freshness state '{state_key}' is missing in freshness_authority.")
            failed = True
            continue
        print(f"  [PASS] Freshness state '{state_key}': {state_val}")

    # Check panel freshness states mapping
    panels = fa.get("panels", {})
    required_panels = [
        "executive_readiness",
        "runtime_status",
        "risks_blockers",
        "worker_metrics",
        "worker_utilization_ledger",
        "pert_recalibration",
        "compute_goal_acceleration",
        "parallel_mirror_verification",
        "monetization_readiness",
        "evidence_ledger",
        "playwright_e2e"
    ]

    for panel in required_panels:
        p_info = panels.get(panel)
        if not p_info:
            print(f"[FAIL] Panel '{panel}' is missing in freshness_authority.panels.")
            failed = True
            continue
        
        f_state = p_info.get("freshness_state")
        s_reason = p_info.get("stale_reason")
        if not f_state or not s_reason:
            print(f"[FAIL] Panel '{panel}' is missing freshness_state or stale_reason.")
            failed = True
            continue
        print(f"  [PASS] Panel '{panel}' freshness_state: {f_state} | stale_reason: {s_reason}")

    # 5. Check if executive readiness degraded if fake status audit fails
    fake_status_violations = data.get("guardrails", {}).get("fake_status_violations", {}).get("value", 0)
    if fake_status_violations > 0 or data.get("metrics", {}).get("no_fake_status_violations", 0) > 0:
        # Expected: Executive Readiness freshness_state is DEGRADED and readiness value shows DEGRADED
        readiness_score = data.get("readiness", {}).get("score", {}).get("value", "UNKNOWN")
        exec_freshness = panels.get("executive_readiness", {}).get("freshness_state")
        confidence = data.get("readiness", {}).get("confidence", "UNKNOWN")

        if exec_freshness != "DEGRADED":
            print(f"[FAIL] Fake status violations found but executive_readiness freshness state is '{exec_freshness}' (expected: DEGRADED).")
            failed = True
        else:
            print("[PASS] Executive readiness freshness state correctly set to DEGRADED due to fake status violations.")

        if "DEGRADED" not in str(readiness_score):
            print(f"[FAIL] Fake status violations found but readiness score is '{readiness_score}' (expected: DEGRADED).")
            failed = True
        else:
            print("[PASS] Executive readiness score shows DEGRADED due to fake status violations.")

        if "degraded" not in confidence.lower() and "low" not in confidence.lower():
            print(f"[FAIL] Fake status violations found but confidence is still '{confidence}' (expected: degraded).")
            failed = True
        else:
            print("[PASS] Goal completion confidence is degraded due to fake status violations.")

    if failed:
        print("==================================================")
        print(">> FAILURE: Telemetry Freshness compliance audit failed!")
        print("==================================================")
        sys.exit(1)
    else:
        print("==================================================")
        print(">> SUCCESS: Telemetry Freshness compliance audit passed!")
        print("==================================================")
        sys.exit(0)

if __name__ == "__main__":
    main()
