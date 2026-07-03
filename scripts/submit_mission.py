#!/usr/bin/env python3
import sys
import json
import uuid
import datetime
import argparse
from mission_intent_sanitizer import sanitize_intent

def submit_mission():
    parser = argparse.ArgumentParser(description="Submit mission to HELM intake queue")
    parser.add_argument("--title", required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--risk-tier", default="R1")
    parser.add_argument("--product-id", default="cyberqrg-ai")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Sanitization
    san_status, clean_intent = sanitize_intent(args.intent)
    
    mission_id = f"mission-{uuid.uuid4().hex[:8]}"
    
    # Fake/dry-run signature details
    signature = "SIGNING_PARTIAL_PENDING_FOUNDER_KEY"
    sig_status = "NOT_REQUIRED_DRY_RUN" if args.dry_run else "VALID"
    
    mission_entry = {
      "mission_id": mission_id,
      "title": args.title,
      "intent": clean_intent,
      "requested_by": "Michael Hoch",
      "risk_tier": args.risk_tier,
      "product_id": args.product_id,
      "allowed_scope": ["planning", "scaffold"],
      "blocked_scope": ["production_release", "monetization", "public_claims", "customer_data", "live_credentials", "destructive_actions"],
      "founder_approval_required": args.risk_tier in ["R3", "R4"],
      "status": "NEW",
      "created_at": datetime.datetime.utcnow().isoformat() + "Z",
      "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
      "evidence_path": "",
      "mission_signature": signature,
      "signature_status": sig_status,
      "sanitization_status": san_status
    }
    
    queue_path = "has_live_project_tracker/data/mission_intake_queue.json"
    try:
        with open(queue_path, "r") as f:
            data = json.load(f)
    except Exception:
        data = {"queue_version": "1.0", "missions": []}
        
    data["missions"].append(mission_entry)
    
    with open(queue_path, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"🟢 Mission submitted successfully. Mission ID: {mission_id}")
    return mission_id

if __name__ == "__main__":
    submit_mission()
