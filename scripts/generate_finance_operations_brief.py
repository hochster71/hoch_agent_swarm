#!/usr/bin/env python3
# scripts/generate_finance_operations_brief.py
# Compiles finance operations brief from ROI models, assignments, readiness results, and action queue.

import os
import json
from datetime import datetime, timezone

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "has_live_project_tracker", "data")
    
    # 1. Resolve file paths
    roi_file = os.path.join(data_dir, "epic_fury_roi_model.json")
    assignments_file = os.path.join(data_dir, "finance_agent_assignments.json")
    readiness_file = os.path.join(data_dir, "project_revenue_readiness_results.json")
    queue_file = os.path.join(data_dir, "revenue_action_queue.json")
    
    # 2. Read input databases safely
    roi_data = {}
    if os.path.exists(roi_file):
        try:
            with open(roi_file, "r") as f:
                roi_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load ROI model: {e}")
            
    assignments = []
    if os.path.exists(assignments_file):
        try:
            with open(assignments_file, "r") as f:
                assignments = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load assignments: {e}")
            
    readiness = {}
    if os.path.exists(readiness_file):
        try:
            with open(readiness_file, "r") as f:
                readiness = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load readiness: {e}")
            
    queue = []
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r") as f:
                queue = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load action queue: {e}")

    # 3. Compile monetization state and W12 blocker status
    score = "0%"
    w12_state = "PENDING"
    stripe_ready = "FAIL"
    
    if isinstance(readiness, list) and len(readiness) > 0:
        score = f"{readiness[0].get('revenue_readiness_score', 0)}%"
        w12_state = readiness[0].get("w12_blocker_status", "PENDING")
        stripe_ready = readiness[0].get("stripe_sandbox_readiness", "FAIL")
    elif isinstance(readiness, dict):
        score = readiness.get("readiness_score", "0%")
        w12_state = readiness.get("w12_blocker_status", "PENDING")
        stripe_ready = readiness.get("stripe_sandbox_readiness", "FAIL")
    
    # 4. Generate dynamic output brief JSON
    timestamp = datetime.now(timezone.utc).isoformat() + "Z"
    
    scenarios = roi_data.get("scenarios", [])
    next_actions = [
        {
            "rank": act.get("critical_path_rank"),
            "title": act.get("title"),
            "description": act.get("description"),
            "status": act.get("status")
        }
        for act in queue
    ]
    
    # Determine next required human approvals
    required_approvals = [
        "Stripe live credentials configuration deployment",
        "Promotion of release candidate tag v0.1.14-hoch-hasf-soccer-pipeline",
        "Final sign-off on Epic Fury pricing tiers base rates change",
        "Approval of HOCH HASF Soccer Platform intake audit & product model"
    ]
    
    brief_json = {
        "generated_at": timestamp,
        "monetization_state": {
            "readiness_score": score,
            "stripe_sandbox_readiness": stripe_ready
        },
        "w12_blocker_status": w12_state,
        "roi_scenarios": scenarios,
        "next_actions": next_actions,
        "required_approvals": required_approvals,
        "evidence_links": [
            "docs/business/epic-fury-roi-projection.md",
            "docs/evidence/business/project-revenue-readiness-audit.md"
        ]
    }
    
    # Write JSON output
    out_json_path = os.path.join(data_dir, "finance_operations_brief.json")
    with open(out_json_path, "w") as f:
        json.dump(brief_json, f, indent=2)
    print(f"Created brief JSON: {out_json_path}")
    
    # 5. Generate markdown brief documentation
    md_content = f"""# Finance Operations Brief — HASF Governance & ROI

*Generated At: {timestamp}*
*Operational Authority: AI Chief Financial Officer — HASF Finance Manager*

---

## 1. Current Monetization State & W12 Blocker
- **Revenue Readiness Score**: `{score}`
- **Stripe Sandbox Status**: `{stripe_ready}`
- **W12 Blocker Status**: `{w12_state}`
- **Governance Note**: Production checkout routes remain **fail-closed** until full sandbox verification checks succeed.

---

## 2. Epic Fury ROI Scenarios Summary

| Scenario | Monthly Installs | Conversion Rate | Month 6 MRR | Annualized Run Rate | ROI Estimate |
|:---|:---:|:---:|:---:|:---:|:---:|
"""
    for sc in scenarios:
        md_content += f"| **{sc['name']}** | {sc['monthly_installs']} | {sc['paid_conversion_rate']}% | ${sc['month_6_mrr']:.2f} | ${sc['annualized_run_rate']:.2f} | {sc['roi_estimate']}% |\n"

    md_content += """
---

## 3. Mandatory Human Approvals Pending (Michael Hoch)
The following tasks are pending final authorization from Michael Hoch (Founder & Owner):
"""
    for app in required_approvals:
        md_content += f"- [ ] **{app}**\n"
        
    md_content += """
---

## 4. Next Revenue Actions

| Rank | Title | Description | Status |
|:---:|:---|:---|:---:|
"""
    for act in queue[:5]:
        md_content += f"| {act.get('critical_path_rank')} | {act.get('title')} | {act.get('description')} | **{act.get('status')}** |\n"
        
    md_content += """
---

## 5. Evidence References
- [Epic Fury ROI Projection Model](file:///Users/michaelhoch/hoch_agent_swarm/docs/business/epic-fury-roi-projection.md)
- [Revenue Readiness Audit Report](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/business/project-revenue-readiness-audit.md)
"""
    
    out_md_path = os.path.join(project_root, "docs", "evidence", "business", "finance-operations-brief.md")
    os.makedirs(os.path.dirname(out_md_path), exist_ok=True)
    with open(out_md_path, "w") as f:
        f.write(md_content)
    print(f"Created brief Markdown: {out_md_path}")

if __name__ == "__main__":
    main()
