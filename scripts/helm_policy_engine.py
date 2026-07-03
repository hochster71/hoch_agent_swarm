#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

class PolicyEngine:
    def __init__(self):
        self.contracts = {}
        self.agents = {}
        self.load_configs()

    def load_configs(self):
        contracts_file = DATA_DIR / "adapter_contracts.json"
        agents_file = DATA_DIR / "helm_agent_registry.json"
        
        if contracts_file.exists():
            with open(contracts_file, "r") as f:
                self.contracts = json.load(f)
        if agents_file.exists():
            with open(agents_file, "r") as f:
                self.agents = json.load(f)

    def check(self, agent_id, adapter_id, action, context=None):
        # 1. Look up contract and agent
        contract = self.contracts.get(adapter_id)
        agent = self.agents.get(agent_id)
        
        if not contract:
            return False, f"Unknown adapter/contract: {adapter_id}"
        if not agent:
            # Fallback default restrictions
            agent = {"capacity_tier": "light"}

        # 2. Block explicitly forbidden actions
        if action in contract.get("forbidden_actions", []):
            return False, f"Action '{action}' is explicitly forbidden under {adapter_id} contract."

        # 3. Risk Tier enforcement (agent tier must cover adapter tier)
        agent_tier = agent.get("capacity_tier", "light") # light (R0/R1), heavy (R2/R3/R4)
        adapter_risk = contract.get("risk_tier", "R0")
        
        if agent_tier == "light" and adapter_risk in ["R2", "R3", "R4"]:
            return False, f"Agent {agent_id} tier (light) is insufficient for high-risk adapter {adapter_id} ({adapter_risk})."

        # 4. Block founder-gated actions
        if action in contract.get("founder_approval_required", []):
            approved = False
            if context and context.get("founder_approved"):
                approved = True
            if not approved:
                return False, f"Action '{action}' requires explicit founder approval."

        # 5. Block dangerous action patterns (monetization/destruction/force pushes)
        if "force" in action.lower() or "delete" in action.lower() or "release" in action.lower() or "monetize" in action.lower():
            return False, f"Policy violation: Action '{action}' contains restricted lifecycle patterns."

        return True, "Policy checks passed."

def main():
    # Simple CLI check for verification gate
    print("Executing HELM Policy Engine Test Probes...")
    pe = PolicyEngine()
    
    # Test 1: Light agent trying to push code (R3)
    ok, msg = pe.check("hasf_scoring_agent", "github", "git_push")
    print(f"Test 1 (R3 Block): Allowed={ok}, Reason: {msg}")
    
    # Test 2: Forbidden push force main
    ok, msg = pe.check("hasf_builder_agent", "github", "git_push_force_main")
    print(f"Test 2 (Forbidden Block): Allowed={ok}, Reason: {msg}")
    
    # Test 3: Normal permitted action
    ok, msg = pe.check("hasf_scoring_agent", "ollama_native", "query_light_model")
    print(f"Test 3 (Permitted): Allowed={ok}, Reason: {msg}")

if __name__ == "__main__":
    main()
