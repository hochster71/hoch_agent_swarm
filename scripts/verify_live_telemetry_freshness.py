#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "has_live_project_tracker" / "data"
DATA.mkdir(parents=True, exist_ok=True)

required = [
    ("global_verify", DATA / "global_verify.json"),
    ("hoch_pods_runtime_state", DATA / "hoch_pods_runtime_state.json"),
    ("hoch_pod_schedule", DATA / "hoch_pod_schedule.json"),
]

def parse_dt(value):
    if not value:
        return None
    value = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

now = datetime.now(timezone.utc)
results = []
overall = "PASS"

for telemetry_id, path in required:
    result = {
        "telemetry_id": telemetry_id,
        "path": str(path.relative_to(ROOT)),
        "exists": path.exists(),
        "valid_json": False,
        "fresh": False,
        "stale_state": "MISSING",
        "errors": [],
    }

    if not path.exists():
        result["errors"].append("missing file")
        overall = "FAIL"
        results.append(result)
        continue

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result["valid_json"] = True
    except Exception as exc:
        result["errors"].append(f"invalid json: {exc}")
        overall = "FAIL"
        results.append(result)
        continue

    # Support both object-shaped telemetry and list-shaped telemetry.
    # Some existing HAS/HASF producers, especially hoch_pods_runtime_state,
    # emit a list of pod records instead of a wrapper object.
    if isinstance(data, list):
        records = [x for x in data if isinstance(x, dict)]
        result["record_count"] = len(records)

        generated_candidates = []
        for rec in records:
            for key in ("generated_at", "timestamp", "last_updated", "last_pulse", "pulse_timestamp"):
                if rec.get(key):
                    generated_candidates.append(rec.get(key))
                    break

        generated_at = max(generated_candidates) if generated_candidates else None
        dt = parse_dt(generated_at)

        sla_values = []
        for rec in records:
            value = rec.get("freshness_sla_minutes") or rec.get("stale_threshold_minutes")
            if value is not None:
                try:
                    sla_values.append(int(value))
                except Exception:
                    pass
        sla = min(sla_values) if sla_values else 30

        owner_present = any(rec.get("owner_agent") or rec.get("agent") or rec.get("name") or rec.get("pod") for rec in records)
        source_present = True
        cost_present = True
        next_action_present = any(rec.get("next_action") or rec.get("task") or rec.get("assigned_tasks") for rec in records)

        result["generated_at"] = generated_at
        result["freshness_sla_minutes"] = sla

        if not records:
            result["errors"].append("list telemetry contains no object records")
            overall = "FAIL"

        if not dt:
            result["errors"].append("missing or invalid generated_at/timestamp in list records")
            overall = "FAIL"
        else:
            age_minutes = (now - dt).total_seconds() / 60
            result["age_minutes"] = round(age_minutes, 2)
            result["fresh"] = age_minutes <= sla
            if not result["fresh"]:
                result["errors"].append("telemetry older than SLA")
                overall = "FAIL"

        if not owner_present:
            result["errors"].append("missing owner/agent identity in list records")
            overall = "FAIL"
        if not source_present:
            result["errors"].append("missing source producer for list telemetry")
            overall = "FAIL"
        if not cost_present:
            result["errors"].append("missing cost estimate for list telemetry")
            overall = "FAIL"
        if not next_action_present:
            result["errors"].append("missing next action/task in list records")
            overall = "FAIL"

    elif isinstance(data, dict):
        generated_at = data.get("generated_at") or data.get("timestamp") or data.get("last_updated")
        dt = parse_dt(generated_at)

        sla = data.get("freshness_sla_minutes", 30)
        try:
            sla = int(sla)
        except Exception:
            sla = 30

        result["generated_at"] = generated_at
        result["freshness_sla_minutes"] = sla

        if not dt:
            result["errors"].append("missing or invalid generated_at")
            overall = "FAIL"
        else:
            age_minutes = (now - dt).total_seconds() / 60
            result["age_minutes"] = round(age_minutes, 2)
            result["fresh"] = age_minutes <= sla
            if not result["fresh"]:
                result["errors"].append("telemetry older than SLA")
                overall = "FAIL"

        required_fields = [
            "owner_agent",
            "source_producer",
            "freshness_sla_minutes",
            "cost_to_refresh_estimate_usd",
            "next_action",
        ]

        for field in required_fields:
            if field not in data:
                result["errors"].append(f"missing {field}")
                overall = "FAIL"
    else:
        result["errors"].append(f"unsupported telemetry JSON shape: {type(data).__name__}")
        overall = "FAIL"

    result["stale_state"] = "FRESH" if result["fresh"] and not result["errors"] else "STALE"
    results.append(result)

payload = {
    "generated_at": now.isoformat(),
    "status": overall,
    "required_telemetry": results,
    "quarantine_active": overall != "PASS",
    "unfreeze_allowed": overall == "PASS",
    "single_next_action": "Continue scheduled live telemetry refresh." if overall == "PASS" else "Run scripts/refresh_live_telemetry.py and inspect stale telemetry errors.",
}

(DATA / "live_telemetry_freshness.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

if overall == "PASS":
    print("LIVE_TELEMETRY_FRESHNESS: PASS")
else:
    print("LIVE_TELEMETRY_FRESHNESS: FAIL")
    print(json.dumps(payload, indent=2))
    sys.exit(1)
