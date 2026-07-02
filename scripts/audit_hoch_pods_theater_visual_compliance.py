#!/usr/bin/env python3
import os
import sys
import json
import re

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def audit_compliance():
    pert_server_path = os.path.join(get_project_root(), "backend", "pert_server.py")
    if not os.path.exists(pert_server_path):
        print(f"Error: {pert_server_path} not found.")
        sys.exit(1)

    with open(pert_server_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_ids = [
        "hoch-pods-theater",
        "hoch-agent-liftoff-movie-board",
        "hoch-agent-lifecycle-grid",
        "hoch-agent-profile-snapshot",
        "hoch-destination-confirmed-strip",
        "hoch-theater-system-status",
        "hoch-agent-movie-detail-drawer",
        "hoch-theater-control-bar",
        "hoch-stale-quarantine-layer",
        "hoch-pods-theater-panel",
        "hoch-pods-container"
    ]

    checks = {}
    passed = True

    # 1. Check all element IDs in HTML markup
    for element_id in required_ids:
        # Match both id="element_id" and id='element_id'
        pattern = rf'id=["\']{element_id}["\']'
        match = re.search(pattern, content)
        if match:
            checks[element_id] = "PRESENT"
        else:
            checks[element_id] = "MISSING"
            passed = False

    # 2. Check layout hierarchy (theater panel before topology panel)
    theater_idx = content.find('id="hoch-pods-theater-panel"')
    topology_idx = content.find('id="hoch-pods-topology-panel"')

    if theater_idx != -1 and topology_idx != -1:
        if theater_idx < topology_idx:
            checks["LAYOUT_ORDER"] = "PASS (Theater loads before Topology Map)"
        else:
            checks["LAYOUT_ORDER"] = "FAIL (Topology Map loads before Theater)"
            passed = False
    else:
        checks["LAYOUT_ORDER"] = "FAIL (One or both panels missing)"
        passed = False

    # 3. Check design theme compliance
    theme_rules = {
        "deep_space_bg": "background" in content and ("#030508" in content or "radial-gradient" in content),
        "neon_cyan": "var(--hoch-cyan)" in content or "#34f6ff" in content,
        "neon_green": "var(--hoch-green)" in content or "#39ff14" in content,
        "stale_frozen": "clip-stale" in content and "pod-stale-freeze" in content,
    }

    for rule, status in theme_rules.items():
        checks[f"THEME_RULE_{rule.upper()}"] = "PASS" if status else "FAIL"
        if not status:
            passed = False

    # Compile result
    result = {
        "THEME_COMPLIANCE": "PASS" if passed else "FAIL",
        "checks": checks
    }

    # Write output to audit_hoch_pods_theater_visual_compliance.json
    output_json_path = os.path.join(get_project_root(), "docs", "design", "audit_hoch_pods_theater_visual_compliance.json")
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as out_f:
        json.dump(result, out_f, indent=2)

    # Write output to audit_hoch_pods_theater_visual_compliance.md
    output_md_path = os.path.join(get_project_root(), "docs", "design", "audit_hoch_pods_theater_visual_compliance.md")
    with open(output_md_path, "w", encoding="utf-8") as out_f:
        out_f.write(f"# HOCH PODS Theater Visual Compliance Audit Report\n\n")
        out_f.write(f"**Status:** {'🟢 PASS' if passed else '🔴 FAIL'}\n\n")
        out_f.write(f"## Compliance Assertions\n\n")
        out_f.write(f"| Element/Rule | Status |\n")
        out_f.write(f"| --- | --- |\n")
        for key, val in checks.items():
            status_emoji = "🟢" if "PASS" in val or val == "PRESENT" else "🔴"
            out_f.write(f"| `{key}` | {status_emoji} {val} |\n")
        out_f.write(f"\n## Visual Theme Audit Status\n\n")
        out_f.write(f"**THEME_COMPLIANCE:** `{'PASS' if passed else 'FAIL'}`\n")

    # Print output to stdout
    print(json.dumps(result, indent=2))

    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    audit_compliance()
