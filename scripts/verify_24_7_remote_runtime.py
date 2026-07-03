#!/usr/bin/env python3
import subprocess
import sys

import os

def check_service(service):
    if os.path.exists("/etc/systemd/system"):
        res = subprocess.run(f"systemctl is-active {service}", shell=True, capture_output=True, text=True)
        return res.stdout.strip() == "active"
        
    # Try Tailscale IP first, fallback to public IP
    res = subprocess.run(f"ssh -o StrictHostKeyChecking=no root@100.87.18.15 'systemctl is-active {service}'", shell=True, capture_output=True, text=True)
    if res.stdout.strip() == "active":
        return True
    res = subprocess.run(f"ssh -o StrictHostKeyChecking=no root@50.116.41.183 'systemctl is-active {service}'", shell=True, capture_output=True, text=True)
    return res.stdout.strip() == "active"

def main():
    print("Executing 24/7 Remote Runtime Verification...")
    services = [
        "helm-runner",
        "has-agent-dispatcher",
        "hasf-product-factory",
        "has-runtime-watchdog"
    ]
    
    for svc in services:
        if not check_service(svc):
            print(f"❌ Verification failed: Remote service '{svc}' is not active.")
            sys.exit(1)
        print(f"🟢 Service '{svc}' is active and running on HOCH-200.")
        
    print("✅ 24/7 Remote Runtime verification PASSED.")

if __name__ == "__main__":
    main()
