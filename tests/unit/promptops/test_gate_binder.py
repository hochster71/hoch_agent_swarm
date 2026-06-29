from backend.promptops.gate_binder import GateBinder

def test_gate_binder():
    binder = GateBinder()
    
    docker_gates = binder.get_bound_gates("DOCKER_RUNTIME")
    assert "docker_truth_check.sh" in docker_gates
    assert "docker_gate.sh" in docker_gates
    
    general_gates = binder.get_bound_gates("GENERAL_E2E_BUILD")
    assert "final_verifier_gate.sh" in general_gates
