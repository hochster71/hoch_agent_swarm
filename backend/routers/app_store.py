"""App Store route handlers extracted from backend/main.py (main-split-plan step).

Serves the `/api/app-store/*` and mirrored `/api/v1/app-store/*` read endpoints
that expose the private App Store candidate queue, first-app release checklist,
exposure scans and TestFlight readiness artifacts.

Paths are preserved EXACTLY as they were registered in main.py — both the
un-versioned and the /api/v1 mirror — so existing consumers keep working.
"""
import os

from fastapi import APIRouter

router = APIRouter()

# main.py resolved data/docs paths relative to backend/ (os.path.dirname(__file__)).
# This module lives one level deeper (backend/routers/), so anchor on backend/.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@router.get("/api/app-store/candidates")
@router.get("/api/v1/app-store/candidates")
def get_app_store_candidates():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/private_app_candidate_queue.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-candidate")
@router.get("/api/v1/app-store/first-candidate")
def get_app_store_first_candidate():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_candidate_decision.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/exposure-review")
@router.get("/api/v1/app-store/exposure-review")
def get_app_store_exposure_review():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_exposure_review.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/release-checklist")
@router.get("/api/v1/app-store/release-checklist")
def get_app_store_release_checklist():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_release_checklist.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/listing")
@router.get("/api/v1/app-store/listing")
def get_app_store_listing():
    import json
    path = os.path.join(_BACKEND_DIR, "../docs/app_store/first_app/APP_STORE_LISTING_DRAFT.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {"listing_draft": f.read()}
        except Exception:
            pass
    return {}

@router.get("/api/app-store/monetization")
@router.get("/api/v1/app-store/monetization")
def get_app_store_monetization():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_monetization_model.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/build-plan")
@router.get("/api/v1/app-store/build-plan")
def get_app_store_build_plan():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_build_plan.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/readiness")
@router.get("/api/v1/app-store/readiness")
def get_app_store_readiness():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_readiness_gate.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/metadata")
@router.get("/api/v1/app-store/first-app/metadata")
def get_app_store_first_app_metadata():
    import json
    path = os.path.join(_BACKEND_DIR, "../apps/rmf_evidence_review_companion/metadata/app_metadata.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/exposure-scan")
@router.get("/api/v1/app-store/first-app/exposure-scan")
def get_app_store_first_app_exposure_scan():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_rc1_exposure_scan.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/build-gate")
@router.get("/api/v1/app-store/first-app/build-gate")
def get_app_store_first_app_build_gate():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_rc1_build_gate.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/checklist")
@router.get("/api/v1/app-store/first-app/checklist")
def get_app_store_first_app_checklist():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_release_checklist.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.post("/api/app-store/first-app/run-exposure-scan")
@router.post("/api/v1/app-store/first-app/run-exposure-scan")
def post_app_store_first_app_run_exposure_scan():
    try:
        from scripts.app_store.scan_first_app_exposure import run_exposure_scan
        res = run_exposure_scan()
        return {"status": "success", "result": res}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/api/app-store/first-app/compile-status")
@router.get("/api/v1/app-store/first-app/compile-status")
def get_app_store_first_app_compile_status():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_compile_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/ui-polish")
@router.get("/api/v1/app-store/first-app/ui-polish")
def get_app_store_first_app_ui_polish():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_ui_polish_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/offline-data")
@router.get("/api/v1/app-store/first-app/offline-data")
def get_app_store_first_app_offline_data():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_offline_data_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/local-storage")
@router.get("/api/v1/app-store/first-app/local-storage")
def get_app_store_first_app_local_storage():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_local_storage_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/assets")
@router.get("/api/v1/app-store/first-app/assets")
def get_app_store_first_app_assets():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_asset_readiness.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/store-connect")
@router.get("/api/v1/app-store/first-app/store-connect")
def get_app_store_first_app_store_connect():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_store_connect_readiness.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/testflight-readiness")
@router.get("/api/v1/app-store/first-app/testflight-readiness")
def get_app_store_first_app_testflight_readiness():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_testflight_readiness_gate.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/toolchain")
@router.get("/api/v1/app-store/first-app/toolchain")
def get_app_store_first_app_toolchain():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_toolchain_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/compile-results")
@router.get("/api/v1/app-store/first-app/compile-results")
def get_app_store_first_app_compile_results():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_compile_results.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/device-test")
@router.get("/api/v1/app-store/first-app/device-test")
def get_app_store_first_app_device_test():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_device_test_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/screenshots")
@router.get("/api/v1/app-store/first-app/screenshots")
def get_app_store_first_app_screenshots():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_screenshot_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/icon")
@router.get("/api/v1/app-store/first-app/icon")
def get_app_store_first_app_icon():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_icon_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/privacy-declaration")
@router.get("/api/v1/app-store/first-app/privacy-declaration")
def get_app_store_first_app_privacy_declaration():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_privacy_declaration_status.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/testflight-upload-gate")
@router.get("/api/v1/app-store/first-app/testflight-upload-gate")
def get_app_store_first_app_testflight_upload_gate():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/first_app_testflight_upload_gate.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.get("/api/app-store/first-app/michael-approval")
@router.get("/api/v1/app-store/first-app/michael-approval")
def get_app_store_first_app_michael_approval():
    import json
    path = os.path.join(_BACKEND_DIR, "../data/app_store/michael_testflight_approval.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
