from __future__ import annotations
import json
from datetime import datetime, timezone
from backend.runtime_execution_store import (
    list_tool_calls,
    list_redaction_records,
    list_approval_gates,
    list_validation_evidence
)
from backend.ledger_manager import get_ledger_blocks

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def generate_runtime_execution_audit() -> dict:
    tool_calls = list_tool_calls()
    redactions = list_redaction_records()
    approvals = list_approval_gates()
    validation_evidence = list_validation_evidence()
    blocks = get_ledger_blocks()

    # Track metrics
    tool_calls_checked = len(tool_calls)
    tool_calls_with_trace = sum(1 for tc in tool_calls if tc.get("trace_id"))
    tool_calls_with_evidence = sum(1 for tc in tool_calls if tc.get("has_evidence") == 1)
    
    redactions_applied = sum(r.get("redactions_count", 0) for r in redactions)
    
    # 1. Check for solved without validation:
    # Any HOCHSTER_SOLUTION_GENERATED in the ledger must have a corresponding validation evidence record.
    solved_request_ids = []
    for b in blocks:
        evt = b.get("event", {})
        action = evt.get("action", {})
        meta = evt.get("metadata", {})
        if action.get("type") == "HOCHSTER_SOLUTION_GENERATED" or evt.get("action", {}).get("type") == "HOCHSTER_SOLUTION_GENERATED":
            req_id = meta.get("request_id")
            if req_id and req_id not in solved_request_ids:
                solved_request_ids.append(req_id)
                
    validation_request_ids = {ve["request_id"] for ve in validation_evidence}
    solved_without_validation = 0
    solved_without_val_details = []
    
    for req_id in solved_request_ids:
        if req_id not in validation_request_ids:
            solved_without_validation += 1
            solved_without_val_details.append(req_id)

    # 2. Check for approval required actions and bypasses
    # We count approval gates in the DB
    approval_required_actions = len(approvals)
    approval_bypass_findings = []
    
    # In main.py, check if there's any ledger event representing a high-risk action
    # (e.g. action.type == "HOCHSTER_HIGH_RISK_ACTION_EXECUTED")
    # For any high-risk action, there must be a approved gate.
    for b in blocks:
        evt = b.get("event", {})
        action = evt.get("action", {})
        meta = evt.get("metadata", {})
        if "override-safety-limits" in action.get("summary", "") or action.get("type") == "HOCHSTER_HIGH_RISK_ACTION_EXECUTED":
            req_id = meta.get("request_id")
            corr_id = meta.get("correlation_id")
            
            # Find approval gate
            approved = False
            for app in approvals:
                if (app["request_id"] == req_id or app["correlation_id"] == corr_id) and app["status"] == "approved":
                    approved = True
                    break
            if not approved:
                approval_bypass_findings.append(
                    f"Bypass found: High risk action execution for request {req_id or corr_id} without approved gate"
                )

    blockers = []
    if tool_calls_with_trace < tool_calls_checked:
        blockers.append(f"Tool call missing trace ID: {tool_calls_checked - tool_calls_with_trace} occurrences")
    if tool_calls_with_evidence < tool_calls_checked:
        blockers.append(f"Tool call missing evidence: {tool_calls_checked - tool_calls_with_evidence} occurrences")
    if solved_without_validation > 0:
        blockers.append(f"Request solved without validation evidence: {solved_without_val_details}")
    if len(approval_bypass_findings) > 0:
        blockers.append(f"Approval gate bypass detected: {approval_bypass_findings}")

    status = "PASS" if len(blockers) == 0 else "BLOCK"

    return {
        "generated_at": now_iso(),
        "base_url": "http://localhost:8000",
        "tool_calls_checked": tool_calls_checked,
        "tool_calls_with_trace": tool_calls_with_trace,
        "tool_calls_with_evidence": tool_calls_with_evidence,
        "redactions_applied": redactions_applied,
        "solved_without_validation": solved_without_validation,
        "approval_required_actions": approval_required_actions,
        "approval_bypass_findings": approval_bypass_findings,
        "blockers": blockers,
        "status": status
    }

def generate_tool_call_trace_summary() -> dict:
    return {
        "tool_calls": list_tool_calls()
    }

def generate_redaction_report() -> dict:
    return {
        "redaction_events": list_redaction_records()
    }

def generate_approval_gate_report() -> dict:
    return {
        "approval_events": list_approval_gates()
    }
