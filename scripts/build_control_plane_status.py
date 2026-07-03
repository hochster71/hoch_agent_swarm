#!/usr/bin/env python3
import os
import sys
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
CONFIG_DIR = ROOT / "config"

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def to_utc_str(dt):
    return dt.isoformat().replace("+00:00", "Z")

def parse_utc_str(ts_str):
    try:
        ts_iso = ts_str.rstrip("Z").split("+")[0]
        return datetime.datetime.fromisoformat(ts_iso).replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None

def wrap_section(name, source_path, snapshot_time, max_age=600, is_hoch200=False, closure_action=None, timestamp_field=None):
    source_rel = os.path.relpath(source_path, ROOT) if source_path else "DYNAMIC_STATE"
    checked_at = to_utc_str(snapshot_time)
    
    if not source_path or not os.path.exists(source_path):
        return {
            "state": "MISSING",
            "source_file": source_rel,
            "data_as_of": "UNKNOWN",
            "snapshot_as_of": to_utc_str(snapshot_time),
            "age_seconds": 999999,
            "max_age_seconds": max_age,
            "hoch200_owned": is_hoch200,
            "hoch200_sync_age_seconds": 999999 if is_hoch200 else 0,
            "checked_at": checked_at,
            "closure_action": closure_action or f"Recreate or restore {source_rel}",
            "data": {}
        }

    # Load data
    data = {}
    try:
        with open(source_path, "r") as f:
            data = json.load(f)
    except Exception:
        pass

    # Determine data_as_of
    data_as_of_dt = None
    if timestamp_field and isinstance(data, dict):
        ts_val = data.get(timestamp_field)
        if ts_val:
            data_as_of_dt = parse_utc_str(ts_val)
            
    if not data_as_of_dt:
        mtime = os.path.getmtime(source_path)
        data_as_of_dt = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)

    data_as_of_str = to_utc_str(data_as_of_dt)
    age_seconds = int((snapshot_time - data_as_of_dt).total_seconds())
    if age_seconds < 0:
        age_seconds = 0

    state = "FRESH"
    current_closure = "None"
    
    if is_hoch200:
        # HOCH-200 owned files
        if age_seconds > max_age:
            state = "SYNC_STALE"
            current_closure = "run bash scripts/secure_sync_hoch200.sh then rebuild control_plane_status.json"
    else:
        if age_seconds > max_age:
            state = "STALE"
            current_closure = closure_action or f"Update data source {source_rel}"

    return {
        "state": state,
        "source_file": source_rel,
        "data_as_of": data_as_of_str,
        "snapshot_as_of": to_utc_str(snapshot_time),
        "age_seconds": age_seconds,
        "max_age_seconds": max_age,
        "hoch200_owned": is_hoch200,
        "hoch200_sync_age_seconds": age_seconds if is_hoch200 else 0,
        "checked_at": checked_at,
        "closure_action": current_closure,
        "data": data
    }

def verify_compute_rules():
    config_path = CONFIG_DIR / "compute_assets.json"
    if not config_path.exists():
        return False, "compute_assets.json missing"
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
        assets = cfg.get("assets", [])
        total_billable = 0
        hoch_200_billable = False
        linode_60_billable = False
        for a in assets:
            if a.get("billable", False):
                total_billable += a.get("monthly_cost_usd", 0)
                if a.get("id") == "hoch-200":
                    hoch_200_billable = True
                if a.get("id") == "linode-remote-60":
                    linode_60_billable = True
        if total_billable == 60 and hoch_200_billable and not linode_60_billable:
            return True, "Compute cost verification passed"
        return False, f"Invalid billing configuration: total={total_billable}, hoch-200={hoch_200_billable}, linode-remote-60={linode_60_billable}"
    except Exception as e:
        return False, f"Error: {e}"

def verify_tag_rules():
    policy_path = CONFIG_DIR / "release_tag_policy.json"
    if not policy_path.exists():
        return False, "release_tag_policy.json missing"
    try:
        with open(policy_path, "r") as f:
            policy = json.load(f)
        tag = policy.get("tag")
        expected_commit = policy.get("expected_commit")
        res = subprocess.run(["git", "rev-parse", f"{tag}^{{commit}}"], capture_output=True, text=True, cwd=ROOT)
        if res.returncode == 0:
            if res.stdout.strip() == expected_commit:
                return True, f"Tag {tag} verified at commit {expected_commit}"
        return False, f"Tag commit mismatch"
    except Exception as e:
        return False, f"Error: {e}"

import subprocess

def build():
    snapshot_time = get_utc_now()
    max_age_seconds = int(os.environ.get("STATUS_MAX_AGE_SECONDS", "60"))
    
    # 1. Authority (orchestration_bridge_control.json) [HOCH-200 owned]
    authority = wrap_section("authority", DATA_DIR / "orchestration_bridge_control.json", snapshot_time, is_hoch200=True)
    if "data" in authority and isinstance(authority["data"], dict):
        authority["data"]["claude_adapter_file_state"] = "READY"
        authority["data"]["claude_adapter_live_state"] = "DISABLED_NOT_CONFIGURED"
        authority["data"]["claude_adapter_state"] = "DISABLED_NOT_CONFIGURED"
    
    # 2. Compute (compute_assets.json)
    compute = wrap_section("compute", CONFIG_DIR / "compute_assets.json", snapshot_time, is_hoch200=False)
    
    # 3. Rung State (orchestration_bridge_control.json) [HOCH-200 owned]
    rung_state = wrap_section("rung_state", DATA_DIR / "orchestration_bridge_control.json", snapshot_time, is_hoch200=True)
    if "data" in rung_state and isinstance(rung_state["data"], dict):
        rung_state["data"]["claude_adapter_file_state"] = "READY"
        rung_state["data"]["claude_adapter_live_state"] = "DISABLED_NOT_CONFIGURED"
        rung_state["data"]["claude_adapter_state"] = "DISABLED_NOT_CONFIGURED"
    
    # 4. HAS (has_runtime_state.json) [HOCH-200 owned]
    has = wrap_section("has", DATA_DIR / "has_runtime_state.json", snapshot_time, is_hoch200=True, timestamp_field="last_heartbeat")
    
    # 5. HASF (hasf_runtime_state.json)
    hasf = wrap_section("hasf", DATA_DIR / "hasf_runtime_state.json", snapshot_time, is_hoch200=False, timestamp_field="last_heartbeat")
    
    # 6. Agents (helm_agent_registry.json)
    agents = wrap_section("agents", DATA_DIR / "helm_agent_registry.json", snapshot_time, is_hoch200=False)
    
    # 7. Adapters (helm_adapter_registry.json) [HOCH-200 owned]
    adapters = wrap_section("adapters", DATA_DIR / "helm_adapter_registry.json", snapshot_time, is_hoch200=True)
    
    # 8. Models (model_capacity_target.json)
    models = wrap_section("models", DATA_DIR / "model_capacity_target.json", snapshot_time, is_hoch200=False, timestamp_field="as_of")
    
    # 9. Freshness (live_telemetry_freshness.json)
    freshness = wrap_section("freshness", DATA_DIR / "live_telemetry_freshness.json", snapshot_time, is_hoch200=False, timestamp_field="generated_at")

    # Load metrics for zero_tolerance
    metrics_path = DATA_DIR / "guardrail_metrics.json"
    metrics_data = {}
    metrics_age = 999999
    if metrics_path.exists():
        try:
            with open(metrics_path, "r") as f:
                metrics_data = json.load(f)
            metrics_ts = parse_utc_str(metrics_data.get("timestamp"))
            if metrics_ts:
                metrics_age = int((snapshot_time - metrics_ts).total_seconds())
        except Exception:
            pass

    # Build zero_tolerance checks (Aggregator Reducer rules)
    zero_tolerance = []
    
    # helper for adding entries
    def add_zt(name, source, ok, reason, age_seconds, evidence_path, closure):
        state = "FAIL"
        if age_seconds > 600:
            state = "STALE"
        elif ok:
            state = "PASS"
        zero_tolerance.append({
            "name": name,
            "state": state,
            "source": os.path.relpath(source, ROOT) if isinstance(source, Path) else str(source),
            "checked_at": to_utc_str(snapshot_time),
            "source_age_seconds": age_seconds,
            "evidence_path": evidence_path,
            "closure_action": closure
        })

    # Secret Scanning
    sec_ok = metrics_data.get("security_guardrail_violations", 999) == 0
    add_zt("secret_scanning", metrics_path, sec_ok, "Security violations", metrics_age, "has_live_project_tracker/data/guardrail_metrics.json", "Fix secrets in committed files then run scripts/secure_build_guardrail_check.sh")

    # Public Exposure
    pub_ok = metrics_data.get("public_exposure_violations", 999) == 0
    add_zt("public_exposure", metrics_path, pub_ok, "Public exposure violations", metrics_age, "has_live_project_tracker/data/guardrail_metrics.json", "Close open public ports")

    # Fake Status Flags
    fake_ok = metrics_data.get("fake_status_violations", 999) == 0
    add_zt("fake_status_flags", metrics_path, fake_ok, "Fake status violations", metrics_age, "has_live_project_tracker/data/guardrail_metrics.json", "Remove fake status flags from status.json")

    # Verification Signature
    sig_path = DATA_DIR / "evidence_manifest_head.sig"
    sig_age = 999999
    if sig_path.exists():
        sig_age = int((snapshot_time - datetime.datetime.fromtimestamp(os.path.getmtime(sig_path), datetime.timezone.utc)).total_seconds())
    add_zt("verification_signature", sig_path, sig_path.exists(), "Signature exists", sig_age, "has_live_project_tracker/data/evidence_manifest_head.sig", "Run scripts/sign_evidence_manifest_head.py")

    # Compute Billing
    comp_ok, comp_reason = verify_compute_rules()
    comp_path = CONFIG_DIR / "compute_assets.json"
    comp_age = int((snapshot_time - datetime.datetime.fromtimestamp(os.path.getmtime(comp_path), datetime.timezone.utc)).total_seconds())
    add_zt("compute_billing", comp_path, comp_ok, comp_reason, comp_age, "config/compute_assets.json", "Fix compute cost in config/compute_assets.json")

    # Tag Integrity
    tag_ok, tag_reason = verify_tag_rules()
    tag_path = CONFIG_DIR / "release_tag_policy.json"
    tag_age = 999999
    if tag_path.exists():
        tag_age = int((snapshot_time - datetime.datetime.fromtimestamp(os.path.getmtime(tag_path), datetime.timezone.utc)).total_seconds())
    add_zt("tag_integrity", tag_path, tag_ok, tag_reason, tag_age, "config/release_tag_policy.json", "Fix release tag policy configurations")

    # Stale or Missing count
    stale_or_missing = {
        "missing_count": 0,
        "stale_count": 0,
        "sync_stale_count": 0,
        "details": []
    }
    
    sections = [authority, compute, rung_state, has, hasf, agents, adapters, models, freshness]
    for s in sections:
        if s["state"] == "MISSING":
            stale_or_missing["missing_count"] += 1
            stale_or_missing["details"].append(f"{s['source_file']} is MISSING")
        elif s["state"] == "STALE":
            stale_or_missing["stale_count"] += 1
            stale_or_missing["details"].append(f"{s['source_file']} is STALE (age={s['age_seconds']}s)")
        elif s["state"] == "SYNC_STALE":
            stale_or_missing["sync_stale_count"] += 1
            stale_or_missing["details"].append(f"{s['source_file']} is SYNC_STALE (age={s['age_seconds']}s)")

    # Global actions
    closure_actions = []
    if stale_or_missing["sync_stale_count"] > 0:
        closure_actions.append("run bash scripts/secure_sync_hoch200.sh then rebuild control_plane_status.json")
    if stale_or_missing["stale_count"] > 0:
        closure_actions.append("python3 scripts/refresh_heartbeats.py")

    expires_at = snapshot_time + datetime.timedelta(seconds=max_age_seconds)
    
    # Contract state
    contract_state = "FRESH" # Initially generated fresh

    # Build final dict
    status_payload = {
        "schema_version": "1.0",
        "source_of_truth": False,
        "system_of_record": "HOCH-200",
        "synced_from": "HOCH-200",
        "as_of": to_utc_str(snapshot_time),
        "max_age_seconds": max_age_seconds,
        "expires_at": to_utc_str(expires_at),
        "contract_state": contract_state,
        "authority": authority,
        "compute": compute,
        "rung_state": rung_state,
        "has": has,
        "hasf": hasf,
        "agents": agents,
        "adapters": adapters,
        "models": models,
        "freshness": freshness,
        "zero_tolerance": zero_tolerance,
        "stale_or_missing": stale_or_missing,
        "closure_actions": closure_actions
    }

    # Minimum schema validator verification inline
    required_keys = [
        "schema_version", "source_of_truth", "system_of_record", "as_of", "expires_at", "max_age_seconds",
        "authority", "compute", "rung_state", "has", "hasf", "agents", "adapters", "models",
        "freshness", "zero_tolerance", "stale_or_missing", "closure_actions"
    ]
    missing = [k for k in required_keys if k not in status_payload]
    if missing:
        raise ValueError(f"Missing required top-level keys: {missing}")

    output_path = DATA_DIR / "control_plane_status.json"
    with open(output_path, "w") as f:
        json.dump(status_payload, f, indent=2)
    print(f"🟢 Successfully wrote control_plane_status.json to {output_path}")

if __name__ == "__main__":
    build()
