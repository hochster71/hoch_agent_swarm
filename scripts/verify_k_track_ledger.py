#!/usr/bin/env python3
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
LEDGER_FILE = DATA_DIR / "k_track_ledger.json"
QUEUE_FILE = DATA_DIR / "human_approval_queue.json"

def main():
    print("Executing K-Track Ledger Verification...")
    
    if not LEDGER_FILE.exists():
        print("❌ K-Track Ledger file missing!")
        sys.exit(1)
        
    with open(LEDGER_FILE, "r") as f:
        ledger = json.load(f)
        
    required_keys = ["id", "title", "status", "blocking_what", "required_founder_action", "evidence_path", "data_as_of", "expires_at", "verdict"]
    
    for item in ledger:
        missing = [k for k in required_keys if k not in item]
        if missing:
            print(f"❌ K-Track item {item.get('id')} is missing required fields: {missing}")
            sys.exit(1)
            
    # Sync to human_approval_queue.json
    queue_data = {"generated_at": "2026-07-05T00:23:12Z", "pending_approvals": []}
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE, "r") as f:
                queue_data = json.load(f)
        except Exception:
            pass
            
    # Rebuild pending_approvals: retain non-K-track items, overwrite K-track items
    pending = [a for a in queue_data.get("pending_approvals", []) if not a.get("approval_id", "").startswith("k-")]
    
    for item in ledger:
        pending.append({
            "approval_id": f"k-{item['id'].lower()}",
            "type": "FOUNDER_CREDENTIAL",
            "status": item["status"],
            "lane": "K-Track",
            "item": item["id"],
            "title": item["title"],
            "description": f"{item['required_founder_action']}. Blocks: {item['blocking_what']}.",
            "evidence_path": item["evidence_path"]
        })
        
    queue_data["pending_approvals"] = pending
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue_data, f, indent=2)
        
    # Determine verdict based on statuses
    # Since K1 is currently BLOCKED_FOUNDER_ACTION, the overall verdict is K_TRACK_BLOCKED
    verdict = "K_TRACK_BLOCKED"
    for item in ledger:
        if item["id"] == "K1" and item["status"] == "READY":
            verdict = "K_TRACK_READY"
            
    print(f"Verdict derived: {verdict}")
    print("🟢 K-Track Ledger verified and synced cleanly.")
    print(f"✅ K-Track Ledger verification PASSED with verdict: {verdict}")
    sys.exit(0)

if __name__ == "__main__":
    main()
