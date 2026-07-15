#!/usr/bin/env python3
import os
import sys
import json
from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="HOCH Swarm Remote Relay API")

AUTH_TOKEN = os.getenv("RELAY_AUTH_TOKEN", "change-me")

def enforce_token_auth(authorization: str):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization token.")
    # Extract token
    token = authorization.split(" ")[-1] if " " in authorization else authorization
    if token != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token.")

@app.get("/relay/health")
def get_relay_health():
    return {"status": "healthy", "service": "relay-api"}

@app.get("/relay/status")
def get_relay_status(authorization: str = Header(None)):
    enforce_token_auth(authorization)
    return {
        "status": "active",
        "private_first_doctrine": "ENFORCED",
        "external_engagement": "FROZEN"
    }

@app.get("/relay/services")
def get_relay_services(authorization: str = Header(None)):
    enforce_token_auth(authorization)
    return {
        "services": [
            {"name": "has-backend", "status": "ONLINE"},
            {"name": "prompt-brain-runtime", "status": "ONLINE"},
            {"name": "prompt-brain-worker", "status": "ONLINE"}
        ]
    }

@app.get("/relay/evidence")
def get_relay_evidence(authorization: str = Header(None)):
    enforce_token_auth(authorization)
    return {"evidence_count": 0, "storage": "writable"}

@app.post("/relay/run-demo")
def post_relay_run_demo(authorization: str = Header(None)):
    enforce_token_auth(authorization)
    return {"status": "success", "job_id": "job_demo_001", "message": "Demo job executed."}

@app.post("/relay/run-prompt-brain-job")
def post_relay_run_job(payload: dict, authorization: str = Header(None)):
    enforce_token_auth(authorization)
    job_type = payload.get("job_type")
    allowed_jobs = [
        "run_demo_workflow", "run_prompt_brain_eval", "run_health_audit",
        "refresh_route_index", "export_evidence_pack", "run_backup",
        "generate_pilot_report", "verify_private_first_doctrine"
    ]
    if job_type not in allowed_jobs:
        raise HTTPException(status_code=400, detail=f"Unrecognized or unsafe job type: {job_type}")
    return {"status": "success", "job_id": "job_worker_001", "job_type": job_type}

@app.post("/relay/backup")
def post_relay_backup(authorization: str = Header(None)):
    enforce_token_auth(authorization)
    return {"status": "success", "backup_id": "backup_001", "manifest": "saved"}

@app.post("/relay/verify")
def post_relay_verify(authorization: str = Header(None)):
    enforce_token_auth(authorization)
    return {"status": "success", "doctrine_gate": "PRIVATE_FIRST_GO"}

if __name__ == "__main__":
    import uvicorn
    # SC-7: default to LOOPBACK. A real cross-machine deployment must opt in explicitly
    # via RELAY_BIND_HOST=0.0.0.0 AND set a strong RELAY_AUTH_TOKEN — binding a public
    # interface with the default/empty token is refused (fail-closed).
    host = os.getenv("RELAY_BIND_HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "localhost", "::1") and AUTH_TOKEN in ("", "change-me"):
        raise SystemExit(
            "REFUSING to bind a public interface with the default/empty RELAY_AUTH_TOKEN. "
            "Set a strong RELAY_AUTH_TOKEN before exposing the relay."
        )
    uvicorn.run(app, host=host, port=int(os.getenv("RELAY_PORT", "8010")))
