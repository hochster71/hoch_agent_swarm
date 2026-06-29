import os
import sys
import json
import hashlib
import time
from playwright.sync_api import sync_playwright

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    dashboard_url = os.environ.get("DASHBOARD_URL", "http://hoch-app:8086")
    print(f"Connecting to dashboard at {dashboard_url}...")
    
    pages_to_capture = [
        {
            "id": "overview",
            "file": "overview.png",
            "navSelectors": ["#nav-overview", "[data-page='overview']", "text=Overview"]
        },
        {
            "id": "promptbrain",
            "file": "promptbrain.png",
            "navSelectors": ["#nav-promptbrain", "[data-page='promptbrain']", "text=Prompt Brain"]
        },
        {
            "id": "promptqa",
            "file": "promptqa.png",
            "navSelectors": ["#nav-promptqa", "[data-page='promptqa']", "text=Prompt QA"]
        },
        {
            "id": "evidencebrain",
            "file": "evidencebrain.png",
            "navSelectors": ["#nav-evidencebrain", "[data-page='evidencebrain']", "text=Evidence Brain"]
        },
        {
            "id": "hochtv",
            "file": "hochtv.png",
            "navSelectors": ["#nav-hochtv", "[data-page='hochtv']", "text=HOCH TV"]
        },
        {
            "id": "operator",
            "file": "operator.png",
            "navSelectors": ["#nav-operator", "[data-page='operator']", "text=Operator"]
        }
    ]
    
    output_dir = "artifacts/live_screenshots"
    os.makedirs(output_dir, exist_ok=True)
    
    manifest = {
        "mode": "live-browser-capture",
        "runtime": "docker-compose-linux",
        "tool": "playwright-chromium-linux",
        "dashboardUrl": dashboard_url,
        "capturedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages": []
    }
    
    overall_success = True
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
        except Exception as e:
            print(f"Failed to launch browser: {e}")
            sys.exit(1)
        
        try:
            page.goto(dashboard_url, timeout=30000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Failed to connect to dashboard: {e}")
            browser.close()
            sys.exit(1)
            
        for pinfo in pages_to_capture:
            pid = pinfo["id"]
            pfile = pinfo["file"]
            selectors = pinfo["navSelectors"]
            
            print(f"Capturing page '{pid}'...")
            page_status = "failed"
            sha256 = ""
            selector_used = ""
            error_msg = ""
            filepath = os.path.join(output_dir, pfile)
            
            # Click selector
            clicked = False
            for selector in selectors:
                try:
                    # Check visibility before clicking
                    page.wait_for_selector(selector, timeout=2000)
                    page.click(selector)
                    selector_used = selector
                    clicked = True
                    break
                except Exception:
                    continue
            
            if clicked:
                container_selector = f"#page-{pid}"
                try:
                    page.wait_for_selector(container_selector, timeout=3000)
                    page.wait_for_timeout(1500)  # load animations wait
                    page.screenshot(path=filepath, full_page=True)
                    sha256 = compute_sha256(filepath)
                    page_status = "captured"
                    print(f"  Successfully captured '{pid}' -> {pfile} (SHA: {sha256})")
                except Exception as e:
                    error_msg = str(e)
                    print(f"  Error capturing container for '{pid}': {error_msg}")
            else:
                error_msg = f"No selector clicked. Checked selectors: {selectors}"
                print(f"  Error: {error_msg}")
                
            if page_status == "failed":
                overall_success = False
                
            manifest["pages"].append({
                "id": pid,
                "file": pfile,
                "status": page_status,
                "sha256": sha256,
                "selectorUsed": selector_used,
                "error": error_msg
            })
            
        browser.close()
        
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote screenshot manifest to {manifest_path}")
    
    if not overall_success:
        print("One or more pages failed to capture.")
        sys.exit(1)
    else:
        print("All screenshots successfully captured!")
        sys.exit(0)

if __name__ == "__main__":
    main()
