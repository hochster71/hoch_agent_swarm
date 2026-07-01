def simulate_homeops_action(device_id: str, action: str) -> dict:
    risk_class = "A2"
    simulation_required = False
    approval_required = False
    
    # Classify actions
    write_keywords = ["water", "irrigate", "lock", "unlock", "delete", "send", "share", "talk", "activate"]
    is_write = any(kw in action.lower() for kw in write_keywords)
    
    if is_write:
        risk_class = "A5"
        simulation_required = True
        approval_required = True
        
    critical_keywords = ["tesla", "powershare", "camera", "vivint", "pool", "pentair", "security"]
    is_critical = any(kw in device_id.lower() or kw in action.lower() for kw in critical_keywords)
    
    if is_critical and is_write:
        risk_class = "A7"
        
    return {
        "device_id": device_id,
        "action": action,
        "risk_class": risk_class,
        "simulation_required": simulation_required,
        "approval_required": approval_required,
        "status": "SIMULATION_PASSED" if simulation_required else "AUTO_PERMITTED",
        "warnings": [f"Simulated boundary check for critical device action '{action}' on '{device_id}'."] if is_critical else []
    }
