#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def verify_routing():
    print("Executing Tier 3 Routing Policy Verification...")
    
    routing_file = DATA_DIR / "model_routing_policy.json"
    registry_file = DATA_DIR / "helm_adapter_registry.json"
    
    if not routing_file.exists() or not registry_file.exists():
        print("❌ Verification failed: Configuration files missing.")
        sys.exit(1)
        
    with open(routing_file, "r") as f:
        routing = json.load(f)
    with open(registry_file, "r") as f:
        registry = json.load(f)
        
    # Get status of adapters
    gpu_online = registry.get("ollama_gpu_pod", {}).get("status") == "ONLINE"
    lmstudio_online = registry.get("lmstudio", {}).get("status") == "ONLINE"
    native_online = registry.get("ollama_native", {}).get("status") == "ONLINE"
    
    # Check heavy routes
    for route in routing.get("routing", []):
        if route.get("tier") == "heavy":
            # 1. Verification of routing target
            target = route.get("default_model_class")
            
            # If GPU is online, it must route to GPU
            if gpu_online and target != "ollama_gpu_pod":
                print("❌ Verification failed: GPU pod is online but Tier 3 tasks are not routed to it.")
                sys.exit(1)
                
            # If GPU is offline but lmstudio is online
            if not gpu_online and lmstudio_online and target == "ollama_gpu_pod":
                # Ensure lmstudio is in fallback list
                if "lmstudio" not in route.get("fallback_order", []):
                    print("❌ Verification failed: GPU pod is offline but lmstudio fallback is not configured.")
                    sys.exit(1)
                    
            # If only native is online
            if not gpu_online and not lmstudio_online and native_online:
                if route.get("fallback_block_to_light_model", True) and not route.get("advisory_mode", False):
                    # Enforce block
                    print("🟢 Verified: Tier 3 tasks block because only 1.5B local model is available.")
                else:
                    print("❌ Verification failed: Heavy model downgraded to 1.5B without advisory_mode=true.")
                    sys.exit(1)
                    
    print("🟢 Tier 3 Routing Policy verification PASSED.")
    return True

if __name__ == "__main__":
    verify_routing()
