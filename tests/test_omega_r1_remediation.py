"""OMEGA R1 remediation proofs — positive + negative tests for audit findings.

Covers: atomic mission_state write, CORS no-wildcard, read-auth mounted,
voice doorstep verb routing, factory readiness reconciliation, CM-3 honesty,
source_authority fail-closed for live UI, mission routes on main app.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- R-18
def test_mission_state_write_atomic(tmp_path, monkeypatch):
    from backend.mission_control import mission_state as ms

    out = tmp_path / "mission_state.json"
    monkeypatch.setattr(ms, "OUT", out)
    # Provide empty/missing sources so build still returns a structure
    state = ms.write_mission_state()
    assert out.exists()
    loaded = json.loads(out.read_text())
    assert loaded.get("schema") == "HELM_MISSION_STATE_v1"
    assert "overall" in loaded
    # No leftover temps
    temps = list(tmp_path.glob(".mission_state.*.tmp"))
    assert temps == []


# --------------------------------------------------------------------------- R-02
def test_helm_live_api_cors_not_wildcard():
    src = (ROOT / "backend" / "helm_live_api.py").read_text()
    # Must not pass wildcard as the live middleware argument (comments may mention it).
    assert not re.search(r'add_middleware\(\s*CORSMiddleware[^)]*allow_origins\s*=\s*\[\s*"\*"\s*\]', src, re.S)
    assert "allow_origins=_CORS_ORIGINS" in src or "HELM_CORS_ORIGINS" in src
    assert "ReadAuthMiddleware" in src


def test_main_api_cors_not_wildcard():
    src = (ROOT / "backend" / "main.py").read_text(encoding="utf-8", errors="ignore")
    assert not re.search(r'add_middleware\(\s*CORSMiddleware[^)]*allow_origins\s*=\s*\[\s*"\*"\s*\]', src, re.S)
    assert "_main_cors_origins" in src or "HELM_CORS_ORIGINS" in src


# --------------------------------------------------------------------------- R-01
def test_read_auth_middleware_mounted_in_helm_live_api():
    src = (ROOT / "backend" / "helm_live_api.py").read_text()
    assert "ReadAuthMiddleware" in src
    assert "HardenedConfig" in src or "from_env" in src


def test_read_auth_default_disabled_fail_closed_when_enabled():
    from backend.security.zero_trust.config import HardenedConfig
    from backend.security.zero_trust.read_auth import ReadAuthMiddleware
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def read(request):
        return JSONResponse({"ok": True})

    base = Starlette(routes=[Route("/api/v1/helm/tasks", read, methods=["GET"])])
    # Disabled: passthrough
    cfg_off = HardenedConfig(read_auth_enabled=False, read_token="secret")
    c_off = TestClient(ReadAuthMiddleware(base, cfg_off))
    assert c_off.get("/api/v1/helm/tasks").status_code == 200
    # Enabled without token: 401
    cfg_on = HardenedConfig(read_auth_enabled=True, read_token="secret")
    c_on = TestClient(ReadAuthMiddleware(base, cfg_on))
    assert c_on.get("/api/v1/helm/tasks").status_code == 401
    # Enabled with token: 200
    assert c_on.get("/api/v1/helm/tasks", headers={"X-Helm-Read-Token": "secret"}).status_code == 200


# --------------------------------------------------------------------------- GOV-03
@pytest.mark.parametrize(
    "utterance,expect_id",
    [
        ("sign the release", "sign_release"),
        ("please deploy to production", "deploy"),
        ("submit to testflight", "submit_store"),
        ("clear apple gate", "clear_apple_gate"),
        ("mark revenue earned", "mark_revenue"),
        ("provision api keys", "provision_keys"),
    ],
)
def test_voice_doorstep_utterances(utterance, expect_id):
    from backend.voice.commands import resolve_command

    cmd, _ = resolve_command(utterance=utterance)
    assert cmd is not None, f"no match for {utterance!r}"
    assert cmd["id"] == expect_id
    assert cmd["mode"] == "DOORSTEP"


# --------------------------------------------------------------------------- R-05
def test_factory_readiness_reconcile_no_fake_ready(tmp_path, monkeypatch):
    import scripts.liveness_producer as lp

    reg = {
        "factories": {
            "HSF": {"id": "HSF", "health": "ACTIVE", "readiness": "READY"},
            "HMF": {"id": "HMF", "health": "ACTIVE", "readiness": "READY"},
            "HHF": {"id": "HHF", "health": "ACTIVE", "readiness": "READY"},
        }
    }
    products = {
        "products": [
            {
                "product_id": "HSF_STORY_STUDIO",
                "factory": "HSF",
                "monetization_rung": "3_PRODUCTIZED_DEFINED_ONLY",
                "live_url": "https://story-studio-live.vercel.app",
                "source_dir": "hsf/deploy",
            },
            {
                "product_id": "HMF_CUE_LIBRARY",
                "factory": "HMF",
                "monetization_rung": "2_BUILT_NOT_SELLABLE",
                "source_dir": "products/hmf-cue-library",
            },
        ]
    }
    prod_path = tmp_path / "products.json"
    prod_path.write_text(json.dumps(products))
    monkeypatch.setattr(lp, "ROOT", tmp_path)
    # Write products where reconcile looks
    (tmp_path / "coordination" / "products").mkdir(parents=True)
    (tmp_path / "coordination" / "products" / "products.json").write_text(json.dumps(products))
    (tmp_path / "hsf" / "deploy").mkdir(parents=True)
    (tmp_path / "products" / "hmf-cue-library").mkdir(parents=True)

    notes = lp._reconcile_factory_readiness(reg)
    # HHF has no products → demoted
    assert reg["factories"]["HHF"]["readiness"] == "NOT_READY"
    assert reg["factories"]["HHF"]["health"] == "UNKNOWN"
    # HMF rung 2 + on disk → DEGRADED not READY
    assert reg["factories"]["HMF"]["readiness"] in ("DEGRADED", "NOT_READY")
    assert reg["factories"]["HMF"]["readiness"] != "READY" or reg["factories"]["HMF"]["health"] != "ACTIVE"
    # HSF rung 3 + live_url → DEGRADED or NOT_READY (not auto READY at rung 3)
    assert reg["factories"]["HSF"]["readiness"] != "READY" or "rung" in str(
        reg["factories"]["HSF"].get("readiness_basis")
    )
    # Actually for n=3 we set DEGRADED if on_disk
    assert reg["factories"]["HSF"]["readiness"] == "DEGRADED"
    assert notes  # something changed


# --------------------------------------------------------------------------- R-03 CM-3
def test_cm03_fails_on_dirty_tree():
    from backend.security.helm_control_catalog import a_cm03_change_control

    r = a_cm03_change_control()
    # Working tree is dirty during remediation — must NOT claim clean IMPLEMENT
    assert r["status"] in ("NOT_IMPLEMENTED", "UNKNOWN")
    if r["status"] == "NOT_IMPLEMENTED":
        assert "uncommitted" in r["evidence"].lower() or "dirty" in r["evidence"].lower()


# --------------------------------------------------------------------------- R-13
def test_stale_source_not_allowed_for_live_ui(tmp_path):
    from backend.brain.runtime_truth_validator import validate_source_manifest
    import time

    src = tmp_path / "naics.csv"
    src.write_text("a,b\n1,2\n")
    # Make stale
    old = time.time() - 10_000
    os.utime(src, (old, old))

    manifest = {
        "naics_2022": {
            "source_name": "NAICS",
            "local_path": str(src),
            "checksum": __import__("hashlib").sha256(src.read_bytes()).hexdigest(),
        }
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest))
    out = validate_source_manifest(mpath)
    entry = out["sources"]["naics_2022"]
    assert entry["status"] == "STALE" or entry["freshness"] == "stale"
    assert entry["allowed_for_live_ui"] is False


# --------------------------------------------------------------------------- R-06
def test_mission_api_router_on_main():
    src = (ROOT / "backend" / "main.py").read_text(encoding="utf-8", errors="ignore")
    assert "mission_api_router" in src or "mission_state_router" in src


def test_mission_api_router_returns_schema():
    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from backend.mission_control.mission_api_router import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/v1/helm/mission")
    assert r.status_code == 200
    body = r.json()
    assert body.get("truth_class") == "HELM_MISSION_STATE"
    assert body.get("schema") == "HELM_MISSION_STATE_v1" or body.get("overall")


def test_posture_schema_denies_full_catalog_claim():
    from backend.security.helm_conmon import assess

    p = assess()
    assert p.get("full_nist_800_53_coverage") is False
    assert p.get("posture_percent_scope") == "SAMPLED_CONTROLS_ONLY"
    assert "NOT" in (p.get("catalog_scope_note") or "").upper() or "not" in (
        p.get("catalog_scope_note") or ""
    )
