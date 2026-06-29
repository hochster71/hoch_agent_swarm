import os
import json
import re
import pytest

def test_live_screenshot_manifest():
    manifest_path = "artifacts/live_screenshots/manifest.json"
    require_live = os.environ.get("REQUIRE_LIVE_SCREENSHOTS") == "1"
    
    if not os.path.exists(manifest_path):
        if require_live:
            pytest.fail("manifest.json is required but missing from artifacts/live_screenshots/")
        else:
            pytest.skip("manifest.json not present in artifacts/live_screenshots/")
            
    with open(manifest_path, "r") as f:
        data = json.load(f)
        
    assert data.get("mode") == "live-browser-capture"
    
    if "runtime" in data:
        assert data.get("runtime") == "docker-compose-linux"
        
    required_pages = ["overview", "promptbrain", "promptqa", "evidencebrain", "hochtv", "operator"]
    pages = data.get("pages", [])
    page_ids = [p.get("id") for p in pages]
    
    for page_id in required_pages:
        assert page_id in page_ids, f"Required page '{page_id}' is missing from manifest"
        
    for page in pages:
        status = page.get("status")
        pfile = page.get("file")
        sha = page.get("sha256")
        
        if status == "captured":
            # Check file exists
            filepath = os.path.join("artifacts/live_screenshots", pfile)
            assert os.path.exists(filepath), f"Screenshot file '{pfile}' is missing but status is captured"
            # Check SHA is valid 64 hex chars
            assert re.match(r"^[0-9a-fA-F]{64}$", sha), f"Invalid SHA-256: {sha}"
