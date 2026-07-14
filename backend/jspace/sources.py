"""Read-only collectors over existing HELM surfaces.

These functions never mutate HELM state. They only open files/ledgers for observation.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_error": "unreadable", "path": str(path)}


def _read_jsonl_tail(path: Path, n: int = 50) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for line in lines[-n:]:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def collect_runtime_snapshot(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo_root) if repo_root else ROOT
    pointer = root / "coordination" / "council" / "active_runtime_source.json"
    lease_dir = root / "coordination" / "leases"
    ptr = _read_json(pointer) or {}
    locks = []
    if lease_dir.exists():
        for p in sorted(lease_dir.glob("*.lock")):
            try:
                locks.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                locks.append({"path": str(p), "status": "UNREADABLE"})
    ledger_path = Path(ptr["ledger_path"]) if ptr.get("ledger_path") else None
    lease_events = _read_jsonl_tail(ledger_path, 80) if ledger_path else []
    soak_cfg = None
    evidence_dir = ptr.get("evidence_dir")
    if evidence_dir:
        cfg_p = Path(evidence_dir).parent / "soak_config.json"
        if not cfg_p.exists():
            cfg_p = Path(evidence_dir) / "soak_config.json"
        # package root is parent of daemon/
        pkg = Path(evidence_dir).parent
        cfg_p = pkg / "soak_config.json"
        soak_cfg = _read_json(cfg_p)
    return {
        "pointer": ptr,
        "pointer_path": str(pointer.relative_to(root)) if pointer.exists() else None,
        "active_locks": locks,
        "lease_events_tail": lease_events,
        "soak_config": soak_cfg,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def collect_authority_snapshot(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo_root) if repo_root else ROOT
    decisions = root / "coordination" / "founder" / "authority_binding_ledger.jsonl"
    autonomous = root / "coordination" / "founder" / "autonomous_decision_ledger.jsonl"
    return {
        "authority_binding_tail": _read_jsonl_tail(decisions, 40),
        "autonomous_decision_tail": _read_jsonl_tail(autonomous, 40),
        "paths": {
            "authority_binding_ledger": str(decisions.relative_to(root)) if decisions.exists() else None,
            "autonomous_decision_ledger": str(autonomous.relative_to(root)) if autonomous.exists() else None,
        },
    }


def collect_security_snapshot(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo_root) if repo_root else ROOT
    posture = root / "coordination" / "security" / "helm_control_posture.json"
    conmon = root / "coordination" / "security" / "conmon_ledger.jsonl"
    return {
        "control_posture": _read_json(posture),
        "conmon_tail": _read_jsonl_tail(conmon, 5),
        "paths": {
            "helm_control_posture": str(posture.relative_to(root)) if posture.exists() else None,
            "conmon_ledger": str(conmon.relative_to(root)) if conmon.exists() else None,
        },
    }


def collect_spend_snapshot(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo_root) if repo_root else ROOT
    spend = root / "coordination" / "council" / "spend_ledger.jsonl"
    return {
        "spend_tail": _read_jsonl_tail(spend, 30),
        "path": str(spend.relative_to(root)) if spend.exists() else None,
    }


def collect_wall_inputs(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Bundle used by all sentinels for one cycle."""
    return {
        "runtime": collect_runtime_snapshot(repo_root),
        "authority": collect_authority_snapshot(repo_root),
        "security": collect_security_snapshot(repo_root),
        "spend": collect_spend_snapshot(repo_root),
    }
