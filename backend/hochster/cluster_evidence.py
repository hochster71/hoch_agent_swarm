from backend.hochster.cluster_trace import generate_otel_trace, generate_correlation_id

def verify_trace_and_link_to_audit(job_id: str, result: dict) -> dict:
    """Links HOCHSTER job results with OTel trace context and copies details into audit event logs."""
    trace_id = result.get("trace_id")
    correlation_id = result.get("correlation_id")
    
    # Audit log event mapping trace to provenance evidence
    audit_evt = {
        "actor": {
            "id": f"hochster-{result['instance']}",
            "name": f"HOCHSTER {result['instance']}",
            "type": "system"
        },
        "action": {
            "type": "HOCHSTER_JOB_COMPLETED",
            "summary": f"Job {job_id} execution completed."
        },
        "target": {
            "type": "job",
            "id": job_id,
            "name": f"HOCHSTER Job {job_id}"
        },
        "result": "success" if result["status"] == "pass" else "failure",
        "severity": "info" if result["status"] == "pass" else "warning",
        "provenance": {
            "source": "observed",
            "evidence_refs": result.get("evidence_refs", []),
            "trace_id": trace_id
        },
        "policy": {
            "required": False,
            "result": "passed"
        },
        "metadata": {
            "correlation_id": correlation_id,
            "trace_id": trace_id
        }
    }
    return audit_evt
