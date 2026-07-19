from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.audit_factory.service import HAFService
from backend.audit_factory.promotion_gate import evaluate_promotion, PromotionDecision

haf_router = APIRouter(prefix="/api/v1/haf", tags=["HAF"])
service = HAFService()

class AssessmentRequest(BaseModel):
    profile: str = "helm_common"
    scope: str = "HELM_COMMON"

class ConMonRequest(BaseModel):
    file_path: str

class PromotionRequest(BaseModel):
    scope: str
    target_level: str

@haf_router.get("/status")
def get_haf_status():
    return {
        "status": "ONLINE",
        "service": "HOCH Audit Factory",
        "version": "v0.1",
        "doctrine": "no_fake_green"
    }

@haf_router.get("/catalog/controls")
def get_haf_controls():
    return {"controls": [c.model_dump() for c in service.control_registry.list_controls()]}

@haf_router.get("/certifications")
def get_haf_certifications():
    return service.registry.load_registry(service.registry.certification_registry_path)

@haf_router.get("/findings")
def get_haf_findings():
    # Load all findings across runs
    findings = []
    runs_dir = os.path.join(service.workspace_root, "coordination/audit_factory/runs")
    if os.path.exists(runs_dir):
        for run_id in os.listdir(runs_dir):
            f_path = os.path.join(runs_dir, run_id, "findings.json")
            if os.path.exists(f_path):
                try:
                    with open(f_path, "r") as f:
                        data = json.load(f)
                        findings.extend(data.get("findings", []))
                except Exception:
                    pass
    return {"findings": findings}

@haf_router.get("/poam")
def get_haf_poam():
    poam_file = os.path.join(service.workspace_root, "coordination/audit_factory/registries/poam_registry.json")
    if os.path.exists(poam_file):
        try:
            with open(poam_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"poam_items": []}

@haf_router.get("/runs")
def get_haf_runs():
    return service.registry.load_registry(service.registry.assessment_registry_path)

@haf_router.get("/runs/{run_id}")
def get_haf_run_detail(run_id: str):
    run_dir = os.path.join(service.workspace_root, "coordination/audit_factory/runs", run_id)
    manifest_path = os.path.join(run_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="Run not found")
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    return manifest

@haf_router.post("/assessments")
def post_haf_assessment(req: AssessmentRequest):
    try:
        summary = service.run_assessment(profile_name=req.profile, scope=req.scope)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@haf_router.post("/conmon/evaluate")
def post_conmon_evaluate(req: ConMonRequest):
    from backend.audit_factory.conmon_engine import ConMonEngine
    engine = ConMonEngine()
    signals = engine.evaluate_file_change(req.file_path)
    return {"signals": [s.model_dump() for s in signals]}

@haf_router.post("/promotion/evaluate")
def post_promotion_evaluate(req: PromotionRequest):
    cert_path = Path(service.registry.certification_registry_path)
    findings_path = Path(os.path.join(service.workspace_root, "coordination/audit_factory/registries/findings_registry.json"))
    approvals_path = Path(os.path.join(service.workspace_root, "coordination/audit_factory/registries/approvals_registry.json"))
    
    decision = evaluate_promotion(
        scope=req.scope,
        target_level=req.target_level,
        certification_registry_path=cert_path,
        findings_path=findings_path,
        approvals_path=approvals_path
    )
    return decision.model_dump()
import json
