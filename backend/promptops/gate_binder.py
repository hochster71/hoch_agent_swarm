class GateBinder:
    def get_bound_gates(self, prompt_class: str) -> list:
        # Default gates that run on all tasks
        gates = ["final_verifier_gate.sh", "anti_fake_gate.sh", "scan_hardcoded_status.sh"]
        
        if prompt_class == "DOCKER_RUNTIME":
            gates.extend(["docker_truth_check.sh", "docker_gate.sh", "scan_host_paths.sh"])
        elif prompt_class == "KUBERNETES_LANE":
            gates.extend(["docker_truth_check.sh", "scan_host_paths.sh"])
        elif prompt_class == "SHOPPING_RESEARCH_GATE":
            gates.extend(["zero_defect_gate.sh"])
        elif prompt_class == "SECURITY_HARDENING" or prompt_class == "ZERO_DEFECT_CLOSEOUT":
            gates.extend(["zero_defect_gate.sh"])
            
        return list(set(gates))
