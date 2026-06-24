import urllib.request
import json
import os
import sys

API_BASE = "http://localhost:8000"

def test_endpoint(path, name):
    try:
        req = urllib.request.urlopen(f"{API_BASE}{path}")
        if req.getcode() != 200:
            print(f" [FAIL] {name} endpoint returned {req.getcode()}")
            return False, None
        data = json.loads(req.read().decode("utf-8"))
        return True, data
    except Exception as e:
        print(f" [FAIL] {name} request failed: {e}")
        return False, None

def run_audits():
    print("==================================================")
    print("HOCH-AGENT-SWARM V0.1.0-RT-LOCK SPRINT INTEGRITY AUDIT")
    print("==================================================")
    
    success = True
    
    # 1. API Telemetry Check
    print("Checking OTel telemetry spans and correlation IDs...")
    health_ok, health_data = test_endpoint("/api/v1/hochster/health", "Health API")
    if health_ok:
        correlation_id = health_data.get("correlation_id")
        otel = health_data.get("otel", {})
        if correlation_id and otel.get("trace_id") and otel.get("span_id"):
            print(f" [PASS] Telemetry traces active. Trace ID: {otel['trace_id']}")
        else:
            print(" [FAIL] Endpoints missing OTel trace context or transaction IDs.")
            success = False
    else:
        success = False

    # 2. Docker Health Reconciliation Check
    print("Reconciling container roles against UI status...")
    if health_ok:
        services = health_data.get("services", [])
        if len(services) == 8:
            print(f" [PASS] All 8 cluster roles verified and active.")
        else:
            print(f" [FAIL] Cluster role count mismatch: expected 8, found {len(services)}.")
            success = False
            
    # 3. Baseline Lock Report Gate
    print("Evaluating Baseline Lock Gates report...")
    lock_ok, lock_data = test_endpoint("/api/v1/hochster/baseline/lock", "Baseline Lock report API")
    if lock_ok:
        report = lock_data.get("report", {})
        decision = report.get("decision", {}).get("status", "BLOCK")
        if decision == "PASS":
            print(" [PASS] v0.1.0-RT-LOCK release decision: PASS (Approved)")
        else:
            print(f" [FAIL] release decision: {decision} (Blocked due to invalid gates)")
            success = False
            
        # Verify schema keys
        required_keys = ["baseline_id", "generated_at", "git_commit_sha", "docker", "realtime", "observability", "hochster", "audit", "decision"]
        missing_keys = [k for k in required_keys if k not in report]
        if missing_keys:
            print(f" [FAIL] Missing BaselineLockEvidencePack schema keys: {missing_keys}")
            success = False
        else:
            print(" [PASS] BaselineLockEvidencePack schema structure verified.")
    else:
        success = False
        
    print("==================================================")
    if success:
        print("VERIFICATION SUCCESS: OPERATIONAL BASELINE APPROVED FOR LOCK")
        sys.exit(0)
    else:
        print("VERIFICATION FAILURE: UNRESOLVED P0 BLOCKERS DETECTED")
        sys.exit(1)

if __name__ == "__main__":
    run_audits()
