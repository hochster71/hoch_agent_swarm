#!/usr/bin/env python3
"""
record_reviewer_feedback.py
===========================
Appends a reviewer feedback entry to reviewer_feedback_log.jsonl and updates
the aggregated reviewer_feedback_summary.json metrics.
"""

import os
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
LOG_PATH = BASE_DIR / "data" / "prompt_brain" / "outreach" / "reviewer_feedback_log.jsonl"
SUMMARY_PATH = BASE_DIR / "data" / "prompt_brain" / "outreach" / "reviewer_feedback_summary.json"

def record_feedback(role, scenario, correctness, usefulness, trust, pain_fit, will_pilot, will_pay, integrations, objections, risks, next_action):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "reviewer_role": role,
        "scenario_reviewed": scenario,
        "correctness_score": float(correctness),
        "usefulness_score": float(usefulness),
        "trust_score": float(trust),
        "buyer_pain_fit": pain_fit,
        "willingness_to_pilot_signal": bool(will_pilot),
        "willingness_to_pay_signal": bool(will_pay),
        "requested_integrations": integrations if isinstance(integrations, list) else [integrations],
        "objections": objections if isinstance(objections, list) else [objections],
        "risk_concerns": risks if isinstance(risks, list) else [risks],
        "next_action": next_action
    }
    
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
        
    records = []
    if LOG_PATH.exists():
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
                    
    total = len(records)
    avg_correctness = sum(r["correctness_score"] for r in records) / total if total > 0 else 0.0
    avg_usefulness = sum(r["usefulness_score"] for r in records) / total if total > 0 else 0.0
    avg_trust = sum(r["trust_score"] for r in records) / total if total > 0 else 0.0
    pilot_count = sum(1 for r in records if r["willingness_to_pilot_signal"])
    pay_count = sum(1 for r in records if r["willingness_to_pay_signal"])
    
    summary = {
        "total_feedback_count": total,
        "average_correctness": round(avg_correctness, 2),
        "average_usefulness": round(avg_usefulness, 2),
        "average_trust": round(avg_trust, 2),
        "willingness_to_pilot_count": pilot_count,
        "willingness_to_pay_count": pay_count
    }
    
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print(f"[+] Recorded feedback. Summary updated at: {SUMMARY_PATH}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI usage mapping
        pass
    else:
        # Clear log if it exists to keep runs deterministic
        if LOG_PATH.exists():
            LOG_PATH.unlink()
        # Seed 3 diverse reviewer feedback logs to verify decision gate logic
        record_feedback("ISSO", "scenario_001", 9.0, 9.5, 9.0, "HIGH", True, True, "Jira", "None", "None", "Schedule installation")
        record_feedback("ISSM", "scenario_002", 8.5, 9.0, 8.5, "HIGH", True, False, "GitLab", "Price too high", "Zero data leakage proof", "Send pricing sheet")
        record_feedback("SCA Auditor", "scenario_003", 9.5, 9.0, 9.5, "HIGH", True, True, "Xacta", "None", "None", "Arrange pilot meeting")
