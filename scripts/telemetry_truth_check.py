#!/usr/bin/env python3
import sys
import json
import urllib.request

def main():
    print("==================================================")
    print("RUNNING DYNAMIC TELEMETRY TRUTH COMPLIANCE AUDIT")
    print("==================================================")
    
    url = "http://127.0.0.1:8765/api/pert/data"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[FAIL] Failed to fetch data from PERT server: {e}")
        sys.exit(1)

    required_fields = [
        ("backend_status", data),
        ("relay_status", data),
        ("port_public_closed", data),
        ("tests_passing_count", data),
        ("tests_failing_count", data),
        ("evidence_coverage_percent", data),
        ("agent_accountability_score", data),
        ("time_saved_minutes", data),
        ("active_workers_count", data),
        ("total_workers_count", data),
        ("high_risk_approval_queue", data),
        ("manual_intervention_queue", data),
        ("goal_progress_percent", data.get("guardrails", {})),
        ("security_guardrail_violations", data.get("guardrails", {})),
        ("public_exposure_violations", data.get("guardrails", {})),
        ("fake_status_violations", data.get("guardrails", {})),
        ("monetization_readiness_percent", data.get("monetization", {})),
        ("evidence_gap_count", data.get("monetization", {})),
        ("stripe_sandbox_readiness", data.get("monetization", {})),
        ("export_expansion_guardrail_status", data.get("monetization", {})),
    ]

    schema_keys = ["value", "source", "last_updated", "freshness", "confidence", "fallback_state"]
    failed = False

    for field, parent in required_fields:
        val = parent.get(field)
        if val is None:
            print(f"  [FAIL] Required field '{field}' is missing from payload.")
            failed = True
            continue
        
        if not isinstance(val, dict):
            print(f"  [FAIL] Field '{field}' is not a dictionary. Type: {type(val).__name__}")
            failed = True
            continue
            
        missing_keys = [k for k in schema_keys if k not in val]
        if missing_keys:
            print(f"  [FAIL] Field '{field}' is missing required schema keys: {missing_keys}")
            failed = True
        else:
            print(f"  [PASS] Field '{field}' carries valid telemetry provenance schema.")

    # Audit workers list
    workers = data.get("tailnet_workers", [])
    if not workers:
        print("  [FAIL] No tailnet_workers returned.")
        failed = True
    else:
        for w in workers:
            w_status = w.get("status")
            if not isinstance(w_status, dict) or any(k not in w_status for k in schema_keys):
                print(f"  [FAIL] Worker '{w.get('machine')}' status is missing telemetry schema: {w_status}")
                failed = True
            else:
                print(f"  [PASS] Worker '{w.get('machine')}' status carries valid telemetry schema.")

    # Audit dispatch history
    history = data.get("dispatch_history", [])
    for job in history:
        job_status = job.get("status")
        if not isinstance(job_status, dict) or any(k not in job_status for k in schema_keys):
            print(f"  [FAIL] Dispatch job '{job.get('task_id')}' status is missing telemetry schema: {job_status}")
            failed = True
        else:
            print(f"  [PASS] Dispatch job '{job.get('task_id')}' status carries valid telemetry schema.")

    if failed:
        print("==================================================")
        print(">> FAILURE: Telemetry Truth check failed compliance audit!")
        print("==================================================")
        sys.exit(1)
    else:
        print("==================================================")
        print(">> SUCCESS: Telemetry Truth check passed compliance audit!")
        print("==================================================")
        sys.exit(0)

if __name__ == "__main__":
    main()
