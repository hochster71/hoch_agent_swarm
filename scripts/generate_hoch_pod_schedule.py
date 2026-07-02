#!/usr/bin/env python3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "has_live_project_tracker" / "data"
DATA.mkdir(parents=True, exist_ok=True)

now_dt = datetime.now(timezone.utc)
now = now_dt.isoformat()
next_refresh = (now_dt + timedelta(minutes=30)).isoformat()

agents = [
    "HAS Command",
    "HASF Factory",
    "Runtime Truth",
    "Stale Watchdog",
    "QA Gatekeeper",
    "PERT Planner",
    "Cost Governor",
    "Local AI Router",
    "Evidence Ledger",
    "Runner Ops",
    "Workflow Cost Guard",
    "Human Approval Gate",
    "Frontend UI",
    "Backend API",
    "Revenue Readiness",
    "Deployment Readiness",
    "Security Guard",
    "Visual Doctrine",
    "Voice Sidecar",
    "Storage Memory",
    "Product Packaging",
    "Agent Performance",
    "Stale Code Audit",
    "Family Revenue Mission",
]

schedule = []
for idx, name in enumerate(agents, start=1):
    schedule.append({
        "agent_id": name.lower().replace(" ", "_"),
        "agent_name": name,
        "owner_agent": name,
        "assigned_runner": "has-qa-runner-mac",
        "cadence_minutes": 30,
        "next_refresh_at": next_refresh,
        "source_producer": "scripts/generate_hoch_pod_schedule.py",
        "freshness_sla_minutes": 45,
        "stale_state": "FRESH",
        "status": "SCHEDULED",
        "approval_required": False,
        "cost_to_refresh_estimate_usd": 0.0,
        "next_action": "Refresh telemetry on next runner cycle.",
        "ui_lane": idx,
    })

payload = {
    "telemetry_id": "hoch_pod_schedule",
    "generated_at": now,
    "last_verified_at": now,
    "owner_agent": "Pod Schedule Agent",
    "source_producer": "scripts/generate_hoch_pod_schedule.py",
    "freshness_sla_minutes": 45,
    "stale_state": "FRESH",
    "status": "FRESH",
    "cost_to_refresh_estimate_usd": 0.0,
    "approval_required": False,
    "evidence_path": "has_live_project_tracker/data/hoch_pod_schedule.json",
    "next_action": "Continue scheduled pod refresh.",
    "active_runner": "has-qa-runner-mac",
    "linux_runner": "FUTURE_NOT_CONFIGURED",
    "release_runner": "FUTURE_NOT_CONFIGURED",
    "schedule": schedule,
}

(DATA / "hoch_pod_schedule.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print("HOCH_POD_SCHEDULE: FRESH")
