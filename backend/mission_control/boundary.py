import os
import re

ALLOWED_PODS = {"has", "hasf", "business", "cyber", "hobby", "family", "ops"}

class BoundaryViolation(Exception):
    pass

def validate_secure_boundary(target_pod: str, command: str, parameters: dict):
    # 1. Validate POD ID
    if target_pod not in ALLOWED_PODS:
        raise BoundaryViolation(f"Target POD '{target_pod}' is not registered.")

    # 2. Check for shell injection / unsafe chaining
    # Disallow character sequences often used for shell injection: ;, &&, ||, |, `, $, <, >
    unsafe_patterns = [r";", r"&&", r"\|\|", r"\|", r"`", r"\$", r"<", r">"]
    for pattern in unsafe_patterns:
        if re.search(pattern, command):
            raise BoundaryViolation(f"Command contains unauthorized chaining or redirection operator: '{pattern}'")

    # 3. Path Safety: Check that path parameters are within authorized workspaces
    path_param = parameters.get("path") or parameters.get("workspace")
    if path_param:
        abs_path = os.path.abspath(path_param)
        home = os.path.expanduser("~")
        allowed_roots = [
            os.path.join(home, "hoch_agent_swarm"),
            os.path.join(home, "hoch_agent_swarm_prompt_library"),
            os.path.join(home, ".gemini/antigravity")
        ]
        if not any(abs_path.startswith(root) for root in allowed_roots):
            raise BoundaryViolation(f"Path '{path_param}' falls outside the secure worker boundary envelope.")

    # 4. Resource Allocation Quotas
    memory_limit_gb = parameters.get("memory_limit_gb", 2.0)
    if memory_limit_gb > 8.0:
        raise BoundaryViolation(f"Requested memory limit {memory_limit_gb}GB exceeds the secure allocation quota of 8GB.")

    cpu_cores = parameters.get("cpu_cores", 2)
    if cpu_cores > 4:
        raise BoundaryViolation(f"Requested CPU cores {cpu_cores} exceeds the secure allocation quota of 4 cores.")

    return True
