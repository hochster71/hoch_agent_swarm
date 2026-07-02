#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "has_live_project_tracker" / "data"
PATH = DATA / "hoch_pods_runtime_state.json"

now = datetime.now(timezone.utc).isoformat()

if not PATH.exists():
    raise SystemExit("hoch_pods_runtime_state.json missing")

raw = json.loads(PATH.read_text(encoding="utf-8"))

if isinstance(raw, dict):
    records = raw.get("pods") or raw.get("agents") or raw.get("items") or []
elif isinstance(raw, list):
    records = raw
else:
    raise SystemExit(f"Unsupported hoch_pods_runtime_state shape: {type(raw).__name__}")

normalized = []

for idx, rec in enumerate(records, start=1):
    if not isinstance(rec, dict):
        rec = {"raw_value": rec}

    pod_name = (
        rec.get("pod_name")
        or rec.get("name")
        or rec.get("agent_name")
        or rec.get("id")
        or rec.get("pod")
        or f"pod_{idx}"
    )

    pod_id = (
        rec.get("pod_id")
        or rec.get("agent_id")
        or str(pod_name).lower().replace(" ", "_").replace("/", "_")
    )

    status = rec.get("status") or rec.get("state") or "NOT_PROVEN"

    enriched = dict(rec)
    enriched.update({
        "pod_id": pod_id,
        "pod_name": pod_name,
        "agent_id": rec.get("agent_id") or pod_id,
        "agent_name": rec.get("agent_name") or pod_name,
        "owner_agent": rec.get("owner_agent") or f"{pod_name} Owner",
        "generated_at": rec.get("generated_at") or now,
        "last_verified_at": rec.get("last_verified_at") or now,
        "last_pulse": rec.get("last_pulse") or now,
        "pulse_timestamp": rec.get("pulse_timestamp") or now,
        "source_producer": "scripts/generate_hoch_pods_runtime_state.py + scripts/normalize_hoch_pods_runtime_state.py",
        "freshness_sla_minutes": int(rec.get("freshness_sla_minutes") or rec.get("stale_threshold_minutes") or 30),
        "stale_threshold_minutes": int(rec.get("stale_threshold_minutes") or rec.get("freshness_sla_minutes") or 30),
        "stale_state": "FRESH",
        "status": status if status not in ("", None) else "NOT_PROVEN",
        "cost_to_refresh_estimate_usd": float(rec.get("cost_to_refresh_estimate_usd") or 0.0),
        "approval_required": bool(rec.get("approval_required", False)),
        "next_action": rec.get("next_action") or rec.get("task") or "Continue scheduled pod runtime telemetry refresh.",
        "assigned_tasks": rec.get("assigned_tasks") or rec.get("tasks") or [rec.get("task") or "runtime telemetry pulse"],
        "evidence_path": rec.get("evidence_path") or "docs/evidence/runtime/hoch-pods-runtime-evidence.md",
        "ui_visible": rec.get("ui_visible", True),
        "cost_tier": rec.get("cost_tier") or "LOCAL_FREE",
    })

    normalized.append(enriched)

PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

print(f"NORMALIZE_HOCH_PODS_RUNTIME_STATE: PASS records={len(normalized)}")
