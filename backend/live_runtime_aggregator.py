from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import backend models safely
def get_cockpit_data() -> dict[str, Any]:
    base_dir = Path(__file__).parent.parent
    now_str = datetime.now(timezone.utc).isoformat()
    
    # 1. Runtime Process Event Bus
    try:
        from backend.runtime_process import RuntimeProcessBus
        bus = RuntimeProcessBus()
        events = bus.tail(20)
        has_failed = any(e.get("state") in ("FAILED", "BLOCKED", "DENIED") for e in events)
        rp_truth = "FAILED" if has_failed else ("EMPTY" if not events else "LIVE")
        rp_data = {
            "truth": rp_truth,
            "source": "/api/v1/runtime/process/events",
            "last_updated": now_str,
            "items": events
        }
    except Exception as exc:
        rp_data = {
            "truth": "ERROR",
            "source": "/api/v1/runtime/process/events",
            "last_updated": now_str,
            "error": str(exc),
            "items": []
        }

    # 2. Local Models health
    try:
        from backend.local_runtime_supervisor import SUPERVISOR
        status = SUPERVISOR.status()
        providers = status.get("providers", [])
        if not providers:
            lm_truth = "EMPTY"
        else:
            any_unreachable = any(not p.get("reachable", False) for p in providers)
            all_unreachable = all(not p.get("reachable", False) for p in providers)
            if all_unreachable:
                lm_truth = "FAILED"
            elif any_unreachable:
                lm_truth = "DEGRADED"
            else:
                lm_truth = "LIVE"
        lm_data = {
            "truth": lm_truth,
            "source": "/api/v1/runtime/local-supervisor/status",
            "last_updated": now_str,
            "providers": providers
        }
    except Exception as exc:
        lm_data = {
            "truth": "ERROR",
            "source": "/api/v1/runtime/local-supervisor/status",
            "last_updated": now_str,
            "error": str(exc),
            "providers": []
        }

    # 3. Model Router Status
    try:
        from backend.model_router import model_registry
        local_first = model_registry.is_local_first()
        local_providers = model_registry.get_enabled_local_providers()
        paid_providers = model_registry.get_enabled_paid_providers()
        if local_first:
            mr_truth = "LIVE" if local_providers else "DEGRADED"
        else:
            mr_truth = "LIVE" if paid_providers else "FAILED"
        mr_data = {
            "truth": mr_truth,
            "source": "/api/v1/models/status",
            "last_updated": now_str,
            "local_first": local_first,
            "default_model": model_registry.get_default_model(),
            "enabled_local_providers": local_providers
        }
    except Exception as exc:
        mr_data = {
            "truth": "ERROR",
            "source": "/api/v1/models/status",
            "last_updated": now_str,
            "error": str(exc)
        }

    # 4. Escalations Approval Queue
    try:
        from backend.model_router.google_frontier import load_approvals
        app_data = load_approvals()
        pending = [
            app for app in app_data.get("approvals", [])
            if app.get("status") == "PENDING" and (not app.get("expires_at") or app.get("expires_at") > now_str)
        ]
        esc_truth = "APPROVAL_REQUIRED" if pending else "EMPTY"
        esc_data = {
            "truth": esc_truth,
            "source": "/api/v1/escalations/pending",
            "last_updated": now_str,
            "pending": pending
        }
    except Exception as exc:
        esc_data = {
            "truth": "ERROR",
            "source": "/api/v1/escalations/pending",
            "last_updated": now_str,
            "error": str(exc),
            "pending": []
        }

    # 5. Detections Health
    try:
        from backend.detection_events import DetectionEventBus
        det_bus = DetectionEventBus()
        recent_detections = det_bus.tail(20)
        has_critical = any(d.get("severity") in ("high", "critical") for d in recent_detections)
        det_truth = "DEGRADED" if has_critical else ("EMPTY" if not recent_detections else "LIVE")
        det_data = {
            "truth": det_truth,
            "source": "/api/v1/detections/health",
            "last_updated": now_str,
            "recent_events": recent_detections
        }
    except Exception as exc:
        det_data = {
            "truth": "ERROR",
            "source": "/api/v1/detections/health",
            "last_updated": now_str,
            "error": str(exc),
            "recent_events": []
        }

    # 6. Production Readiness Score
    try:
        # Avoid circular imports in main.py by reading qa_evidence_matrix.json directly
        matrix_path = base_dir / "config" / "qa_evidence_matrix.json"
        score = 0
        status_val = "UNKNOWN"
        if matrix_path.exists():
            matrix_data = json.loads(matrix_path.read_text(encoding="utf-8"))
            summary = matrix_data.get("summary", {})
            total_tests = summary.get("total_tests", 1)
            tests_pass = summary.get("tests_pass", 0)
            score = round((tests_pass / max(total_tests, 1)) * 100, 2)
            status_val = summary.get("matrix_status", "LIVE")
        
        # Read the release_authorization.json to get go/no-go status
        go_no_go = "NO-GO"
        auth_path = base_dir / "config" / "release_authorization.json"
        if auth_path.exists():
            auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
            if auth_data.get("authorized") is True and auth_data.get("verdict") == "GO":
                go_no_go = "GO"
            else:
                go_no_go = "PENDING_VERIFICATION"
        
        pr_data = {
            "truth": status_val if status_val != "UNKNOWN" else "LIVE",
            "source": "/api/v1/production-readiness",
            "last_updated": now_str,
            "score": score,
            "go_no_go": go_no_go
        }
    except Exception as exc:
        pr_data = {
            "truth": "ERROR",
            "source": "/api/v1/production-readiness",
            "last_updated": now_str,
            "error": str(exc),
            "score": 0,
            "go_no_go": "NO-GO"
        }

    # 7. QA Evidence Matrix Controls / Tests
    try:
        matrix_path = base_dir / "config" / "qa_evidence_matrix.json"
        controls_count = 0
        tests_count = 0
        tests_passed = 0
        if matrix_path.exists():
            matrix_data = json.loads(matrix_path.read_text(encoding="utf-8"))
            controls_count = len(matrix_data.get("controls", []))
            summary = matrix_data.get("summary", {})
            tests_count = summary.get("total_tests", 0)
            tests_passed = summary.get("tests_pass", 0)
        
        ev_data = {
            "truth": "LIVE",
            "source": "/api/v1/qa/evidence-matrix",
            "last_updated": now_str,
            "controls": controls_count,
            "tests": tests_count,
            "tests_passed": tests_passed
        }
    except Exception as exc:
        ev_data = {
            "truth": "ERROR",
            "source": "/api/v1/qa/evidence-matrix",
            "last_updated": now_str,
            "error": str(exc),
            "controls": 0,
            "tests": 0
        }

    # 8. Immutability
    imm_data = {
        "truth": "ASSUMPTION",
        "source": "pending PR-14 verification test",
        "last_updated": now_str,
        "status": "NOT_VERIFIED"
    }

    # 9. Local Outage Queue
    try:
        # Check if local_outage_queue.jsonl exists and count elements
        outage_path = base_dir / "audit" / "local_outage_queue.jsonl"
        items_count = 0
        if outage_path.exists():
            items_count = len(outage_path.read_text(encoding="utf-8").splitlines())
        oq_data = {
            "truth": "LIVE" if items_count == 0 else "DEGRADED",
            "source": "audit/local_outage_queue.jsonl",
            "last_updated": now_str,
            "queued_items_count": items_count
        }
    except Exception as exc:
        oq_data = {
            "truth": "ERROR",
            "source": "audit/local_outage_queue.jsonl",
            "last_updated": now_str,
            "error": str(exc),
            "queued_items_count": 0
        }

    # 10. Port Hardening Audit
    try:
        port_path = base_dir / "config" / "port_hardening_audit.json"
        overall_status = "UNKNOWN"
        ports_count = 0
        if port_path.exists():
            port_data = json.loads(port_path.read_text(encoding="utf-8"))
            summary = port_data.get("summary", {})
            overall_status = summary.get("overall_status", "UNKNOWN")
            ports_count = len(port_data.get("swarm_ports", [])) + len(port_data.get("non_swarm_lan_ports", []))
        
        ph_data = {
            "truth": "LIVE" if overall_status == "PASS" else "FAILED",
            "source": "config/port_hardening_audit.json",
            "last_updated": now_str,
            "overall_status": overall_status,
            "ports_count": ports_count
        }
    except Exception as exc:
        ph_data = {
            "truth": "ERROR",
            "source": "config/port_hardening_audit.json",
            "last_updated": now_str,
            "error": str(exc),
            "overall_status": "ERROR",
            "ports_count": 0
        }

    # 11. Autonomy Error Budget
    try:
        from backend.remediation_safety import calculate_error_budget_and_burn_rate, get_autonomy_level
        remaining_budget, burn_rate = calculate_error_budget_and_burn_rate()
        matrix_path = base_dir / "config" / "qa_evidence_matrix.json"
        score = 0
        if matrix_path.exists():
            matrix_data = json.loads(matrix_path.read_text(encoding="utf-8"))
            summary = matrix_data.get("summary", {})
            total_tests = summary.get("total_tests", 1)
            tests_pass = summary.get("tests_pass", 0)
            score = round((tests_pass / max(total_tests, 1)) * 100, 2)
            
        autonomy_level = get_autonomy_level(score, remaining_budget, burn_rate)
        
        ab_data = {
            "truth": "LIVE" if remaining_budget > 20 else "DEGRADED",
            "source": "/api/v1/readiness/budget-report",
            "last_updated": now_str,
            "remaining_error_budget": remaining_budget,
            "burn_rate": burn_rate,
            "autonomy_level": autonomy_level
        }
    except Exception as exc:
        ab_data = {
            "truth": "ERROR",
            "source": "/api/v1/readiness/budget-report",
            "last_updated": now_str,
            "error": str(exc),
            "remaining_error_budget": 0,
            "burn_rate": 0,
            "autonomy_level": "UNKNOWN"
        }

    # 12. Device Service Registry
    try:
        leases_path = base_dir / "config" / "cluster_worker_profiles.json"
        devices_count = 0
        if leases_path.exists():
            leases_data = json.loads(leases_path.read_text(encoding="utf-8"))
            devices_count = len(leases_data.get("workers", []))
            if not devices_count:
                devices_count = len(leases_data)
        
        dr_data = {
            "truth": "LIVE" if devices_count > 0 else "EMPTY",
            "source": "/api/v1/devices/service-registry",
            "last_updated": now_str,
            "devices_count": devices_count
        }
    except Exception as exc:
        dr_data = {
            "truth": "ERROR",
            "source": "/api/v1/devices/service-registry",
            "last_updated": now_str,
            "devices_count": 0
        }

    return {
        "truth": "LIVE",
        "generated_at": now_str,
        "cards": {
            "runtime_process": rp_data,
            "local_models": lm_data,
            "model_router": mr_data,
            "escalations": esc_data,
            "detections": det_data,
            "readiness": pr_data,
            "evidence": ev_data,
            "immutability": imm_data,
            "local_outage_queue": oq_data,
            "port_hardening": ph_data,
            "autonomy_budget": ab_data,
            "device_registry": dr_data
        }
    }
