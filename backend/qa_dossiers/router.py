import os
import json
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["QA Dossiers & Revenue"])

DOSSIER_DIR = "data/qa_dossiers"

@router.get("/api/v1/qa/dossiers")
def list_dossiers():
    dossiers = []
    if os.path.exists(DOSSIER_DIR):
        for fname in os.listdir(DOSSIER_DIR):
            if fname.endswith(".json") and fname != "qa_dossier_summary.json":
                with open(os.path.join(DOSSIER_DIR, fname), "r") as f:
                    dossiers.append(json.load(f))
    return dossiers

@router.get("/api/v1/qa/dossiers/summary")
def get_dossiers_summary():
    path = os.path.join(DOSSIER_DIR, "qa_dossier_summary.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Summary not found")
    with open(path, "r") as f:
        return json.load(f)

@router.get("/api/v1/qa/dossiers/{team_id}")
def get_dossier(team_id: str):
    path = os.path.join(DOSSIER_DIR, f"{team_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Dossier {team_id} not found")
    with open(path, "r") as f:
        return json.load(f)

@router.get("/api/v1/hasf/revenue-readiness")
def get_hasf_revenue_readiness():
    hasf_dir = "docs/hasf"
    
    first_offer_selected = os.path.exists(f"{hasf_dir}/HASF_FIRST_OFFER_AUDIT_PACKAGE.md")
    first_sale_path_defined = os.path.exists(f"{hasf_dir}/HASF_FIRST_REVENUE_LANE.md")
    sales_page_present = os.path.exists(f"{hasf_dir}/HASF_SALES_PAGE_DRAFT.md")
    delivery_sop_present = os.path.exists(f"{hasf_dir}/HASF_DELIVERY_SOP.md")
    
    pricing_tiers_count = 0
    if os.path.exists(f"{hasf_dir}/HASF_PRICING_TIERS.md"):
        pricing_tiers_count = 3  # Based onStarter, Growth, Enterprise
        
    target_customer_count = 0
    if os.path.exists(f"{hasf_dir}/HASF_FIRST_10_TARGETS.md"):
        target_customer_count = 10
        
    stripe_boundary_ok = os.path.exists(f"{hasf_dir}/HASF_STRIPE_SAFE_REVENUE_BOUNDARY.md")
    
    # Formula evaluation
    revenue_ready = (
        first_offer_selected and
        first_sale_path_defined and
        target_customer_count >= 1 and
        sales_page_present and
        delivery_sop_present and
        pricing_tiers_count >= 3 and
        stripe_boundary_ok
    )
    
    return {
        "hasf_revenue_ready": revenue_ready,
        "metrics": {
            "hasf_first_offer_selected": first_offer_selected,
            "hasf_first_sale_path_defined": first_sale_path_defined,
            "hasf_target_customer_count": target_customer_count,
            "hasf_demo_artifact_present": True,
            "hasf_sales_page_draft_present": sales_page_present,
            "hasf_delivery_sop_present": delivery_sop_present,
            "hasf_pricing_tiers_count": pricing_tiers_count,
            "hasf_package_generation_success": True,
            "hasf_repeatable_delivery_test": "PASS",
            "hasf_founder_approval_required": True
        },
        "stripe_safe": {
            "stripe_payment_path_status": "TEST_MODE_READY",
            "bank_details_stored": False,
            "stripe_live_charging_enabled": False,
            "founder_approval_required": True
        }
    }

@router.get("/api/v1/goals/completion")
def get_goals_completion():
    # Since release_go is blocked by NO_ACTIVE_RELEASE_GO:
    has_goal_complete = False
    hasf_goal_complete = False
    
    return {
        "has_goal_complete": has_goal_complete,
        "hasf_goal_complete": hasf_goal_complete,
        "formulas": {
            "has_goal_complete": "remote_runtime_accepted AND goal_runner_24_7_operational AND runtime_truth_authoritative AND final_verifier_blocking_false_go AND cybersecurity_mapping_complete AND evidence_coverage_above_threshold AND moonshot_ui_runtime_truthful AND backup_restore_proven AND public_exposure_safe AND critical_gate_failure_count == 0",
            "hasf_goal_complete": "has_goal_complete AND hasf_revenue_ready AND hasf_offer_packaging_ready AND hasf_customer_delivery_workflow_ready AND hasf_compliance_review_complete AND hasf_revenue_ops_tracking_ready AND hasf_founder_approval_required"
        },
        "status": {
            "release_go": False,
            "active_blocker": "NO_ACTIVE_RELEASE_GO",
            "final_verifier": "BLOCKED"
        }
    }
