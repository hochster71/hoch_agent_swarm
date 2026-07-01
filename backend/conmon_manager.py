import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

CONMON_STATE = {
    "status": "IDLE",  # IDLE, RUNNING, ALERTING
    "last_run": "Never",
    "schedule_interval": "Daily",  # Hourly, Daily, Weekly
    "compliance_score": 88.0,
    "previous_score": 88.0,
    "active_alerts": [],
    "logs": [
        "[system] Continuous monitoring daemon initialized. Awaiting scheduled execution."
    ],
    "history": []
}

def get_conmon_status() -> dict:
    delta = CONMON_STATE["compliance_score"] - CONMON_STATE["previous_score"]
    return {
        "status": CONMON_STATE["status"],
        "last_run": CONMON_STATE["last_run"],
        "schedule_interval": CONMON_STATE["schedule_interval"],
        "compliance_score": CONMON_STATE["compliance_score"],
        "previous_score": CONMON_STATE["previous_score"],
        "delta": delta,
        "active_alerts": CONMON_STATE["active_alerts"],
        "logs": CONMON_STATE["logs"],
        "history": CONMON_STATE["history"],
        "compliance": {
            "statement": "SIMULATED CONTINUOUS COMPLIANCE POSTURE",
            "notice": "Continuous monitoring is simulated for controlled compliance evaluation. Actual ATO has not been granted. No authorization claim is being made."
        }
    }

def update_conmon_schedule(interval: str) -> dict:
    global CONMON_STATE
    if interval in ["Hourly", "Daily", "Weekly"]:
        CONMON_STATE["schedule_interval"] = interval
        CONMON_STATE["logs"].append(f"[schedule] Updated monitoring interval to: {interval}")
    return get_conmon_status()

def execute_conmon_cycle(root_dir: str = ".") -> dict:
    global CONMON_STATE
    
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    CONMON_STATE["status"] = "RUNNING"
    CONMON_STATE["logs"].append(f"[{ts}] Launching active Continuous Monitoring evaluation cycle...")
    
    # 1. Fetch current live boundary state
    from backend.live_binding_manager import get_live_binding_status
    live_status = get_live_binding_status()
    
    # Evaluate check results and alert on issues
    alerts = []
    
    # Simulate scanning Live Exposure parameters
    tls_ok = live_status["metrics"]["tls_active"]
    auth_ok = live_status["metrics"]["auth_enforced"]
    ports_ok = (live_status["metrics"]["network_exposed_port"] == 8443) if live_status["metrics"]["network_exposed_port"] else True
    
    if not tls_ok and live_status["status"] == "LIVE":
        alerts.append({
            "id": f"alrt-{int(datetime.utcnow().timestamp())}-tls",
            "severity": "CRITICAL",
            "message": "TLS boundary routes disabled on active exposure endpoint."
        })
    if not auth_ok and live_status["status"] == "LIVE":
        alerts.append({
            "id": f"alrt-{int(datetime.utcnow().timestamp())}-auth",
            "severity": "HIGH",
            "message": "Admin session authenticator interceptor bypassed."
        })
    if not ports_ok:
        alerts.append({
            "id": f"alrt-{int(datetime.utcnow().timestamp())}-port",
            "severity": "CRITICAL",
            "message": "Detected unauthorized external network port exposure."
        })
        
    # 2. CyberGov Scorecard delta calculation
    prev = CONMON_STATE["compliance_score"]
    # Dynamic variation simulation
    score = 88.0
    if len(alerts) > 0:
        score -= len(alerts) * 5.0
    else:
        score = 92.0 # score improves when fully secure
        
    CONMON_STATE["previous_score"] = prev
    CONMON_STATE["compliance_score"] = score
    CONMON_STATE["active_alerts"] = alerts
    
    # Update status based on alerts
    if len(alerts) > 0:
        CONMON_STATE["status"] = "ALERTING"
        CONMON_STATE["logs"].append(f"[{ts}] [WARNING] Evaluation cycle complete. {len(alerts)} compliance breaches detected!")
    else:
        CONMON_STATE["status"] = "IDLE"
        CONMON_STATE["logs"].append(f"[{ts}] [PASS] Evaluation cycle complete. Zero compliance breaches detected.")
        
    # 3. Auto-update POA&Ms
    from backend.cybergov_manager import cybergov_poam
    if len(alerts) > 0:
        # Append alert issues to POA&M table
        for alert in alerts:
            alert_suffix = alert["id"].split("-")[-1].upper()
            existing = [p for p in cybergov_poam if p.get("poam_id") == f"PM-CONMON-{alert_suffix}"]
            if not existing:
                cybergov_poam.append({
                    "poam_id": f"PM-CONMON-{alert_suffix}",
                    "finding_id": f"fi-conmon-{alert['id'].split('-')[-1]}",
                    "title": f"Resolve ConMon {alert_suffix} alert",
                    "weakness_description": f"ConMon Alert: {alert['message']}",
                    "owner": "ISSO",
                    "scheduled_completion": "Immediate",
                    "status": "OPEN",
                    "closure_evidence": None
                })
    else:
        # Resolve any open ConMon POA&Ms
        for p in cybergov_poam:
            if p.get("poam_id", "").startswith("PM-CONMON-"):
                p["status"] = "RESOLVED"
                
    # 4. Generate snapshot evidence
    snapshot = {
        "timestamp": ts,
        "interval": CONMON_STATE["schedule_interval"],
        "compliance_score": score,
        "previous_score": prev,
        "delta": score - prev,
        "alerts_count": len(alerts),
        "alerts": alerts,
        "live_metrics": live_status["metrics"]
    }
    
    artifacts_dir = Path(root_dir) / "artifacts" / "qa"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = artifacts_dir / f"conmon-evidence-{ts.replace(':', '-')}.json"
    with open(evidence_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        
    CONMON_STATE["logs"].append(f"[{ts}] Saved evidence snapshot to: {evidence_path.name}")
    CONMON_STATE["history"].append(snapshot)
    
    # 5. Log monitoring event to Action Ledger
    from backend.ledger_manager import log_operator_action
    log_operator_action(
        "conmon_compliance_evaluation",
        "/api/v1/conmon/run",
        {"timestamp": ts, "alerts_detected": len(alerts), "score": score},
        "APPROVED"
    )
    
    CONMON_STATE["last_run"] = ts
    
    return get_conmon_status()
