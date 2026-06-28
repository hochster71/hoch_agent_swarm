import subprocess
from pathlib import Path
from typing import Any, Dict
from backend.exclusion_guard import GUARD
from backend.migration_monitor import MONITOR

MIGRATION_DIR = Path.home() / "hoch_large_file_migration"
PATHS_RELATIVE = MIGRATION_DIR / "large_files_paths_relative.txt"
LOG_FILE = MIGRATION_DIR / "rclone_move.log"

class MigrationRunner:
    def __init__(self):
        pass

    def resume_migration(self) -> Dict[str, Any]:
        # 1. Check if already active
        if MONITOR.check_migration_active():
            return {
                "status": "ALREADY_RUNNING",
                "command": "",
                "message": "Migration is already active in the background."
            }

        # 2. Re-generate exclusions to ensure latest rules are mapped
        GUARD.generate_exclude_file()
        exclude_path = GUARD.resolve_protected_assets()["exclude_file_path"]

        # 3. Construct command line args
        cmd = [
            "rclone", "move",
            str(Path.home()),
            "gdrive:HOCH-ARCHIVE/Large-Files-2026-06-28",
            "--files-from", str(PATHS_RELATIVE),
            "--exclude-from", str(exclude_path),
            "--create-empty-src-dirs",
            "--transfers", "4",
            "--checkers", "8",
            "--log-file", str(LOG_FILE),
            "--log-level", "INFO"
        ]

        # 4. Spawning subprocess in background
        try:
            # Ensure parents exist
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True
            )
            
            return {
                "status": "STARTED",
                "pid": process.pid,
                "command": " ".join(cmd),
                "message": f"Guarded rclone migration successfully started in background (PID: {process.pid})."
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "command": " ".join(cmd),
                "message": f"Failed to execute rclone process: {e}"
            }

RUNNER = MigrationRunner()
