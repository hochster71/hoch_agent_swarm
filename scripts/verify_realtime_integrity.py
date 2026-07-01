import urllib.request
import json
import sys

API_BASE = "http://localhost:8000"

def test_endpoint(path, name):
    print(f"Testing endpoint {path} ({name})...")
    try:
        req = urllib.request.urlopen(f"{API_BASE}{path}")
        if req.getcode() != 200:
            print(f" [FAIL] Endpoint returned status code {req.getcode()}")
            return False, None
        
        data = json.loads(req.read().decode("utf-8"))
        
        # Verify OTel headers
        otel = data.get("otel", {})
        correlation_id = data.get("correlation_id")
        observed_at = data.get("observed_at")
        
        if not otel.get("trace_id") or not otel.get("span_id"):
            print(" [FAIL] Missing OTel trace telemetry (trace_id or span_id)")
            return False, None
            
        if not correlation_id:
            print(" [FAIL] Missing correlation_id")
            return False, None
            
        if not observed_at:
            print(" [FAIL] Missing observed_at timestamp")
            return False, None
            
        print(f" [PASS] Telemetry check succeeded. Trace ID: {otel['trace_id']}, Correlation ID: {correlation_id}")
        return True, data
    except Exception as e:
        print(f" [FAIL] Exception raised: {e}")
        return False, None

def run_tests():
    print("==================================================")
    print("HOCH CONTROL PLANE: VERIFYING REAL-TIME INTEGRITY")
    print("==================================================")
    
    success = True
    
    # 1. Test Health API
    health_pass, health_data = test_endpoint("/api/v1/hochster/health", "Cluster Health API")
    if not health_pass:
        success = False
    else:
        # Verify all 8 cluster roles
        services = health_data.get("services", [])
        expected_roles = [
            "Detect mock/static UI state",
            "Validate live endpoints",
            "Validate OTel traces/metrics/logs",
            "Inspect containers/logs/health",
            "Validate policy enforcement",
            "Validate audit event integrity",
            "Inject stale/failure scenarios",
            "Generate validated patches"
        ]
        roles_found = [s["role"] for s in services]
        missing_roles = [r for r in expected_roles if r not in roles_found]
        if missing_roles:
            print(f" [FAIL] Missing cluster roles: {missing_roles}")
            success = False
        else:
            print(f" [PASS] All {len(expected_roles)} cluster roles verified in active service telemetry.")

    # 2. Test Candidates API
    cand_pass, _ = test_endpoint("/api/v1/hochster/mesh/candidates", "Mesh Candidates API")
    if not cand_pass:
        success = False
        
    # 3. Test SLO API
    slo_pass, _ = test_endpoint("/api/v1/hochster/product/slo", "SLO Dashboard API")
    if not slo_pass:
        success = False

    # 4. Test Quotas API
    quota_pass, _ = test_endpoint("/api/v1/hochster/product/quotas", "Usage Quotas API")
    if not quota_pass:
        success = False

    # 5. Test Baseline Lock report
    lock_pass, lock_data = test_endpoint("/api/v1/hochster/baseline/lock", "Baseline Lock Report API")
    if not lock_pass:
        success = False
    else:
        report = lock_data.get("report", {})
        if report.get("lock_decision") != "PASS":
            print(f" [FAIL] Expected baseline lock PASS, got: {report.get('lock_decision')}")
            success = False
        else:
            print(f" [PASS] v0.1.0-RT-LOCK Baseline lock decision APPROVED.")
            
    print("==================================================")
    if success:
        print("VERIFICATION COMPLETED: ALL REAL-TIME INTEGRITY GATES PASSED")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED: REAL-TIME INTEGRITY DEFECTS DETECTED")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
