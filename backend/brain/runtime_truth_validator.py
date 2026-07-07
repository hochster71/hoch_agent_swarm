# -*- coding: utf-8 -*-
"""
backend/brain/runtime_truth_validator.py
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

STALE_THRESHOLD_SECONDS = 1800  # 30 minutes


def get_file_status(path: Path) -> str:
    """Determine file status: GO, STALE, QUARANTINED, MALFORMED, or UNKNOWN."""
    if not path.exists():
        return "UNKNOWN"

    # Quarantine check
    if "_quarantine_" in str(path) or "quarantine" in str(path).lower():
        return "QUARANTINED"

    # Staleness check
    try:
        mtime = path.stat().st_mtime
        age = datetime.now().timestamp() - mtime
        if age > STALE_THRESHOLD_SECONDS:
            return "STALE"
    except Exception:
        pass

    # Malformed check
    try:
        content = path.read_text(encoding="utf-8").strip()
        if path.suffix == ".json":
            json.loads(content)
        elif path.suffix == ".jsonl":
            for line in content.splitlines():
                if line.strip():
                    json.loads(line)
    except Exception:
        return "MALFORMED"

    return "GO"


def compute_sha256(path: Path) -> Optional[str]:
    """Compute SHA256 of a file."""
    if not path.exists():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def validate_source_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Validate source files referenced in the manifest."""
    if not manifest_path.exists():
        return {"status": "UNKNOWN", "sources": {}}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "MALFORMED", "sources": {}}

    manifest_file_status = get_file_status(manifest_path)

    sources_out = {}
    has_stale = manifest_file_status == "STALE"
    has_no_go = False
    has_quarantined = manifest_file_status == "QUARANTINED"

    authorities = {
        "naics_2022": "US Census Bureau",
        "onet_28": "O*NET Center",
        "bls_oews_24": "Bureau of Labor Statistics"
    }

    for key, info in manifest.items():
        local_path_str = info.get("local_path")
        label = info.get("source_name", key)
        authority = authorities.get(key, "Unknown Authority")
        
        if not local_path_str:
            sources_out[key] = {
                "source_id": key,
                "label": label,
                "path": "",
                "authority": authority,
                "allowed_for_live_ui": False,
                "freshness": "unknown",
                "last_modified": None,
                "age_seconds": None,
                "checksum_sha256": None,
                "validation_method": "SHA256 checksum matching",
                "fallback_policy": "Local static cache",
                "status": "UNKNOWN"
            }
            has_no_go = True
            continue

        local_path = Path(local_path_str)
        if not local_path.is_absolute():
            local_path = Path(__file__).resolve().parent.parent.parent / local_path

        mtime_str = None
        age_seconds = None
        if local_path.exists():
            try:
                mtime = local_path.stat().st_mtime
                mtime_str = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
                age_seconds = datetime.now().timestamp() - mtime
            except Exception:
                pass

        f_status = get_file_status(local_path)
        expected_checksum = info.get("checksum")
        actual_checksum = compute_sha256(local_path)

        freshness = "unknown"
        if f_status == "STALE":
            freshness = "stale"
            has_stale = True
        elif f_status == "GO":
            freshness = "fresh"
        elif f_status == "QUARANTINED":
            freshness = "quarantined"
            has_quarantined = True
        elif f_status == "MALFORMED":
            freshness = "malformed"
            has_no_go = True
        elif f_status == "UNKNOWN":
            freshness = "unknown"
            has_no_go = True

        status_val = f_status
        if local_path.exists():
            if actual_checksum != expected_checksum:
                status_val = "MALFORMED"
                has_no_go = True
        else:
            status_val = "UNKNOWN"
            has_no_go = True

        sources_out[key] = {
            "source_id": key,
            "label": label,
            "path": str(local_path),
            "authority": authority,
            "allowed_for_live_ui": True,
            "freshness": freshness,
            "last_modified": mtime_str,
            "age_seconds": age_seconds,
            "checksum_sha256": actual_checksum,
            "validation_method": "SHA256 checksum matching",
            "fallback_policy": "Local static cache",
            "status": status_val
        }

    if has_quarantined:
        overall_status = "QUARANTINED"
    elif has_no_go:
        overall_status = "NO_GO"
    elif has_stale:
        overall_status = "STALE"
    else:
        overall_status = "GO"

    try:
        manifest_mtime = manifest_path.stat().st_mtime
        last_updated_str = datetime.fromtimestamp(manifest_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        last_updated_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "status": overall_status,
        "last_updated": last_updated_str,
        "sources": sources_out
    }



def validate_brain_runtime_proof(usage_paths: list, outcome_paths: list) -> Dict[str, Any]:
    """Evaluate if BRAIN has non-fallback real execution proof."""
    usages = []
    outcomes = {}

    # Load usage ledger(s)
    for p in usage_paths:
        path = Path(p)
        if path.exists():
            # Check quarantine on ledger path
            if "_quarantine_" in str(path) or "quarantine" in str(path).lower():
                return {"status": "QUARANTINED", "go_no_go": "NO_GO", "evidence": {}}
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        usages.append(json.loads(line))
            except Exception:
                return {"status": "MALFORMED", "go_no_go": "NO_GO", "evidence": {}}

    # Load outcome ledger(s)
    for p in outcome_paths:
        path = Path(p)
        if path.exists():
            if "_quarantine_" in str(path) or "quarantine" in str(path).lower():
                return {"status": "QUARANTINED", "go_no_go": "NO_GO", "evidence": {}}
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        obj = json.loads(line)
                        u_id = obj.get("usage_id")
                        if u_id:
                            outcomes[u_id] = obj
            except Exception:
                return {"status": "MALFORMED", "go_no_go": "NO_GO", "evidence": {}}

    # Find valid real execution proof
    real_execution = None
    for u in reversed(usages):
        # Exclude fallback execution
        if u.get("fallback_used") is True:
            continue
        # Exclude dashboard/RAG/introspection surfaces
        surface = u.get("execution_surface", "")
        if not surface or any(x in surface.lower() for x in ["dashboard", "rag", "introspection"]):
            continue

        # Check if outcome linked and is completed/successful
        u_id = u.get("usage_id")
        outcome = outcomes.get(u_id)
        if outcome and outcome.get("status") == "COMPLETED":
            real_execution = {
                "has_real_execution": True,
                "fallback_used": False,
                "execution_surface": surface,
                "usage_id": u_id,
                "outcome_linked": True,
                "outcome_status": "COMPLETED",
                "timestamp": u.get("timestamp"),
                "champion_id": u.get("champion_id")
            }
            break

    if real_execution:
        return {
            "status": "LIVE",
            "go_no_go": "GO",
            "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "evidence": real_execution
        }
    else:
        return {
            "status": "NO_GO",
            "go_no_go": "NO_GO",
            "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "evidence": {
                "has_real_execution": False,
                "fallback_used": True,
                "execution_surface": None,
                "usage_id": None,
                "outcome_linked": False,
                "outcome_status": None
            }
        }
