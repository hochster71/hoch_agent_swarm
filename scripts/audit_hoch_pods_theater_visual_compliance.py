#!/usr/bin/env python3
import os
import sys
import json
import re

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def audit_compliance():
    root = get_project_root()
    pert_server_path = os.path.join(root, "backend", "pert_server.py")
    ref_image_path = os.path.join(root, "docs", "design", "assets", "hoch-pods-theater-reference.jpeg")
    doctrine_path = os.path.join(root, "docs", "design", "hoch-pods-theater-doctrine.md")

    if not os.path.exists(pert_server_path):
        print(f"Error: {pert_server_path} not found.")
        sys.exit(1)

    checks = {}
    passed = True

    # 1. Assert reference image exists
    if os.path.exists(ref_image_path):
        checks["REF_IMAGE_EXISTS"] = "PASS"
    else:
        checks["REF_IMAGE_EXISTS"] = f"FAIL (Missing: {ref_image_path})"
        passed = False

    # 2. Assert doctrine exists
    if os.path.exists(doctrine_path):
        checks["DOCTRINE_EXISTS"] = "PASS"
    else:
        checks["DOCTRINE_EXISTS"] = f"FAIL (Missing: {doctrine_path})"
        passed = False

    with open(pert_server_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 3. Assert all 14 required DOM IDs are present
    required_ids = [
        "hoch-pods-theater",
        "hoch-pods-intro-movie-board",
        "hoch-pods-storyboard-grid",
        "hoch-pods-agent-spinup-variations",
        "hoch-pods-skill-card-animation-flow",
        "hoch-pods-destination-lanes",
        "hoch-pods-status-overview",
        "hoch-pods-data-flow-visualization",
        "hoch-pods-evidence-archive",
        "hoch-pods-system-confirmation",
        "hoch-pods-mission-ready",
        "hoch-pods-movie-detail-drawer",
        "hoch-pods-theater-control-bar",
        "hoch-pods-stale-quarantine-layer"
    ]

    for element_id in required_ids:
        # Check in HTML id attribute or JS document.getElementById calls
        pattern = rf'id=["\']{element_id}["\']|document\.getElementById\(["\']{element_id}["\']\)'
        match = re.search(pattern, content)
        if match:
            checks[f"ID_{element_id.upper()}"] = "PASS"
        else:
            checks[f"ID_{element_id.upper()}"] = "FAIL"
            passed = False

    # 4. Assert all 17 frame titles are present
    required_frames = [
        "SYSTEM BOOT",
        "CORE IGNITION",
        "POD RING ACTIVATION",
        "VAULT GATE OPENING",
        "AGENT ENERGY BUILD",
        "FIRST AGENT SPIN UP",
        "AGENT LAUNCH",
        "SKILL CARD POP OUT",
        "JOINING SWARM",
        "MULTI AGENT SPIN UPS",
        "ROUTING TO DESTINATIONS",
        "DESTINATION LANES ACTIVE",
        "POD STATUS OVERVIEW",
        "DATA FLOW VISUALIZATION",
        "EVIDENCE ARCHIVE",
        "SYSTEM CONFIRMATION",
        "MISSION READY"
    ]

    for frame in required_frames:
        if frame in content:
            checks[f"FRAME_{frame.replace(' ', '_')}"] = "PASS"
        else:
            checks[f"FRAME_{frame.replace(' ', '_')}"] = "FAIL"
            passed = False

    # 5. Assert bottom sections exist in markup or generated UI
    bottom_sections = [
        "Agent Spin Up Variations",
        "Skill Card Animation Flow",
        "Destination Lanes",
        "System Confirmation",
        "Mission Ready"
    ]
    for sec in bottom_sections:
        if sec.lower() in content.lower():
            checks[f"SECTION_{sec.replace(' ', '_').upper()}"] = "PASS"
        else:
            checks[f"SECTION_{sec.replace(' ', '_').upper()}"] = "FAIL"
            passed = False

    # 6. Assert layout hierarchy (theater panel loads before legacy panels)
    theater_idx = content.find('id="hoch-pods-theater-panel"')
    legacy_idx = content.find('id="hoch-pods-container"')
    if theater_idx != -1 and legacy_idx != -1:
        if theater_idx < legacy_idx:
            checks["LAYOUT_ORDER"] = "PASS"
        else:
            checks["LAYOUT_ORDER"] = "FAIL (Legacy panel loads before Theater)"
            passed = False
    else:
        checks["LAYOUT_ORDER"] = "FAIL (Missing panels)"
        passed = False

    # 7. Assert no placeholder-only text in HTML content (exclude scripts, styles, comments)
    cleaned_content = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    cleaned_content = re.sub(r'<style.*?</style>', '', cleaned_content, flags=re.DOTALL | re.IGNORECASE)
    cleaned_content = re.sub(r'<!--.*?-->', '', cleaned_content, flags=re.DOTALL)

    placeholders = ["lorem ipsum", "todo", "placeholder"]
    for ph in placeholders:
        pattern = rf'>[^<]*{ph}[^<]*<'
        if re.search(pattern, cleaned_content, re.IGNORECASE):
            checks[f"PLACEHOLDER_{ph.upper()}"] = f"FAIL (Found '{ph}')"
            passed = False
        else:
            checks[f"PLACEHOLDER_{ph.upper()}"] = "PASS"

    # 8. Assert stale/unknown states do not map to green/healthy
    # Verify that in stale logic, green class badge-pass is not assigned
    stale_logic_match = re.search(r'let badgeClass = isStale \? ["\']badge-fail["\']', content)
    if stale_logic_match:
        checks["STALE_SAFE_MAPPING"] = "PASS"
    else:
        checks["STALE_SAFE_MAPPING"] = "FAIL (Stale logic might map to green)"
        passed = False

    # 9. Assert reference image is not used as a static background
    ref_image_name = "hoch-pods-theater-reference.jpeg"
    bg_pattern = rf'background(-image)?\s*:\s*url\([^)]*{ref_image_name}[^)]*\)'
    if re.search(bg_pattern, content):
        checks["STATIC_BACKGROUND_GATE"] = "FAIL (Reference image used as CSS background)"
        passed = False
    else:
        checks["STATIC_BACKGROUND_GATE"] = "PASS"

    # Compile result
    result = {
        "THEME_COMPLIANCE": "PASS" if passed else "FAIL",
        "checks": checks
    }

    # Write output to has_live_project_tracker/data/hoch_pods_theater_visual_compliance.json
    output_json_path = os.path.join(root, "has_live_project_tracker", "data", "hoch_pods_theater_visual_compliance.json")
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as out_f:
        json.dump(result, out_f, indent=2)

    # Write output to docs/evidence/ui/hoch-pods-theater-visual-compliance-audit.md
    output_md_path = os.path.join(root, "docs", "evidence", "ui", "hoch-pods-theater-visual-compliance-audit.md")
    os.makedirs(os.path.dirname(output_md_path), exist_ok=True)
    with open(output_md_path, "w", encoding="utf-8") as out_f:
        out_f.write(f"# HOCH PODS Theater Visual Compliance Audit Report\n\n")
        out_f.write(f"**Status:** {'🟢 PASS' if passed else '🔴 FAIL'}\n\n")
        out_f.write(f"## Compliance Assertions\n\n")
        out_f.write(f"| Element/Rule | Status |\n")
        out_f.write(f"| --- | --- |\n")
        for key, val in checks.items():
            status_emoji = "🟢" if val == "PASS" else "🔴"
            out_f.write(f"| `{key}` | {status_emoji} {val} |\n")
        out_f.write(f"\n## Visual Theme Audit Status\n\n")
        out_f.write(f"**THEME_COMPLIANCE:** `{'PASS' if passed else 'FAIL'}`\n")

    # Print output to stdout
    print(json.dumps(result, indent=2))

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    audit_compliance()
