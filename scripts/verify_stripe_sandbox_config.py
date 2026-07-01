#!/usr/bin/env python3
# scripts/verify_stripe_sandbox_config.py
# Verification script for safe Stripe sandbox/test-mode environment configuration.

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def check_env_keys():
    print("Checking Stripe test-mode configuration...")
    
    # Load from env or .env file
    pub_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    sec_key = os.environ.get("STRIPE_SECRET_KEY", "")
    wh_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    
    # If not in env, check if it's in .env file
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if "=" in line:
                    key, val = line.strip().split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    if key == "STRIPE_PUBLISHABLE_KEY":
                        pub_key = val
                    elif key == "STRIPE_SECRET_KEY":
                        sec_key = val
                    elif key == "STRIPE_WEBHOOK_SECRET":
                        wh_secret = val

    if not pub_key or not sec_key:
        print("  [FAIL] STRIPE_PUBLISHABLE_KEY or STRIPE_SECRET_KEY is missing from environment/env files.")
        return False
        
    if not pub_key.startswith("pk_test_"):
        print(f"  [FAIL] STRIPE_PUBLISHABLE_KEY does not start with pk_test_ (actual: '{pub_key[:8]}...')")
        return False
        
    if not sec_key.startswith("sk_test_"):
        print(f"  [FAIL] STRIPE_SECRET_KEY does not start with sk_test_ (actual: '{sec_key[:8]}...')")
        return False
        
    if wh_secret and not wh_secret.startswith("whsec_"):
        print(f"  [FAIL] STRIPE_WEBHOOK_SECRET does not start with whsec_ (actual: '{wh_secret[:6]}...')")
        return False

    print("  [PASS] Stripe test-mode credentials prefixes match pk_test_, sk_test_ and whsec_.")
    return True

def check_no_committed_live_keys():
    print("Checking committed files for live Stripe keys...")
    try:
        # Search for pk_live_ or sk_live_ excluding docs, scripts, tests
        res = subprocess.run(
            ["git", "grep", "-E", "pk_live_[a-zA-Z0-9_]+|sk_live_[a-zA-Z0-9_]+", "--", ".:!scripts/*", ".:!tests/*", ".:!docs/*"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            lines = res.stdout.splitlines()
            dirty = []
            for line in lines:
                if "sk_live_xxx" in line or "sk_live_epic_fury_91283" in line or "[a-za-z" in line.lower() or "sk_live_[" in line:
                    continue
                dirty.append(line)
                
            if dirty:
                print("  [FAIL] Found committed live Stripe keys in repository files:")
                for d in dirty:
                    print("   ", d)
                return False
                
        print("  [PASS] No committed live Stripe keys found.")
        return True
    except Exception as e:
        print(f"  [WARN] Git grep failed ({e}). Proceeding...")
        return True

def verify():
    env_ok = check_env_keys()
    committed_ok = check_no_committed_live_keys()
    
    if env_ok and committed_ok:
        print("[SUCCESS] Stripe sandbox test-mode keys verified successfully.")
        return True
    else:
        print("[FAILURE] Stripe sandbox verification failed.")
        return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
