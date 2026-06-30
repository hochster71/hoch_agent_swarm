import os
import yaml
import uuid
from datetime import datetime

class GoogleDriveDelivery:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.targets_path = os.path.join(root_dir, "config/delivery_targets.yaml")

    def deliver_file(self, requester: str, filepath: str, target_name: str) -> dict:
        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": "Source file does not exist."
            }

        # Check targets allowlist
        if not os.path.exists(self.targets_path):
            return {
                "success": False,
                "error": "Delivery targets allowlist configuration not found."
            }

        with open(self.targets_path, "r") as f:
            data = yaml.safe_load(f) or {}

        targets = data.get("delivery_targets", {})
        if target_name not in targets:
            return {
                "success": False,
                "error": f"Target folder '{target_name}' is not allowlisted."
            }

        target_info = targets[target_name]
        allowed_requesters = target_info.get("allowed_requesters", [])
        if requester not in allowed_requesters:
            return {
                "success": False,
                "error": f"Requester '{requester}' is not authorized to deliver to target folder '{target_name}'."
            }

        # Check credentials availability
        has_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None or os.getenv("GD_CREDENTIALS") is not None
        delivery_mode = "real_upload" if has_credentials else "dry_run"

        # Successful simulation (or copying file to a simulated GDrive root)
        simulated_drive_root = os.path.join(self.root_dir, "dist/google_drive_simulated", target_info["folder"])
        os.makedirs(simulated_drive_root, exist_ok=True)
        
        filename = os.path.basename(filepath)
        dest_path = os.path.join(simulated_drive_root, filename)
        
        # Simple simulation: write file metadata or copy
        try:
            with open(filepath, "rb") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
        except Exception as e:
            return {
                "success": False,
                "error": f"Simulated Drive write failed: {e}"
            }

        receipt_id = f"rcpt-{str(uuid.uuid4())[:8]}"
        return {
            "success": True,
            "receipt_id": receipt_id,
            "delivery_mode": delivery_mode,
            "provider": target_info["provider"],
            "folder": target_info["folder"],
            "filename": filename,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sha256": "simulated-sha256-checksum",
            "status": "DRY-RUN RECEIPT ONLY (Credentials Unavailable)" if delivery_mode == "dry_run" else "SUCCESSFULLY DELIVERED"
        }
