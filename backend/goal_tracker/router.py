from fastapi import APIRouter
from backend.goal_tracker.pert_model import get_goal_pert_analysis

router = APIRouter(prefix="/api/v1/goal", tags=["Goal PERT Tracker"])

@router.get("/pert")
def get_goal_pert():
    return get_goal_pert_analysis()

@router.post("/pert/recalculate")
def post_goal_pert_recalculate():
    # In-memory calculations are dynamic, so this is equivalent to get
    return get_goal_pert_analysis()

@router.get("/live-tracker")
def get_goal_live_tracker():
    return get_goal_pert_analysis()

@router.get("/critical-path")
def get_goal_critical_path():
    analysis = get_goal_pert_analysis()
    return {
        "critical_path": analysis["critical_path"],
        "expected_completion_minutes": analysis["expected_completion_minutes"],
        "confidence": analysis["confidence"]
    }
