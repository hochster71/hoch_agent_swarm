#!/usr/bin/env python3
import sys
import os

def verify_sync_posture():
    forbidden = ["StrictHostKey" + "Checking=no"]
    
    # We scan scripts directory for sync-related scripts
    for root, dirs, files in os.walk("scripts"):
        for file in files:
            if not file.endswith(".py") and not file.endswith(".sh"):
                continue
            if "sync" not in file.lower() and "deploy" not in file.lower() and "push" not in file.lower():
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
                for item in forbidden:
                    if item in content:
                        print(f"❌ Verification failed: Found insecure sync parameter '{item}' in {path}.")
                        sys.exit(1)
            except Exception:
                pass

    print("🟢 Secure remote sync posture verification PASSED.")
    return True

if __name__ == "__main__":
    verify_sync_posture()
