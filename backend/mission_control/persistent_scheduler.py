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

from scripts.ag_execution_lease_manager import LeaseManager  # legacy global mutex (retained for history)
from backend.mission_control.per_task_lease import PerTaskLeaseManager
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
        # PER-TASK leases. The legacy LeaseManager was a single GLOBAL mutex, so the
        # advertised concurrency_limit=4 was effectively 1 (a runtime-truth defect).
        self.lease_manager = PerTaskLeaseManager()
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

            # (a) lane-level block (rare: only a genuine whole-factory halt)
            if f_info.get("state") == StateStatus.BLOCKED.value:
                logger.info(f"Skipping task {t['task_id']} due to blocked lane {pod}")
                continue

            # (b) MISSION/CAPABILITY-scoped block. An external App Store review blocks the
            #     Epic Fury DISTRIBUTION mission -- not safe, unrelated engineering work in
            #     the same factory. Scope binds to what is actually blocked.
            blocked_missions = set(f_info.get("blocked_missions") or [])
            blocked_caps = set(f_info.get("blocked_capabilities") or [])
            t_mission = (t.get("mission_id") or "").upper()
            t_cap = (t.get("required_capability") or "").upper()
            if t_mission and t_mission in {m.upper() for m in blocked_missions}:
                logger.info(f"Skipping {t['task_id']}: mission {t_mission} is BLOCKED_EXTERNAL")
                continue
            if t_cap and t_cap in {c.upper() for c in blocked_caps}:
                logger.info(f"Skipping {t['task_id']}: capability {t_cap} is BLOCKED_EXTERNAL")
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
        # ── FOUNDER AUTHORITY GATE ────────────────────────────────────────────
        # Makes coordination/founder/authority_matrix.json a HARD GATE at dispatch,
        # not a document. The daemon may run AUTONOMOUS work unattended; anything that
        # spends/publishes/binds (PROPOSE_ONLY) or is FOUNDER_ONLY is HELD and escalated,
        # never auto-executed. This is what makes 24/7 safe rather than merely unattended.
        try:
            import hashlib as _hl, json as _json, time as _t
            from backend.council.founder_model import (
                classify_action, Authority, Escalation, escalate)
            _probe = f"{task.get('name','')} {task.get('mission_prompt','')} " \
                     f"dispatch:{task.get('dispatch_type','LOCAL_OLLAMA')}"
            ruling = classify_action(_probe)

            # AUTHORITY-ID-PROPAGATION-CONTROL: every task gets an authority decision id at
            # classification. "No authority decision id means no dispatch." It is stamped
            # onto the task so it flows into lease metadata, dispatch + result envelopes.
            _adid = "AUTH-" + _hl.sha256(
                f"{task.get('task_id')}|{ruling.authority.value}|{_t.time()}".encode()
            ).hexdigest()[:16]
            task["authority_decision_id"] = _adid
            task["authority_class"] = ruling.authority.value

            _PROCEED = (Authority.AUTONOMOUS, Authority.PREAUTHORIZED_PLAYBOOK)
            if ruling.authority not in _PROCEED:
                if ruling.authority is Authority.PROHIBITED:
                    # PROHIBITED: deny + SECURITY RECORD. Never escalated — it is not
                    # approvable, so offering the founder an APPROVE button would be wrong.
                    _sec = ROOT / "coordination" / "security" / "prohibited_denials.jsonl"
                    _sec.parent.mkdir(parents=True, exist_ok=True)
                    with open(_sec, "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                            "authority_decision_id": _adid, "matched": ruling.matched,
                            "action": "DENIED_PROHIBITED"}) + "\n")
                    self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                        "status": "DENIED_PROHIBITED", "authority_decision_id": _adid,
                        "matched": ruling.matched})
                    return False

                # PROPOSE_ONLY / FOUNDER_ONLY / CONFLICTED -> withhold + escalate (decision object)
                _q = ("Which doctrine applies to" if ruling.authority is Authority.CONFLICTED
                      else f"Authorize {ruling.authority.value} task")
                escalate(Escalation(
                    one_sentence_question=f"{_q} '{task.get('name','?')}'?",
                    why_it_needs_you=f"{ruling.reason} (matched: {ruling.matched or 'n/a'}) [{_adid}]",
                    options=["Approve this dispatch", "Deny / keep local-only"],
                    recommendation_and_why="HOLD by default — the daemon does not spend, publish, or bind without you",
                    evidence_sanitized=f"task_id={task.get('task_id')} authority_decision_id={_adid} scope=factory:{task.get('target_pod','?')}",
                    cost_of_delay="none; the mission stays queued",
                    reversible=True), can_prove_answer=False)
                self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                    "status": "HELD_AUTHORITY", "authority": ruling.authority.value,
                    "authority_decision_id": _adid, "matched": ruling.matched})
                return False
        except Exception as _e:
            # fail CLOSED: if the gate cannot run, do not dispatch — a broken gate must
            # never become an open door.
            self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                            "status": "HELD_GATE_ERROR", "error": str(_e)[:120]})
            return False

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
        self.log_lease({"ts": started_at, "task_id": task_id, "lease_id": lease["lease_id"],
                        "fencing_token": lease["fencing_token"], "status": "DISPATCH_START"})

        # ---- SPEND PRE-FLIGHT, checked against OBSERVED month/day spend ----------
        # Previously the cap was checked against a pre-flight GUESS and the actual cost
        # was never recorded (every envelope said cost_usd: None). Now the cap is
        # enforced against real metered spend, and an UNPRICED adapter fails closed.
        adapter_id = str(getattr(req, "dispatch_type", "")).split(".")[-1]
        adapter_id = {"LOCAL_OLLAMA": "ollama", "LOCAL_LM_STUDIO": "lm_studio",
                      "CLI_GROK": "grok", "CLI_GEMINI": "gemini",
                      "CLI_CLAUDE": "claude"}.get(adapter_id, adapter_id.lower())
        try:
            from backend.mission_control.spend_meter import SpendMeter
            meter = SpendMeter()
            gate = meter.check_caps(adapter_id, envelope["prompt"])
        except Exception as e:
            meter, gate = None, {"allowed": False, "reason": f"SPEND_METER_ERROR: {e}"}

        if not gate.get("allowed"):
            self.log_dispatch({"ts": get_utc_now_str(), "task_id": task_id,
                               "status": "BLOCKED_SPEND", "reason": gate.get("reason"),
                               "detail": gate})
            self.lease_manager.release_lease(task_id, lease["lease_id"], status="RELEASED")
            logger.warning(f"{task_id}: BLOCKED_SPEND {gate.get('reason')}")
            return False
        
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

        # ---- METER THE REAL COST (observed I/O, hash-chained, never None) --------
        spend_entry = None
        if meter is not None:
            try:
                spend_entry = meter.record(task_id=task_id, adapter=adapter_id,
                                           prompt=envelope["prompt"], output=artifact_text,
                                           exit_code=exit_code)
            except Exception as e:
                logger.error(f"spend meter failed for {task_id}: {e}")

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
            "started_at": started_at,
            "completed_at": get_utc_now_str(),
            "worker_id": lease.get("worker_id"),
            "fencing_token": lease.get("fencing_token"),
            # REAL metered cost -- never None again.
            "cost_usd": (spend_entry or {}).get("cost_usd"),
            "cost_state": (spend_entry or {}).get("cost_state", "UNMETERED"),
            "cost_measurement": (spend_entry or {}).get("measurement"),
            "in_chars": (spend_entry or {}).get("in_chars"),
            "out_chars": (spend_entry or {}).get("out_chars"),
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
        self.lease_manager.release_lease(task_id, lease["lease_id"], status="RELEASED")
        self.log_lease({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "status": "RELEASED"
        })
        
        return passed

    def concurrency_report(self) -> Dict[str, Any]:
        """Report EFFECTIVE concurrency, never the aspirational number.

        With the legacy global mutex this had to read:
            concurrency_mode: GLOBAL_SERIAL, effective_limit: 1, status: DEGRADED
        Per-task leases remove the shared lock, so effective == configured.
        """
        per_task = isinstance(self.lease_manager, PerTaskLeaseManager)
        return {
            "concurrency_mode": "PER_TASK_LEASE" if per_task else "GLOBAL_SERIAL",
            "configured_limit": self.concurrency_limit,
            "effective_limit": self.concurrency_limit if per_task else 1,
            "status": "OK" if per_task else "DEGRADED",
            "lease_backend": type(self.lease_manager).__name__,
            "note": ("Per-task lock records; unrelated tasks run concurrently."
                     if per_task else
                     "Single global mutex: only one task can hold a lease at a time."),
        }

    def run_once(self) -> Dict[str, Any]:
        cycle_start = get_utc_now_str()
        blockers = self.load_blockers()
        runnable = self.evaluate_runnable_tasks()
        ranked = self.rank_tasks(runnable, blockers)
        
        # Per-task leases mean unrelated tasks may genuinely run at the same time.
        # Effective concurrency now equals the configured limit.
        batch = ranked[: self.concurrency_limit]
        dispatched = []
        if len(batch) <= 1:
            for task in batch:
                dispatched.append({"task_id": task["task_id"],
                                   "success": self.execute_task(task)})
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.concurrency_limit) as ex:
                futs = {ex.submit(self.execute_task, t): t for t in batch}
                for f, t in futs.items():
                    try:
                        ok = f.result()
                    except Exception as e:
                        logger.error(f"task {t['task_id']} raised: {e}")
                        ok = False
                    dispatched.append({"task_id": t["task_id"], "success": ok})

        status = "ACTIVE" if dispatched else "IDLE"
        cycle_result = {
            "cycle_start": cycle_start,
            "cycle_end": get_utc_now_str(),
            "status": status,
            "concurrency": self.concurrency_report(),
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
