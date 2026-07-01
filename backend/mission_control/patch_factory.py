import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

def create_mission_patch(mission_id: str, file_path: str, target: str, replacement: str) -> dict:
    project_root = Path(__file__).resolve().parent.parent.parent
    patch_dir = project_root / "has_live_project_tracker" / "artifacts" / "patches"
    os.makedirs(patch_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    patch_filename = f"patch_{mission_id}_{timestamp}.json"
    patch_path = patch_dir / patch_filename

    patch_data = {
        "mission_id": mission_id,
        "file_path": file_path,
        "target_content": target,
        "replacement_content": replacement,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Generate cryptographic signature
    serialized = json.dumps(patch_data, sort_keys=True)
    signature = hashlib.sha256(serialized.encode()).hexdigest()
    patch_data["signature"] = signature

    with open(patch_path, "w", encoding="utf-8") as f:
        json.dump(patch_data, f, indent=2)

    return {
        "patch_file": str(patch_path),
        "filename": patch_filename,
        "signature": signature
    }
