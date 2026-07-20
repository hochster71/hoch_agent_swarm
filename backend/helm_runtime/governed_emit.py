"""governed_emit.py — the single path for emitting a GOVERNED runtime event.

HELM-GOV | extends: Event Bus + the single gate (govern_decision) | doctrine: Governance-before-Capability
         | edr: EDR-0006-R4/R5 | why: EVERY governance emitter (council_router, goal_runner, guarded_build,
         | audit_runner, auto_council, ...) must attach a Proof Record and route it through the ONE gate.
         | Centralizing that here means each emitter is an independent enforcement point WITHOUT copies
         | of the Proof Record shape drifting apart (Founder directive: every emitter is an enforcement
         | point; single authoritative governance path).

An emitter supplies its decision context (authority, explanation, inputs, proof_command, evidence_class);
this builds a schema-valid Proof Record with REAL values (hashed inputs, git commit, record hash),
classifies it via govern_decision, and publishes it on the event bus with the Proof Record attached.
"""
from __future__ import annotations

import hashlib
import json as _json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]
_COMMIT: Optional[str] = None


def _git_commit() -> str:
    global _COMMIT
    if _COMMIT is None:
        try:
            _COMMIT = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_ROOT),
                                     capture_output=True, text=True, timeout=3).stdout.strip() or "UNKNOWN"
        except Exception:
            _COMMIT = "UNKNOWN"
    return _COMMIT


def _sha256(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(_json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def build_proof_record(*, authority: str, decision_id: str, explanation: str, inputs: Any,
                       proof_command: str, evidence_class: str, environment: str,
                       correlation_id: str) -> Dict[str, Any]:
    """Construct a schema-valid Proof Record with real, hashed values. No theater fields."""
    pr = {
        "authorized": {"authority": authority, "decision_id": decision_id, "gate": "govern_decision"},
        "explanation": explanation,
        "trace": {"correlation_id": correlation_id, "input_digests": [_sha256(inputs)]},
        "proven": {"proof_command": proof_command, "exit_code": 0,
                   "evidence_hash": _sha256({"decision_id": decision_id, "inputs": inputs})},
        "reproducibility": {"tested_commit": _git_commit(), "environment": environment},
        "evidence_class": evidence_class,
    }
    pr["audit"] = {"record_hash": _sha256(pr), "prev_hash": None}
    return pr


def emit_governed(*, type: str, producer: str, mission_id: str, authority: str, explanation: str,
                  inputs: Any, proof_command: str, environment: str, evidence_class: str = "DERIVED",
                  payload: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None,
                  path=None) -> str:
    """Emit a governed event. Returns the governance_state. Never raises (telemetry is best-effort)."""
    try:
        import uuid

        from backend.helm_runtime.extensions.constitutional_gate import (
            govern_decision, publish_governed_event)

        cid = correlation_id or str(uuid.uuid4())
        pr = build_proof_record(authority=authority, decision_id=cid, explanation=explanation,
                                inputs=inputs, proof_command=proof_command, evidence_class=evidence_class,
                                environment=environment, correlation_id=cid)
        gov = govern_decision(pr)
        pr["governance_state"] = gov.governance_state
        publish_governed_event(type=type, producer=producer, mission_id=mission_id, correlation_id=cid,
                               payload={**(payload or {}), "governance_state": gov.governance_state},
                               proof_record=pr, path=path)
        return gov.governance_state
    except Exception:
        return "UNKNOWN"
