#!/usr/bin/env python3
import json
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_FILE = ROOT / "has_live_project_tracker/data/evidence_manifest.json"
SIG_FILE = ROOT / "has_live_project_tracker/data/evidence_manifest_head.sig"

def verify_signature():
    print("Executing Evidence Signature Verification Gate...")
    
    if not SIG_FILE.exists():
        print("❌ Verification failed: Signature file is missing.")
        sys.exit(1)
        
    if not MANIFEST_FILE.exists():
        print("❌ Verification failed: Manifest file is missing.")
        sys.exit(1)
        
    with open(SIG_FILE, "r") as f:
        try:
            sig_data = json.load(f)
        except Exception as e:
            print(f"❌ Verification failed: Signature file malformed: {e}")
            sys.exit(1)
            
    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)
        
    if not manifest:
        print("❌ Verification failed: Manifest is empty.")
        sys.exit(1)
        
    head_entry = manifest[-1]
    head_hash = head_entry["entry_hash"]
    
    # Verify values
    sig_head_hash = sig_data.get("head_entry_hash")
    sig_head_id = sig_data.get("head_entry_id")
    signature = sig_data.get("signature")
    
    if sig_head_hash != head_hash:
        print(f"❌ Verification failed: Signature head hash mismatch. Signed: {sig_head_hash}, Actual Head: {head_hash}")
        sys.exit(1)
        
    if sig_head_id != head_entry["entry_id"]:
        print(f"❌ Verification failed: Signature head ID mismatch. Signed: {sig_head_id}, Actual Head: {head_entry['entry_id']}")
        sys.exit(1)
        
    # Recalculate signature
    mock_priv_key = "founder-private-key-material-2026-remediation"
    sig_payload = f"{head_hash}:{mock_priv_key}"
    expected_sig = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()
    
    if signature != expected_sig:
        print("❌ Verification failed: Cryptographic signature is invalid.")
        sys.exit(1)
        
    print("🟢 Cryptographic manifest signature is valid.")
    return True

if __name__ == "__main__":
    verify_signature()
