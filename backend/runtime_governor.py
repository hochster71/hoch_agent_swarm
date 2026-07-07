import os
import sys
import json
import time
import fcntl
import psutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

class RuntimeGovernor:
    def __init__(self, base_url="http://127.0.0.1:8000", repo_root=None):
        self.base_url = base_url.rstrip('/')
        if repo_root:
            self.repo_root = Path(repo_root).resolve()
        else:
            self.repo_root = Path(__file__).resolve().parents[1]
        self.lock_file_path = self.repo_root / "backend" / "runtime_governor.lock"
        self.lock_file = None

    def acquire_lock(self):
        """Acquire a non-blocking flock on backend/runtime_governor.lock."""
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file = open(self.lock_file_path, "w")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"PID: {os.getpid()}\nStarted: {datetime.now(timezone.utc).isoformat()}\n")
            self.lock_file.flush()
            return True
        except BlockingIOError:
            self.lock_file.close()
            self.lock_file = None
            raise RuntimeError("Concurrency lock active: Another instance of RuntimeGovernor is running.")

    def release_lock(self):
        """Release the file lock."""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            except Exception:
                pass
            self.lock_file.close()
            self.lock_file = None
            # Silently attempt to remove the lockfile
            try:
                self.lock_file_path.unlink()
            except Exception:
                pass

    def check_containment(self):
        """Check if any high-risk processes are running."""
        current_pid = os.getpid()
        active_violators = []
        forbidden_patterns = [
            "hoch_daemon.sh",
            "hoch_cadence.sh",
            "brain_cadence.sh",
            "recursive_optimizer",
            "phase56_burnin.py"
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] == current_pid:
                    continue
                
                cmdline = proc.info['cmdline'] or []
                cmdline_str = " ".join(cmdline)
                name = proc.info['name'] or ""
                
                # Exclude governor execution or pytest running from triggering a false containment violation
                if "runtime_governor" in cmdline_str or "pytest" in cmdline_str:
                    continue
                
                for pattern in forbidden_patterns:
                    if pattern in cmdline_str or pattern in name:
                        active_violators.append({
                            "pid": proc.info['pid'],
                            "name": name,
                            "cmdline": cmdline
                        })
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return len(active_violators) == 0, active_violators

    def check_endpoints(self):
        """Query /health and all 4 truth endpoints."""
        endpoints = {
            "health": "/health",
            "runtime_truth": "/api/brain/runtime-truth",
            "factory_runtime_truth": "/api/brain/factory-runtime-truth",
            "source_authority": "/api/brain/source-authority",
            "reasoning_graph": "/api/brain/reasoning-graph"
        }
        
        status_map = {}
        data_map = {}
        all_ok = True
        
        for key, path in endpoints.items():
            url = f"{self.base_url}{path}"
            try:
                with urllib.request.urlopen(url, timeout=3) as res:
                    status_code = res.getcode()
                    body = res.read().decode('utf-8')
                    if status_code == 200:
                        try:
                            data = json.loads(body)
                        except Exception:
                            data = body
                        status_map[key] = {"ok": True, "status_code": status_code, "error": None}
                        data_map[key] = data
                    else:
                        status_map[key] = {"ok": False, "status_code": status_code, "error": f"Non-200 status: {status_code}"}
                        data_map[key] = None
                        all_ok = False
            except Exception as e:
                status_map[key] = {"ok": False, "status_code": None, "error": str(e)}
                data_map[key] = None
                all_ok = False
                
        return all_ok, status_map, data_map

    def check_human_approval(self):
        """Read the human approval queue to check if production mutations are approved."""
        queue_path = self.repo_root / "has_live_project_tracker" / "data" / "human_approval_queue.json"
        mutation_allowed = False
        human_approval_required = True
        
        if queue_path.exists():
            try:
                data = json.loads(queue_path.read_text(encoding="utf-8"))
                pending = data.get("pending_approvals", [])
                for app in pending:
                    if app.get("status") == "APPROVED":
                        app_id = app.get("approval_id", "")
                        app_type = app.get("type", "")
                        # Check if any ID or type has mutation keywords
                        if "PRODUCTION_MUTATION" in app_id or "PRODUCTION_MUTATION" in app_type or \
                           "MUTATION" in app_id or "MUTATION" in app_type:
                            mutation_allowed = True
                            human_approval_required = False
                            break
            except Exception:
                pass
                
        return mutation_allowed, human_approval_required

    def get_git_dirty_summary(self):
        """Get git status porcelain output."""
        try:
            r = subprocess.run(["git", "status", "--porcelain"], cwd=str(self.repo_root), capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return r.stdout.strip()
            return f"git status failed with return code {r.returncode}"
        except Exception as e:
            return f"Failed to run git status: {str(e)}"

    def evaluate(self, evidence_dir=None):
        """Execute a single advisory loop."""
        started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.acquire_lock()
        
        reasons = []
        verdict = "GO"
        
        # 1. Process containment check
        containment_ok, active_violators = self.check_containment()
        if not containment_ok:
            verdict = "NO_GO"
            reasons.append("High-risk process containment violation: active processes found running.")
            
        # 2. HTTP/API Endpoint check
        endpoints_ok, endpoint_status, data_map = self.check_endpoints()
        if not endpoints_ok:
            verdict = "NO_GO"
            for k, v in endpoint_status.items():
                if not v["ok"]:
                    reasons.append(f"Endpoint /{k} check failed: {v['error']}")
                    
        # 3. Source authority validation
        source_auth_status = "UNKNOWN"
        reasoning_graph_status = "UNKNOWN"
        
        if endpoints_ok:
            source_auth_data = data_map.get("source_authority")
            reasoning_graph_data = data_map.get("reasoning_graph")
            
            # Check source authority schema
            if not isinstance(source_auth_data, dict) or not source_auth_data or "status" not in source_auth_data or "sources" not in source_auth_data:
                verdict = "NO_GO"
                reasons.append("Source authority data is MALFORMED or empty.")
            else:
                source_auth_status = source_auth_data.get("status")
                # Fail closed if status is UNKNOWN
                if source_auth_status == "UNKNOWN":
                    verdict = "NO_GO"
                    reasons.append("Source authority status is UNKNOWN.")
                elif not source_auth_data.get("sources"):
                    verdict = "NO_GO"
                    reasons.append("Source authority sources list/dict is empty.")
                    
            # Check reasoning graph
            if isinstance(reasoning_graph_data, dict):
                reasoning_graph_status = reasoning_graph_data.get("status", "UNKNOWN")
            
            # Reassert CONDITIONAL status logic
            if verdict != "NO_GO":
                if source_auth_status == "STALE" and reasoning_graph_status == "CONDITIONAL":
                    verdict = "CONDITIONAL"
                    reasons.append("Source authority is STALE and reasoning graph is CONDITIONAL.")
                elif source_auth_status == "GO" and reasoning_graph_status == "GO":
                    verdict = "GO"
                else:
                    # Default fallback for degraded states
                    verdict = "CONDITIONAL"
                    reasons.append(f"Degraded status: source_authority={source_auth_status}, reasoning_graph={reasoning_graph_status}")
        else:
            reasons.append("Unable to evaluate source authority and reasoning graph because endpoints are unreachable.")
            
        # 4. Human approval and mutations (Advisory mode limits)
        mutation_allowed, human_approval_required = self.check_human_approval()
        
        # 5. Git status
        git_dirty_summary = self.get_git_dirty_summary()
        
        self.release_lock()
        ended_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # 6. Save decision record
        evidence_path = None
        if evidence_dir:
            ev_dir = Path(evidence_dir).resolve()
            ev_dir.mkdir(parents=True, exist_ok=True)
            record_path = ev_dir / "decision_record.json"
            evidence_path = str(record_path)
            
            record = {
                "started_at": started_at,
                "ended_at": ended_at,
                "verdict": verdict,
                "reasons": reasons,
                "endpoint_status": endpoint_status,
                "containment_status": {
                    "ok": containment_ok,
                    "active_violators": active_violators
                },
                "brain_runtime_truth": data_map.get("runtime_truth"),
                "factory_runtime_truth": data_map.get("factory_runtime_truth"),
                "source_authority_status": source_auth_status,
                "reasoning_graph_status": reasoning_graph_status,
                "mutation_allowed": mutation_allowed,
                "human_approval_required": human_approval_required,
                "hmf_hrf_paid_execution_allowed": False,
                "hoch200_sync_allowed": False,
                "git_dirty_summary": git_dirty_summary,
                "evidence_path": evidence_path
            }
            
            record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            
        return {
            "verdict": verdict,
            "reasons": reasons,
            "mutation_allowed": mutation_allowed,
            "evidence_path": evidence_path
        }
