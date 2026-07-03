#!/usr/bin/env python3
import sys
import json
import time

def run_worker_job(job_type: str):
    allowed_jobs = [
        "run_demo_workflow", "run_prompt_brain_eval", "run_health_audit",
        "refresh_route_index", "export_evidence_pack", "run_backup",
        "generate_pilot_report", "verify_private_first_doctrine"
    ]
    if job_type not in allowed_jobs:
        return {"status": "FAILED", "error": f"Unknown or unsafe job type: {job_type}"}
        
    start_time = time.time()
    # Mocking execution steps
    time.sleep(0.1)
    duration = int((time.time() - start_time) * 1000)
    
    return {
        "job_id": f"job_{int(start_time)}",
        "job_type": job_type,
        "status": "SUCCESS",
        "started_at": start_time,
        "completed_at": time.time(),
        "duration_ms": duration,
        "output_path": f"/data/runtime/outputs/{job_type}.json",
        "error": None,
        "evidence_hash": "sha256-mocked-evidence-hash"
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: worker_runner.py <job_type>")
        sys.exit(1)
    res = run_worker_job(sys.argv[1])
    print(json.dumps(res))
