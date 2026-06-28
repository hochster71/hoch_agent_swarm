import os
from pathlib import Path
from typing import Any, Dict, List, Set
from backend.exclusion_guard import GUARD

MIGRATION_DIR = Path.home() / "hoch_large_file_migration"
PATHS_FILE = MIGRATION_DIR / "large_files_paths.txt"
LOG_FILE = MIGRATION_DIR / "rclone_move.log"

class MigrationMonitor:
    def __init__(self):
        pass

    def check_migration_active(self) -> bool:
        # Check if rclone is in the process list
        try:
            # Check using standard ps command
            import subprocess
            res = subprocess.run(["ps", "-A"], capture_output=True, text=True)
            return "rclone" in res.stdout
        except Exception:
            return False

    def get_log_tail(self, num_lines: int = 15) -> List[str]:
        if not LOG_FILE.exists():
            return ["Log file not found."]
        try:
            with open(LOG_FILE, "r", errors="replace") as f:
                lines = f.readlines()
            return [line.strip() for line in lines[-num_lines:]]
        except Exception as e:
            return [f"Error reading log file: {e}"]

    def parse_rclone_log(self) -> Dict[str, str]:
        # Maps relative or absolute path fragment to status: 'COPIED', 'DELETED', 'ERROR'
        statuses = {}
        if not LOG_FILE.exists():
            return statuses
        
        try:
            with open(LOG_FILE, "r", errors="replace") as f:
                for line in f:
                    if "INFO" in line:
                        # e.g., "2026/06/28 00:30:36 INFO  : AI_MODELS/ollama/blobs/sha256-xxx: Copied (new)"
                        parts = line.split("INFO  :")
                        if len(parts) > 1:
                            subparts = parts[1].split(":")
                            if len(subparts) > 1:
                                file_path = subparts[0].strip()
                                action = subparts[1].strip()
                                if "Copied" in action:
                                    statuses[file_path] = "COPIED"
                                elif "Deleted" in action:
                                    statuses[file_path] = "DELETED"
                    elif "ERROR" in line:
                        parts = line.split("ERROR :")
                        if len(parts) > 1:
                            subparts = parts[1].split(":")
                            if len(subparts) > 1:
                                file_path = subparts[0].strip()
                                statuses[file_path] = "ERROR"
        except Exception as e:
            print(f"Error parsing rclone log: {e}")
        
        return statuses

    def get_status(self) -> Dict[str, Any]:
        migration_active = self.check_migration_active()
        
        # 1. Resolve protected files
        protected_assets = GUARD.resolve_protected_assets()
        protected_blobs = {b["filename"] for b in protected_assets.get("protected_blobs", [])}
        protected_manifests = {m.split("/")[-2] + "/" + m.split("/")[-1] for m in protected_assets.get("protected_manifests", [])}

        # 2. Parse target paths
        target_files: List[Dict[str, Any]] = []
        total_files = 0
        completed_files = 0
        pending_files = 0
        skipped_protected = 0
        failed_files = 0
        total_space_recovered = 0
        total_space_pending = 0

        # Parse log status
        log_statuses = self.parse_rclone_log()

        if PATHS_FILE.exists():
            try:
                with open(PATHS_FILE, "r") as f:
                    paths = [line.strip() for line in f if line.strip()]
                
                for path_str in paths:
                    path = Path(path_str)
                    filename = path.name
                    rel_path = path_str.replace(str(Path.home()) + "/", "")
                    
                    # Determine size if exists
                    size = -1
                    local_exists = path.exists()
                    if local_exists:
                        size = path.stat().st_size
                    
                    # Check protection
                    is_protected = False
                    # Matches ollama blobs or manifest files
                    if filename in protected_blobs:
                        is_protected = True
                    else:
                        # Matches manifest tag/family path like "gemma2/2b"
                        for pm in protected_manifests:
                            if pm in path_str:
                                is_protected = True
                                break
                    
                    # Determine status
                    status = "PENDING"
                    
                    # Match log records
                    log_key = rel_path
                    # Also try matching sub-path
                    matched_action = None
                    for k, act in log_statuses.items():
                        if k in path_str or path_str.endswith(k):
                            matched_action = act
                            break
                    
                    if is_protected:
                        status = "SKIPPED_PROTECTED"
                        skipped_protected += 1
                        if local_exists:
                            total_space_pending += size if size > 0 else 0
                    elif matched_action == "DELETED" or (not local_exists and matched_action == "COPIED"):
                        status = "COMPLETED"
                        completed_files += 1
                        # If deleted, we guess size or read from log/estimations
                        # Since we don't have it on disk, we can estimate standard sizes if needed,
                        # or if we saw it in the manifest, or standard 1GB fallback.
                        # Let's check if we can parse the size from elsewhere.
                        # For now, let's assume standard size or read from manifest if ollama blob.
                        resolved_size = size if size > 0 else 1024 * 1024 * 1024 # default 1GB estimate if already deleted
                        total_space_recovered += resolved_size
                    elif matched_action == "ERROR":
                        status = "FAILED"
                        failed_files += 1
                        if local_exists:
                            total_space_pending += size if size > 0 else 0
                    elif local_exists:
                        status = "PENDING"
                        pending_files += 1
                        total_space_pending += size if size > 0 else 0
                    else:
                        # Doesn't exist locally, not protected, and not explicitly logged as error
                        status = "COMPLETED"
                        completed_files += 1
                        total_space_recovered += 1024 * 1024 * 1024

                    total_files += 1
                    target_files.append({
                        "absolute_path": path_str,
                        "filename": filename,
                        "rel_path": rel_path,
                        "size_bytes": size,
                        "is_protected": is_protected,
                        "status": status
                    })
            except Exception as e:
                print(f"Error parsing paths file: {e}")

        # Construct recovery commands
        recovery_commands = {
            "restore_all": f"rclone copy \"gdrive:HOCH-ARCHIVE/Large-Files-2026-06-28\" \"$HOME\" --files-from {MIGRATION_DIR}/large_files_paths_relative.txt --create-empty-src-dirs --progress --transfers 4",
            "restore_ollama": f"rclone copy \"gdrive:HOCH-ARCHIVE/Large-Files-2026-06-28/AI_MODELS/ollama\" \"~/.ollama/models\" --exclude-from {GUARD.resolve_protected_assets()['exclude_file_path']} --progress",
            "verify_destination": "rclone size \"gdrive:HOCH-ARCHIVE/Large-Files-2026-06-28\""
        }

        return {
            "migration_active": migration_active,
            "total_files": total_files,
            "completed_files": completed_files,
            "pending_files": pending_files,
            "skipped_protected": skipped_protected,
            "failed_files": failed_files,
            "total_space_recovered_bytes": total_space_recovered,
            "total_space_pending_bytes": total_space_pending,
            "log_tail": self.get_log_tail(),
            "target_files": target_files[:100], # limit list size to prevent huge payload
            "recovery_commands": recovery_commands
        }

MONITOR = MigrationMonitor()
