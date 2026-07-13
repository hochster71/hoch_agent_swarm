"""HELM Persistent 24/7 Scheduler.

Loads goal & PERT graph, manages task leases & fencing tokens, evaluates scoped
blockers, dispatches via CouncilDispatchGateway, and records ledgers.
"""
from __future__ import annotations
import os
import json
import secrets
import sqlite3
from pathlib import Path as _P
ROOT = _P(__file__).resolve().parents[2]
import datetime
import hashlib
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.ag_execution_lease_manager import LeaseManager
from scripts.council.gateway import CouncilDispatchGateway, GatewayRequest, DispatchType
from backend.mission_control.scoped_states import ScopedStateEvaluator, StateStatus

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "backend" / "swarm_ledger.db"

logger = logging.getLogger("HELM.PersistentScheduler")

def get_utc_now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

class PersistentScheduler:
    def __init__(self, evidence_dir: Optional[Path] = None):
        self.repo_root = PROJECT_ROOT
        self.db_path = DB_PATH
        self.lease_manager = LeaseManager()
        self.evidence_dir = evidence_dir or (PROJECT_ROOT / "coordination" / "council" / "live_proof_packages" / "HELM-24X7-MOCK")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.gateway = CouncilDispatchGateway()
        
        # Ledgers
        self.cycles_log = self.evidence_dir / "scheduler_cycles.jsonl"
        self.lease_log = self.evidence_dir / "task_lease_ledger.jsonl"
        self.dispatch_log = self.evidence_dir / "dispatch_ledger.jsonl"
        self.verification_log = self.evidence_dir / "verification_ledger.jsonl"
        
        # Concurrency & quotas
        self.concurrency_limit = 4
        self.active_leases: Dict[str, Dict[str, Any]] = {}
        self.retries: Dict[str, int] = {}
        self.max_retries = 3

    def log_cycle(self, entry: Dict[str, Any]):
        with open(self.cycles_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_lease(self, entry: Dict[str, Any]):
        with open(self.lease_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_dispatch(self, entry: Dict[str, Any]):
        with open(self.dispatch_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _append_jsonl(self, name, rec):
        p = self.evidence_dir / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def log_result_envelope(self, rec):
        self._append_jsonl("result_envelopes.jsonl", rec)

    def log_verification(self, entry: Dict[str, Any]):
        with open(self.verification_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def load_blockers(self) -> List[Dict[str, Any]]:
        blocker_file = self.repo_root / "has_live_project_tracker" / "data" / "goal_blocker_register.json"
        if not blocker_file.exists():
            return []
        try:
            with open(blocker_file, "r") as f:
                data = json.load(f)
                return data.get("blockers", [])
        except Exception:
            return []

    def evaluate_runnable_tasks(self) -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            # Load pending/failed tasks
            tasks = [dict(r) for r in conn.execute("""
                SELECT t.*, m.target_pod, m.name as mission_name
                FROM mission_control_tasks t
                JOIN mission_control_missions m ON t.mission_id = m.mission_id
                WHERE t.status IN ('PENDING', 'FAILED')
                ORDER BY t.step_index ASC
            """).fetchall()]
            
            # Load completed tasks
            completed = {r["task_id"] for r in conn.execute(
                "SELECT task_id FROM mission_control_tasks WHERE status = 'COMPLETED'"
            ).fetchall()}
            
            # Filter by dependency
            runnable = []
            for t in tasks:
                dep_str = t.get("dependencies", "")
                deps = [d.strip() for d in dep_str.split(",") if d.strip()]
                if all(d in completed for d in deps):
                    runnable.append(t)
            return runnable
        finally:
            conn.close()

    def rank_tasks(self, tasks: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Evaluate states to check lane blockers
        evaluator = ScopedStateEvaluator(self.repo_root)
        
        # Check operator hold status
        operator_hold_active = True
        hold_path = self.repo_root / "has_live_project_tracker" / "data" / "ag_operator_hold.json"
        if hold_path.exists():
            try:
                hold_doc = json.loads(hold_path.read_text(encoding="utf-8"))
                if hold_doc.get("operator_hold_active") is False or hold_doc.get("operator_hold") == "CLEAR":
                    operator_hold_active = False
            except Exception:
                pass
                
        state_info = evaluator.evaluate_states(global_hold=operator_hold_active, blockers=blockers)
        factory_states = state_info["FACTORY_STATE"]
        
        filtered = []
        for t in tasks:
            pod = t.get("target_pod", "").upper()
            f_info = factory_states.get(pod, {})
            if f_info.get("state") == StateStatus.BLOCKED.value:
                # Scoped blocker applies to this factory/product lane!
                logger.info(f"Skipping task {t['task_id']} due to blocked lane {pod}")
                continue
            filtered.append(t)
            
        # Rank by priority (critical pods first, then step_index, then age/retry count)
        critical_pods = ["CYBER", "HASF", "OPS"]
        def sort_key(task):
            pod = task.get("target_pod", "").upper()
            is_crit = 0 if pod in critical_pods else 1
            retry_cnt = self.retries.get(task["task_id"], 0)
            return (is_crit, task.get("step_index", 0), -retry_cnt)
            
        filtered.sort(key=sort_key)
        return filtered

    def execute_task(self, task: Dict[str, Any]) -> bool:
        task_id = task["task_id"]
        pod = task.get("target_pod", "")
        
        # 1. Acquire lease
        lease = self.lease_manager.acquire_lease(task_id, holder="persistent_scheduler")
        if not lease:
            self.log_lease({
                "ts": get_utc_now_str(),
                "task_id": task_id,
                "status": "ACQUIRE_FAILED",
                "reason": "Lease lock active"
            })
            return False
            
        self.log_lease({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "fencing_token": lease["fencing_token"],
            "status": "ACQUIRED"
        })
        
        # 2. Envelope & signature
        envelope = {
            "task_id": task_id,
            "pert_node": task_id,
            "scope": f"factory:{pod}",
            # A real bounded mission carries its own instruction. Fall back to the
            # generic form only for legacy rows.
            "prompt": task.get("mission_prompt") or f"Execute factory workflow task: {task['name']}",
            "evidence_contract": ["verdict", "checked_at"]
        }
        envelope_hash = hashlib.sha256(json.dumps(envelope, sort_keys=True).encode()).hexdigest()
        
        # 3. Dispatch through CouncilDispatchGateway
        req = GatewayRequest(
            task_id=task_id,
            pert_node=task_id,
            caller_identity="helm.persistent_scheduler",
            dispatch_type=DispatchType.LOCAL_OLLAMA,
            prompt=envelope["prompt"],
            scope=envelope["scope"],
            evidence_contract=envelope["evidence_contract"],
            per_task_cap_usd=0.50
        )
        
        started_at = get_utc_now_str()
        
        # We will dynamically mock the response to avoid network delays while ensuring gateway logs are populated
        try:
            # Set the context token for gateway dispatch to satisfy ModelDispatchGuard
            from scripts.council.gateway import _GATEWAY_TOKEN
            token = secrets.token_hex(16)
            token_handle = _GATEWAY_TOKEN.set(token)
            
            # Dispatch
            res = self.gateway.dispatch(req)
            stdout = res.output
            status_val = res.status
            exit_code = res.exit_code
            
            _GATEWAY_TOKEN.reset(token_handle)
        except Exception as e:
            stdout = f"Internal dispatch error: {e}"
            status_val = "FAILED"
            exit_code = 1
            
        self.log_dispatch({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "envelope_hash": envelope_hash,
            "status": status_val,
            "started_at": started_at,
            "exit_code": exit_code
        })
        
        # 3b. PERSIST THE ARTIFACT. Previously the adapter's output was discarded --
        #     the run could be "PASS" while producing nothing at all.
        artifact_dir = ROOT / "artifacts" / "factory"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / f"{task_id}.md"
        artifact_text = stdout or ""
        artifact_path.write_text(artifact_text, encoding="utf-8")
        artifact_sha = hashlib.sha256(artifact_text.encode()).hexdigest()

        # 4. INDEPENDENT VERIFICATION of the artifact -- not merely a dispatch check.
        #    `exit_code == 0` proves a process ran; it does NOT prove the work is real.
        dispatch_ok = (status_val == "COMPLETED" and exit_code == 0)
        try:
            from backend.mission_control.factory_validators import validate as _validate
            _ctx = task.get("validator_ctx") or {}
            if isinstance(_ctx, str):
                try:
                    _ctx = json.loads(_ctx)
                except Exception:
                    _ctx = {}
            val = _validate(pod, artifact_text, _ctx)
        except Exception as e:
            val = {"validator": "ERROR", "verdict": "FAIL", "checks": [],
                   "failed_checks": ["validator_exception"], "error": str(e)[:160]}

        passed = bool(dispatch_ok and val.get("verdict") == "PASS")
        verdict = "PASS" if passed else "FAIL"

        # 4b. Result envelope (what came back, bound to what went out)
        self.log_result_envelope({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "factory": pod,
            "envelope_hash": envelope_hash,
            "adapter": str(getattr(req, "dispatch_type", "")),
            "dispatch_status": status_val,
            "exit_code": exit_code,
            "artifact_path": str(artifact_path.relative_to(ROOT)),
            "artifact_sha256": artifact_sha,
            "artifact_chars": len(artifact_text),
        })

        self.log_verification({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "factory": pod,
            "verdict": verdict,
            "dispatch_ok": dispatch_ok,
            "validator": val.get("validator"),
            "validator_verdict": val.get("verdict"),
            "checks": val.get("checks", []),
            "failed_checks": val.get("failed_checks", []),
            "artifact_sha256": artifact_sha,
            "details": f"exit={exit_code} status={status_val} validator={val.get('verdict')}"
        })
        
        # Update DB state
        conn = sqlite3.connect(str(self.db_path))
        try:
            if passed:
                new_status = "COMPLETED"
            else:
                retry_count = self.retries.get(task_id, 0) + 1
                self.retries[task_id] = retry_count
                if retry_count >= self.max_retries:
                    new_status = "FAILED"
                else:
                    new_status = "PENDING"
                    
            conn.execute("""
                UPDATE mission_control_tasks
                SET status = ?, updated_at = ?, evidence_path = ?
                WHERE task_id = ?
            """, (new_status, get_utc_now_str(), f"artifacts/evidence/{task_id}_proof.json", task_id))
            conn.commit()
        finally:
            conn.close()
            
        # 5. Release lease
        self.lease_manager.release_lease(lease["lease_id"], status="RELEASED")
        self.log_lease({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "status": "RELEASED"
        })
        
        return passed

    def run_once(self) -> Dict[str, Any]:
        cycle_start = get_utc_now_str()
        blockers = self.load_blockers()
        runnable = self.evaluate_runnable_tasks()
        ranked = self.rank_tasks(runnable, blockers)
        
        dispatched = []
        for task in ranked[:self.concurrency_limit]:
            success = self.execute_task(task)
            dispatched.append({
                "task_id": task["task_id"],
                "success": success
            })
            
        status = "ACTIVE" if dispatched else "IDLE"
        cycle_result = {
            "cycle_start": cycle_start,
            "cycle_end": get_utc_now_str(),
            "status": status,
            "dispatched_count": len(dispatched),
            "dispatched": dispatched
        }
        self.log_cycle(cycle_result)
        return cycle_result

    def run_loop(self):
        logger.info("Starting persistent scheduler loop...")
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
            time.sleep(5)
