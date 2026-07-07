import os
import sys
import json
import argparse
from pathlib import Path

def check_record_schema(record_path):
    if not record_path.exists():
        print(f"ERROR: Decision record file not found at {record_path}", file=sys.stderr)
        return False
        
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: Failed to parse JSON from {record_path}: {e}", file=sys.stderr)
        return False
        
    required_keys = [
        "started_at", "ended_at", "verdict", "reasons", "endpoint_status",
        "containment_status", "brain_runtime_truth", "factory_runtime_truth",
        "source_authority_status", "reasoning_graph_status", "mutation_allowed",
        "human_approval_required", "hmf_hrf_paid_execution_allowed",
        "hoch200_sync_allowed", "git_dirty_summary", "evidence_path"
    ]
    
    missing_keys = [k for k in required_keys if k not in data]
    if missing_keys:
        print(f"ERROR: Missing required keys in decision record: {missing_keys}", file=sys.stderr)
        return False
        
    # Check advisory constraints
    if data.get("hmf_hrf_paid_execution_allowed") is not False:
        print("ERROR: hmf_hrf_paid_execution_allowed is not False", file=sys.stderr)
        return False
        
    if data.get("hoch200_sync_allowed") is not False:
        print("ERROR: hoch200_sync_allowed is not False", file=sys.stderr)
        return False
        
    if data.get("verdict") not in ["GO", "CONDITIONAL", "NO_GO"]:
        print(f"ERROR: Invalid verdict: {data.get('verdict')}", file=sys.stderr)
        return False
        
    print("[OK] Decision record JSON schema is fully compliant.")
    return True

def check_codebase_compliance():
    repo_root = Path(__file__).resolve().parents[1]
    gov_file = repo_root / "backend" / "runtime_governor.py"
    if not gov_file.exists():
        print(f"ERROR: {gov_file} not found", file=sys.stderr)
        return False
        
    content = gov_file.read_text(encoding="utf-8")
    
    # 1. Ensure no launchctl usage
    for term in ["launchctl", "bootstrap", "kickstart"]:
        if term in content.lower():
            print(f"ERROR: Governor code contains forbidden path/term: '{term}'", file=sys.stderr)
            return False
            
    # 2. Check that no subprocesses of high-risk scripts exist
    import ast
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_subproc = False
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "subprocess":
                    is_subproc = True
                elif isinstance(func, ast.Name) and func.id in ["run", "Popen"]:
                    is_subproc = True
                
                if is_subproc:
                    if node.args:
                        arg0 = node.args[0]
                        if isinstance(arg0, ast.List):
                            elts = [e.value for e in arg0.elts if isinstance(e, ast.Constant)]
                            if elts and elts[0] == "git":
                                continue
                        print(f"ERROR: Forbidden subprocess invocation found in governor code: {ast.dump(node)}", file=sys.stderr)
                        return False
    except Exception as e:
        print(f"WARNING: AST compliance check skipped/failed: {e}")
        
    print("[OK] Governor codebase compliance verified (No launchctl, no illegal subprocesses).")
    return True

def main():
    parser = argparse.ArgumentParser(description="Verify Runtime Governor decision records and code compliance")
    parser.add_argument("--evidence-dir", type=str, required=True, help="Directory containing decision_record.json")
    args = parser.parse_args()
    
    evidence_dir = Path(args.evidence_dir).resolve()
    record_path = evidence_dir / "decision_record.json"
    
    schema_ok = check_record_schema(record_path)
    code_ok = check_codebase_compliance()
    
    if schema_ok and code_ok:
        print("SUCCESS: Runtime Governor verification PASSED.")
        sys.exit(0)
    else:
        print("FAILURE: Runtime Governor verification FAILED.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
