# -*- coding: utf-8 -*-
"""
backend/brain/live_runtime_aggregator.py
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

from backend.brain.runtime_truth_validator import (
    get_file_status,
    validate_source_manifest,
    validate_brain_runtime_proof
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRACKER_DATA = PROJECT_ROOT / "has_live_project_tracker" / "data"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def aggregate_source_authority() -> Dict[str, Any]:
    manifest_path = PROJECT_ROOT / "data" / "prompt_brain" / "source_manifest.json"
    res = validate_source_manifest(manifest_path)
    out_path = TRACKER_DATA / "source_authority_manifest.json"
    _write_json(out_path, res)
    return res


def aggregate_brain_runtime_truth() -> Dict[str, Any]:
    usage_paths = [
        str(PROJECT_ROOT / "data" / "prompt_brain" / "runtime_usage_ledger.jsonl"),
        str(PROJECT_ROOT / "data" / "prompt_brain" / "champion_runtime_usage.jsonl")
    ]
    outcome_paths = [
        str(PROJECT_ROOT / "data" / "prompt_brain" / "outcome_feedback_ledger.jsonl"),
        str(PROJECT_ROOT / "data" / "prompt_brain" / "champion_outcome_feedback.jsonl")
    ]
    res = validate_brain_runtime_proof(usage_paths, outcome_paths)
    out_path = TRACKER_DATA / "brain_runtime_truth.json"
    _write_json(out_path, res)
    return res


def aggregate_factory_runtime_truth() -> Dict[str, Any]:
    factories = {
        "software": PROJECT_ROOT / "data" / "prompt_brain" / "convergence_status.json",
        "music": PROJECT_ROOT / "data" / "prompt_brain" / "music" / "convergence_status.json",
        "research": PROJECT_ROOT / "data" / "prompt_brain" / "research" / "convergence_status.json"
    }

    factories_out = {}
    all_go = True

    for name, path in factories.items():
        status = get_file_status(path)
        if status != "GO":
            factories_out[name] = {"status": status}
            all_go = False
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = data.get("state")
            mean_score = data.get("mean_score")
            gen = data.get("generation")
            
            f_go = state in ["IMPROVING", "CONVERGED"]
            if not f_go:
                all_go = False

            factories_out[name] = {
                "status": "GO" if f_go else "NO_GO",
                "state": state,
                "mean_score": mean_score,
                "generation": gen,
                "freshness": "fresh"
            }
        except Exception:
            factories_out[name] = {"status": "MALFORMED"}
            all_go = False

    res = {
        "status": "GO" if all_go else "NO_GO",
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "factories": factories_out
    }
    out_path = TRACKER_DATA / "factory_runtime_truth.json"
    _write_json(out_path, res)
    return res


def aggregate_reasoning_graph() -> Dict[str, Any]:
    # Dynamic graph structure mapping factories, sources, ledgers, and gates
    sources_res = aggregate_source_authority()
    brain_res = aggregate_brain_runtime_truth()
    factory_res = aggregate_factory_runtime_truth()

    nodes = [
        {
            "id": "source-naics",
            "type": "source",
            "label": "NAICS 2022",
            "status": sources_res.get("sources", {}).get("naics_2022", {}).get("status", "UNKNOWN"),
            "source_authority_ref": "naics_2022"
        },
        {
            "id": "source-onet",
            "type": "source",
            "label": "O*NET 28.0",
            "status": sources_res.get("sources", {}).get("onet_28", {}).get("status", "UNKNOWN"),
            "source_authority_ref": "onet_28"
        },
        {
            "id": "source-bls",
            "type": "source",
            "label": "BLS OEWS 2024",
            "status": sources_res.get("sources", {}).get("bls_oews_24", {}).get("status", "UNKNOWN"),
            "source_authority_ref": "bls_oews_24"
        },
        {"id": "factory-software", "type": "factory", "label": "HASF (Software)", "status": factory_res.get("factories", {}).get("software", {}).get("status", "UNKNOWN")},
        {"id": "factory-music", "type": "factory", "label": "HMF (Music)", "status": factory_res.get("factories", {}).get("music", {}).get("status", "UNKNOWN")},
        {"id": "factory-research", "type": "factory", "label": "HRF (Research)", "status": factory_res.get("factories", {}).get("research", {}).get("status", "UNKNOWN")},
        {"id": "ledger-usage", "type": "ledger", "label": "Runtime Usage Ledger", "status": "GO" if brain_res.get("status") == "LIVE" else "NO_GO"},
        {"id": "ledger-outcome", "type": "ledger", "label": "Outcome Feedback Ledger", "status": "GO" if brain_res.get("status") == "LIVE" else "NO_GO"}
    ]

    edges = [
        {"source": "source-naics", "target": "factory-software", "label": "provides industry codes"},
        {"source": "source-onet", "target": "factory-software", "label": "provides tasks"},
        {"source": "source-bls", "target": "factory-software", "label": "provides employment stats"},
        {"source": "factory-software", "target": "ledger-usage", "label": "logs prompt execution"},
        {"source": "ledger-usage", "target": "ledger-outcome", "label": "links execution to outcome"}
    ]

    # Reasoning graph status depends on factories and sources
    status_val = "GO"
    if sources_res.get("status") != "GO" or factory_res.get("status") != "GO" or brain_res.get("status") != "LIVE":
        # If the only issue is staleness, overall status can be CONDITIONAL
        is_stale_only = True
        if sources_res.get("status") not in ["GO", "STALE"]:
            is_stale_only = False
        for name, info in factory_res.get("factories", {}).items():
            if info.get("status") not in ["GO", "STALE"]:
                is_stale_only = False
        if brain_res.get("status") != "LIVE":
            is_stale_only = False
            
        if is_stale_only:
            status_val = "CONDITIONAL"
        else:
            status_val = "NO_GO"

    res = {
        "status": status_val,
        "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "nodes": nodes,
        "edges": edges
    }
    out_path = TRACKER_DATA / "reasoning_graph.json"
    _write_json(out_path, res)
    return res


def read_champion_runtime_usage() -> Dict[str, Any]:
    path = PROJECT_ROOT / "data" / "prompt_brain" / "champion_runtime_usage.jsonl"
    usages = []
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    usages.append(json.loads(line))
        except Exception:
            pass
    return {"usages": usages}


def read_champion_outcome_feedback() -> Dict[str, Any]:
    path = PROJECT_ROOT / "data" / "prompt_brain" / "champion_outcome_feedback.jsonl"
    outcomes = []
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    outcomes.append(json.loads(line))
        except Exception:
            pass
    return {"outcomes": outcomes}


