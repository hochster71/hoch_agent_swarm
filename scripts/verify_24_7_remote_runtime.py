#!/usr/bin/env python3
import subprocess
import sys

def check_service(service):
    res = subprocess.run(f"ssh root@50.116.41.183 'systemctl is-active {service}'", shell=True, capture_output=True, text=True)
    status = res.stdout.strip()
    return status == "active"

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
