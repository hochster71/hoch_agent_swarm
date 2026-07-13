"""HELM Platform Operations Supervisor.

Supervises FastAPI backend, Vite dev server, and persistent scheduler daemon,
writing heartbeat logs and managing process lifetimes.
"""
from __future__ import annotations
import os
import sys
import time
import json
import datetime
import signal
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HEARTBEAT_FILE = PROJECT_ROOT / "has_live_project_tracker" / "data" / "helm_supervisor_heartbeat.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("HELM.Supervisor")

class HelmSupervisor:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = True
        
        # Setup signals
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        logger.info(f"Received signal {signum}. Initiating graceful shutdown of all processes...")
        self.running = False
        self.terminate_all()

    def terminate_all(self):
        for name, proc in list(self.processes.items()):
            if proc.poll() is None:
                logger.info(f"Terminating process {name} (PID: {proc.pid})")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {name} did not terminate. Killing...")
                    proc.kill()
                except Exception as e:
                    logger.error(f"Error terminating {name}: {e}")
        self.processes.clear()

    def write_heartbeat(self):
        status = {}
        for name, proc in self.processes.items():
            exit_code = proc.poll()
            status[name] = {
                "pid": proc.pid,
                "status": "RUNNING" if exit_code is None else "STOPPED",
                "exit_code": exit_code
            }
            
        heartbeat_data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "supervisor_pid": os.getpid(),
            "processes": status,
            "status": "HEALTHY" if all(p["status"] == "RUNNING" for p in status.values()) else "DEGRADED"
        }
        
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            HEARTBEAT_FILE.write_text(json.dumps(heartbeat_data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write heartbeat file: {e}")

    def run(self):
        logger.info("Initializing HELM Platform Processes...")
        
        # 1. Start backend (uvicorn main:app --port 8000)
        logger.info("Starting Backend...")
        self.processes["backend"] = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 2. Start persistent scheduler
        logger.info("Starting Persistent Scheduler...")
        self.processes["scheduler"] = subprocess.Popen(
            [sys.executable, "-c", "from backend.mission_control.persistent_scheduler import PersistentScheduler; PersistentScheduler().run_loop()"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        import datetime
        
        logger.info("All processes spawned. Supervisor loop active.")
        while self.running:
            self.write_heartbeat()
            
            # Restart stopped processes
            for name, proc in list(self.processes.items()):
                if proc.poll() is not None:
                    logger.error(f"Process {name} has stopped (Exit code: {proc.poll()}). Restarting...")
                    if name == "backend":
                        self.processes["backend"] = subprocess.Popen(
                            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
                            cwd=str(PROJECT_ROOT),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    elif name == "scheduler":
                        self.processes["scheduler"] = subprocess.Popen(
                            [sys.executable, "-c", "from backend.mission_control.persistent_scheduler import PersistentScheduler; PersistentScheduler().run_loop()"],
                            cwd=str(PROJECT_ROOT),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
            
            time.sleep(5)

if __name__ == "__main__":
    HelmSupervisor().run()
