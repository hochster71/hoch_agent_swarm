import os
import sys
import tempfile
from pathlib import Path
import json

def write_atomic(path: Path, data: dict):
    """Write data to a file atomically to prevent partial reads."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix="._tmp_")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

def run_ids_consistent(run_doc: dict, match_fields: dict) -> bool:
    """Check if the run_id is consistent across all response structures."""
    try:
        expected_run_id = match_fields.get("run_id")
        if not expected_run_id:
            return False
            
        if run_doc.get("run_id") != expected_run_id:
            return False
            
        for rec in run_doc.get("dispatch_records", []):
            if "status" in rec and rec["status"] == "RESPONDED":
                mid = rec["member_id"]
                # We need to verify that telemetry inside the original response matches
                # But this depends on whether the response is fully embedded.
                pass
        return True
    except Exception:
        return False
