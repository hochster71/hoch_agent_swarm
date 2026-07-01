import json
from pathlib import Path
from typing import List, Dict, Any

def analyze_drift(base_dir: Path) -> List[Dict[str, Any]]:
    from backend.prompt_registry import get_registry
    registry = get_registry()
    
    evidence_dir = base_dir / "artifacts" / "qa" / "prompt_registry"
    evidence_files = []
    if evidence_dir.exists():
        evidence_files = list(evidence_dir.glob("evidence_*.json"))
        
    evidence_by_prompt = {}
    for f in evidence_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            pid = data.get("prompt_id")
            if pid:
                evidence_by_prompt.setdefault(pid, []).append((data, f))
        except Exception:
            pass
            
    findings = []
    
    for p in registry.prompts:
        pid = p["id"]
        required_ev = p.get("evidence_required", [])
        
        runs = evidence_by_prompt.get(pid, [])
        runs.sort(key=lambda x: x[0].get("executed_at", ""), reverse=True)
        
        if not runs:
            continue
            
        latest_run_data, latest_file = runs[0]
        
        # 1. Evidence Drift
        missing_evidence = []
        for req_file in required_ev:
            workspace_file = base_dir / req_file
            art_file = base_dir / "artifacts" / req_file
            if not workspace_file.exists() and not art_file.exists():
                missing_evidence.append(req_file)
                
        if missing_evidence:
            findings.append({
                "prompt_id": pid,
                "type": "evidence_drift",
                "severity": "HIGH",
                "message": f"Missing required evidence files: {', '.join(missing_evidence)}",
                "timestamp": latest_run_data.get("executed_at")
            })
            
        # 2. Structure Drift
        expected_outputs = p.get("outputs", [])
        exec_res = latest_run_data.get("execution_result", {})
        res_text = str(exec_res.get("result", ""))
        missing_output_fields = []
        for out in expected_outputs:
            if isinstance(out, str) and out.lower() not in res_text.lower():
                missing_output_fields.append(out)
                
        if missing_output_fields:
            findings.append({
                "prompt_id": pid,
                "type": "structure_drift",
                "severity": "MEDIUM",
                "message": f"Latest output text lacks expected output contract strings: {', '.join(missing_output_fields)}",
                "timestamp": latest_run_data.get("executed_at")
            })
            
        # 3. Routing Drift
        if len(runs) >= 2:
            prev_run_data, _ = runs[1]
            latest_route = latest_run_data.get("task_request", {}).get("task_type")
            prev_route = prev_run_data.get("task_request", {}).get("task_type")
            if latest_route != prev_route:
                findings.append({
                    "prompt_id": pid,
                    "type": "routing_drift",
                    "severity": "HIGH",
                    "message": f"Routing target changed from '{prev_route}' to '{latest_route}'",
                    "timestamp": latest_run_data.get("executed_at")
                })
                
    return findings
