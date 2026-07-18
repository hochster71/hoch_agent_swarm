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

# ── FAIL-CLOSED CAPABILITY GRANT SET ──────────────────────────────────────────
# A task that declares a `required_capability` may be dispatched autonomously
# ONLY if that capability appears here (i.e. is POSITIVELY GRANTED). This is the
# default-DENY half of the dispatch-time capability gate: it does not depend on
# any blocker being present, so a missing / parse-failed / resolved blocker
# register can no longer leak an externally-gated task.
#
# LOCAL_ONLY = self-contained local work needing no external/founder authority
# (all 8factory moonshot tasks carry it). Capabilities that require out-of-band
# authorization — APP_STORE_CONNECT_OBSERVATION, APPLE_DISTRIBUTION_PROMOTION,
# and anything Apple/Google/store/founder-gated — are deliberately ABSENT and
# are therefore denied at dispatch until explicitly granted here.
#
# Root cause this closes (sealed soak HELM-SOAK-24H-20260715T194547Z, round 644):
# the old gate only skipped a required_capability that was listed in the
# dynamically-derived `blocked_capabilities`. When `epic_fury_blocked` was
# momentarily False (blocker absent/resolved or a racy non-atomic rewrite of
# goal_blocker_register.json making load_blockers() return []), that list was
# empty and the Epic Fury APP_STORE_CONNECT_OBSERVATION task dispatched. Grant
# is now required, not merely "no active block".
DISPATCH_GRANTED_CAPABILITIES: frozenset = frozenset({"LOCAL_ONLY"})

logger = logging.getLogger("HELM.PersistentScheduler")

def get_utc_now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def _sqlite_connect(db_path, *, ro: bool = False):
    """SQLITE CONTENTION GUARD (Phase A run 2 crashed here: 'database is locked').

    Four concurrent workers + the live API + the seeder all write one sqlite file. Without WAL
    journal mode a writer blocks ALL readers, and without busy_timeout a collision raises
    immediately instead of waiting. Both are now mandatory on every connection.
    """
    import sqlite3 as _sq
    if ro:
        c = _sq.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    else:
        c = _sq.connect(str(db_path), timeout=30)
    c.execute("PRAGMA busy_timeout=30000")
    try:
        c.execute("PRAGMA journal_mode=WAL")      # readers never block writers
        c.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass
    return c


def _with_locked_retry(op, *, what: str = "db", attempts: int = 8, base: float = 0.4):
    """Run a DB unit-of-work, retrying ONLY on 'database is locked'.

    busy_timeout (above) makes ONE connection wait up to 30s for the lock. This wraps
    the whole connect->write->commit unit so that when a peer holds the WAL write lock
    LONGER than the busy_timeout (a bulk seeder, a slow transaction, a checkpoint), a
    transient lock becomes a WAIT-AND-RETRY, never a failed scheduler cycle. That is the
    difference between "HELM is operational" and the 2026-07-15 crash ('database is
    locked' killed cycle 506). Bounded: after `attempts` it re-raises, so a genuine
    deadlock is surfaced, not hidden. The op MUST open its own connection each call so a
    retry starts from a clean transaction.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            return op()
        except sqlite3.OperationalError as e:
            if "locked" not in str(e).lower():
                raise
            last = e
            waited = min(base * (2 ** i), 8.0)
            # INSTRUMENTATION: every locked-retry is the leading indicator of the exact
            # 2026-07-15 failure mode. Recording it lets HELM SEE contention rising before
            # it hits the wall. Best-effort — telemetry must never break the write path.
            try:
                from backend.mission_control import loop_metrics
                loop_metrics.get().record_lock_retry(what, waited)
            except Exception:
                pass
            time.sleep(waited)
    logger.error("%s: gave up after %d locked-retries: %s", what, attempts, last)
    raise last  # type: ignore[misc]


class PersistentScheduler:
    def __init__(self, evidence_dir: Optional[Path] = None,
                 publish_runtime_source: bool = False):
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
        # Declare THIS ledger as the canonical runtime source so the API/UI cannot silently
        # read a different one and report UNKNOWN when the truth is simply elsewhere.
        try:
            import uuid as _uuid
            from backend.truth.runtime_source import publish as _publish
            self.instance_id = f"sched-{_uuid.uuid4().hex[:8]}"
            # ONLY a real daemon may publish the canonical pointer. The API constructs a
            # PersistentScheduler on several routes; each construction was OVERWRITING the
            # daemon's pointer with the API's own evidence_dir (whose ledger does not exist),
            # producing RUNTIME_SOURCE_MISMATCH and observed_peak=UNKNOWN. The API is a READER.
            if publish_runtime_source:
                _publish(self.evidence_dir, self.instance_id)
        except Exception:
            self.instance_id = "UNKNOWN"
        self.retries: Dict[str, int] = {}
        self.max_retries = 3

    def log_cycle(self, entry: Dict[str, Any]):
        with open(self.cycles_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_lease(self, entry: Dict[str, Any]):
        # AU-9: every evidence record binds to its predecessor. Delete, edit, reorder or truncate
        # this ledger and verify_chain() breaks at that point and stays broken. Before this, a
        # record could be removed from the middle of history and NOTHING detected it.
        from backend.truth.evidence_chain import append_record
        append_record(self.lease_log, entry)

    def _release_lease_logged(
        self,
        task_id: str,
        lease_id: str,
        *,
        reason: str = "",
        status_if_ok: str = "RELEASED",
    ) -> bool:
        """Release a lease and record what ACTUALLY happened.

        Invariant: never write status=RELEASED unless lock file removal succeeded.
        If the lease is already gone (prior successful release), return True without
        inventing a second RELEASED row.
        """
        still = self.lease_manager.read_lease(task_id)
        if not still:
            return True
        if still.get("lease_id") != lease_id:
            self.log_lease({
                "ts": get_utc_now_str(),
                "task_id": task_id,
                "lease_id": lease_id,
                "status": "RELEASE_FAILED",
                "lock_file_removed": False,
                "detail": "lease_id_mismatch_or_foreign_holder",
                "reason": reason or None,
            })
            logger.error(f"{task_id}: LEASE RELEASE FAILED — lease_id mismatch")
            return False
        ok = bool(self.lease_manager.release_lease(task_id, lease_id, status=status_if_ok))
        self.log_lease({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease_id,
            "status": status_if_ok if ok else "RELEASE_FAILED",
            "lock_file_removed": ok,
            "reason": reason or None,
        })
        if not ok:
            logger.error(f"{task_id}: LEASE RELEASE FAILED — lock file may be stranded")
        return ok

    def log_dispatch(self, entry: Dict[str, Any]):
        from backend.truth.evidence_chain import append_record
        append_record(self.dispatch_log, entry)

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

        def _read() -> List[Dict[str, Any]]:
            conn = _sqlite_connect(self.db_path)
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

        return _with_locked_retry(_read, what="evaluate_runnable_tasks")

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

            # (b0) FAIL-CLOSED CAPABILITY GATE. A task that declares a
            #      required_capability dispatches ONLY if that capability is
            #      POSITIVELY GRANTED. This is default-DENY and does NOT depend
            #      on any blocker: a missing / resolved / parse-failed blocker
            #      register cannot open this gate. Closes the round-644 leak
            #      where an empty blocked_capabilities list let the Epic Fury
            #      APP_STORE_CONNECT_OBSERVATION task through.
            if t_cap and t_cap not in {c.upper() for c in DISPATCH_GRANTED_CAPABILITIES}:
                logger.info(
                    f"Skipping {t['task_id']}: capability {t_cap} not positively "
                    f"granted (fail-closed dispatch gate)")
                continue

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
            # INSTRUCTION / DATA BOUNDARY.
            # The gate classifies what HELM *does*, never the payload it carries. A task that
            # merely READS a file whose contents happen to contain the word "revoke" is not a
            # revocation -- but a naive probe over the whole prompt classified exactly that as
            # FOUNDER_ONLY and withheld safe read-only work. (Observed: all 4 native-concurrency
            # tasks held with matched='revoke', because they quote decision_record.py, which
            # defines a REVOKED status.)
            #
            # Content inside <DATA>...</DATA> is INERT: it is material the model reads, not an
            # action HELM performs. Everything OUTSIDE the block is still fully classified, so
            # an instruction cannot be smuggled past the gate by sitting next to a data block.
            # (Safe because governed adapters run with no tools and no side effects: an
            # instruction embedded in data cannot cause HELM to act.)
            import re as _re
            _action_only = _re.sub(r"<DATA>.*?</DATA>", " ", task.get("mission_prompt", "") or "",
                                   flags=_re.DOTALL | _re.IGNORECASE)
            _probe = f"{task.get('name','')} {_action_only} " \
                     f"cap:{task.get('required_capability') or ''} " \
                     f"dispatch:{task.get('dispatch_type','LOCAL_OLLAMA')}"
            ruling = classify_action(_probe)

            # Authority class now; full immutable binding (decision_digest + dispatch_digest
            # + lease_id) is minted after lease acquisition.
            task["authority_class"] = ruling.authority.value
            task["_authority_ruling_matched"] = ruling.matched
            _adid = None  # filled after mint_binding

            # PAYLOAD BOUNDARY RECORD. The <DATA> exclusion is NOT a universal security
            # boundary -- it is sound ONLY while the adapter is toolless and the payload can
            # cause no side effects. Record the assumption so it cannot be silently inherited:
            # any tool-enabled adapter MUST force reclassification under an untrusted-data
            # policy rather than reusing this ruling.
            _adapter = str(task.get("dispatch_type", "LOCAL_OLLAMA"))
            _toolless = _adapter.upper() in ("LOCAL_OLLAMA", "GROK_CLI", "")
            task["payload_boundary"] = {
                "payload_boundary": "DATA_INERT",
                "adapter": _adapter,
                "adapter_tool_access": (not _toolless),
                "side_effect_capability": "NONE" if _toolless else "UNKNOWN",
                "boundary_assumption": "VALID_FOR_TOOLLESS_ADAPTER_ONLY",
            }
            if not _toolless:
                # fail closed: the inert-data assumption does not hold for this adapter.
                self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                                "status": "HELD_UNTRUSTED_PAYLOAD_BOUNDARY",
                                "adapter": _adapter,
                                "reason": "tool-enabled adapter requires reclassification "
                                          "under an untrusted-data policy"})
                return False

            _PROCEED = (Authority.AUTONOMOUS, Authority.PREAUTHORIZED_PLAYBOOK)
            if ruling.authority not in _PROCEED:
                if ruling.authority is Authority.PROHIBITED:
                    # PROHIBITED: deny + SECURITY RECORD. Never escalated — it is not
                    # approvable, so offering the founder an APPROVE button would be wrong.
                    _sec = ROOT / "coordination" / "security" / "prohibited_denials.jsonl"
                    _sec.parent.mkdir(parents=True, exist_ok=True)
                    with open(_sec, "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                            "authority_class": ruling.authority.value, "matched": ruling.matched,
                            "action": "DENIED_PROHIBITED"}) + "\n")
                    self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                        "status": "DENIED_PROHIBITED", "authority_class": ruling.authority.value,
                        "matched": ruling.matched})
                    return False

                # PROPOSE_ONLY / FOUNDER_ONLY / CONFLICTED -> withhold + escalate (decision object)
                _q = ("Which doctrine applies to" if ruling.authority is Authority.CONFLICTED
                      else f"Authorize {ruling.authority.value} task")
                escalate(Escalation(
                    one_sentence_question=f"{_q} '{task.get('name','?')}'?",
                    why_it_needs_you=f"{ruling.reason} (matched: {ruling.matched or 'n/a'})",
                    options=["Approve this dispatch", "Deny / keep local-only"],
                    recommendation_and_why="HOLD by default — the daemon does not spend, publish, or bind without you",
                    evidence_sanitized=f"task_id={task.get('task_id')} authority={ruling.authority.value} scope=factory:{task.get('target_pod','?')}",
                    cost_of_delay="none; the mission stays queued",
                    reversible=True), can_prove_answer=False)
                self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                    "status": "HELD_AUTHORITY", "authority_class": ruling.authority.value,
                    "matched": ruling.matched})
                return False
        except Exception as _e:
            # fail CLOSED: if the gate cannot run, do not dispatch — a broken gate must
            # never become an open door.
            self.log_lease({"ts": get_utc_now_str(), "task_id": task.get("task_id"),
                            "status": "HELD_GATE_ERROR", "error": str(_e)[:120]})
            return False

        task_id = task["task_id"]
        pod = task.get("target_pod", "")

        # 1. Acquire lease (need lease_id before minting full binding)
        lease = self.lease_manager.acquire_lease(task_id, holder="persistent_scheduler")
        if not lease:
            self.log_lease({
                "ts": get_utc_now_str(),
                "task_id": task_id,
                "status": "ACQUIRE_FAILED",
                "reason": "Lease lock active"
            })
            return False

        # Mint immutable authority binding: decision → task → lease → dispatch digests
        try:
            from backend.truth.authority_binding import (
                BindingError, mint_binding, assert_active_binding,
            )
            envelope_pre = {
                "task_id": task_id,
                "pert_node": task_id,
                "scope": f"factory:{pod}",
                "prompt": task.get("mission_prompt") or f"Execute factory workflow task: {task['name']}",
                "evidence_contract": ["verdict", "checked_at"],
            }
            envelope_hash = hashlib.sha256(
                json.dumps(envelope_pre, sort_keys=True).encode()
            ).hexdigest()
            binding_obj = mint_binding(
                task=task,
                lease_id=lease["lease_id"],
                authority_class=str(task.get("authority_class") or "AUTONOMOUS"),
                scheduler_instance_id=str(getattr(self, "instance_id", "UNKNOWN")),
                envelope_hash=envelope_hash,
                decision=task.get("_test_decision"),
            )
            binding = binding_obj.to_dict()
            assert_active_binding(binding_obj)
            task["authority_binding"] = binding
            task["authority_decision_id"] = binding["authority_decision_id"]
            task["decision_digest"] = binding["decision_digest"]
            task["dispatch_digest"] = binding["dispatch_digest"]
            task["authority_status"] = binding["authority_status"]
            task["envelope_hash"] = envelope_hash
            self.lease_manager.update_lease_binding(task_id, binding)
        except Exception as _be:
            code = getattr(_be, "code", "AUTHORITY_INCOMPLETE")
            self.log_lease({
                "ts": get_utc_now_str(), "task_id": task_id,
                "lease_id": lease["lease_id"], "status": "AUTHORITY_BINDING_FAILED",
                "code": str(code), "error": str(_be)[:200],
            })
            try:
                self._release_lease_logged(
                    task_id, lease["lease_id"], reason="authority_binding_failed")
            except Exception:
                pass
            return False

        self.log_lease({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "fencing_token": lease["fencing_token"],
            "status": "ACQUIRED",
            **{k: binding[k] for k in (
                "authority_class", "authority_decision_id", "authority_status",
                "decision_digest", "dispatch_digest", "scheduler_instance_id",
            )},
        })

        # LEASE-LEAK GUARD (found by the live 2h soak).
        try:
            return self._execute_task_body(task, task_id, pod, lease, binding, envelope_hash)
        except Exception as _leak_e:
            logger.error(f"{task_id}: execute body raised: {_leak_e}")
            self.log_lease({"ts": get_utc_now_str(), "task_id": task_id,
                            "lease_id": lease["lease_id"], "status": "FAILED",
                            "error": str(_leak_e)[:160],
                            "authority_decision_id": binding.get("authority_decision_id")})
            return False
        finally:
            # Honest release: only logs RELEASED if lock file actually removed.
            # No-op (no false ledger row) if body already released successfully.
            try:
                self._release_lease_logged(
                    task_id, lease["lease_id"], reason="execute_finally")
            except Exception as _rel_e:
                logger.error(f"{task_id}: release in finally raised: {_rel_e}")

    def _execute_task_body(self, task, task_id, pod, lease, binding, envelope_hash) -> bool:
        from backend.truth.authority_binding import (
            BindingError,
            assert_active_binding,
            assert_dispatch_digest,
            assert_scheduler_instance,
            assert_lease_owns_decision,
            assert_artifact_does_not_infer_authority,
            assert_decision_digest,
            load_decision,
        )

        try:
            assert_active_binding(binding)
            assert_lease_owns_decision(binding, lease["lease_id"])
            assert_scheduler_instance(binding, str(getattr(self, "instance_id", "UNKNOWN")))
            assert_dispatch_digest(binding, envelope_hash=envelope_hash)
            dec = load_decision(binding["authority_decision_id"])
            if dec:
                assert_decision_digest(binding, dec)
        except BindingError as be:
            self.log_lease({"ts": get_utc_now_str(), "task_id": task_id,
                            "lease_id": lease["lease_id"], "status": be.code,
                            "detail": be.detail,
                            "authority_decision_id": binding.get("authority_decision_id")})
            self._release_lease_logged(
                task_id, lease["lease_id"], reason=f"binding_error:{be.code}")
            return False

        # 2. Envelope & signature (identity fields must match pre-mint envelope_hash)
        envelope = {
            "task_id": task_id,
            "pert_node": task_id,
            "scope": f"factory:{pod}",
            "prompt": task.get("mission_prompt") or f"Execute factory workflow task: {task['name']}",
            "evidence_contract": ["verdict", "checked_at"],
            "authority_decision_id": binding["authority_decision_id"],
            "decision_digest": binding["decision_digest"],
            "dispatch_digest": binding["dispatch_digest"],
            "scheduler_instance_id": binding["scheduler_instance_id"],
        }
        recomputed = hashlib.sha256(
            json.dumps({k: envelope[k] for k in (
                "task_id", "pert_node", "scope", "prompt", "evidence_contract",
            )}, sort_keys=True).encode()
        ).hexdigest()
        if recomputed != envelope_hash:
            self.log_lease({"ts": get_utc_now_str(), "task_id": task_id,
                            "status": "AUTHORITY_BINDING_MISMATCH",
                            "detail": "envelope mutated after classification"})
            self._release_lease_logged(
                task_id, lease["lease_id"], reason="envelope_mutated")
            return False

        # 3. Dispatch through CouncilDispatchGateway
        req = GatewayRequest(
            task_id=task_id,
            pert_node=task_id,
            caller_identity="helm.persistent_scheduler",
            dispatch_type=DispatchType.LOCAL_OLLAMA,
            prompt=envelope["prompt"],
            scope=envelope["scope"],
            evidence_contract=envelope["evidence_contract"],
            per_task_cap_usd=0.50,
            metadata={
                "authority_decision_id": binding["authority_decision_id"],
                "decision_digest": binding["decision_digest"],
                "dispatch_digest": binding["dispatch_digest"],
                "scheduler_instance_id": binding["scheduler_instance_id"],
            },
        )
        
        started_at = get_utc_now_str()
        self.log_lease({"ts": started_at, "task_id": task_id, "lease_id": lease["lease_id"],
                        "fencing_token": lease["fencing_token"], "status": "DISPATCH_START",
                        "authority_decision_id": binding["authority_decision_id"],
                        "dispatch_digest": binding["dispatch_digest"],
                        "lease_status": "RUNNING"})
        self.lease_manager.update_lease_binding(task_id, {"lease_status": "RUNNING"})

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
            self._release_lease_logged(
                task_id, lease["lease_id"], reason=f"blocked_spend:{gate.get('reason')}")
            logger.warning(f"{task_id}: BLOCKED_SPEND {gate.get('reason')}")
            return False
        
        # We will dynamically mock the response to avoid network delays while ensuring gateway logs are populated
        try:
            # Set the context token for gateway dispatch to satisfy ModelDispatchGuard
            from scripts.council.gateway import _GATEWAY_TOKEN
            token = secrets.token_hex(16)
            token_handle = _GATEWAY_TOKEN.set(token)
            
            # Bind the authority decision to the request so it lands in the DISPATCH RECORD.
            # It was stamped on the task at classification (before the lease); it must travel
            # all the way into the ledger or the ledger cannot prove the dispatch was allowed.
            try:
                req.authority_decision_id = task.get("authority_decision_id")
                req.authority_class = task.get("authority_class")
            except Exception:
                pass

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
            
        # Fail-closed: adapter result must preserve dispatch_digest
        result_dispatch_digest = binding["dispatch_digest"]
        if task.get("_test_alter_dispatch_digest"):
            result_dispatch_digest = "ALTERED-" + result_dispatch_digest
        if result_dispatch_digest != binding["dispatch_digest"]:
            self.log_dispatch({
                "ts": get_utc_now_str(), "task_id": task_id,
                "envelope_hash": envelope_hash, "status": "DISPATCH_BINDING_MISMATCH",
                "authority_decision_id": binding["authority_decision_id"],
                "dispatch_digest": result_dispatch_digest,
                "expected_dispatch_digest": binding["dispatch_digest"],
            })
            self._release_lease_logged(
                task_id, lease["lease_id"], reason="dispatch_binding_mismatch")
            return False

        self.log_dispatch({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "envelope_hash": envelope_hash,
            "status": status_val,
            "started_at": started_at,
            "exit_code": exit_code,
            "authority_class": binding["authority_class"],
            "authority_decision_id": binding["authority_decision_id"],
            "authority_status": binding["authority_status"],
            "decision_digest": binding["decision_digest"],
            "dispatch_digest": binding["dispatch_digest"],
            "scheduler_instance_id": binding["scheduler_instance_id"],
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

        # Authority must be on the artifact explicitly — never inferred from task_id alone.
        artifact_meta = {
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "authority_class": binding["authority_class"],
            "authority_decision_id": binding["authority_decision_id"],
            "authority_status": binding["authority_status"],
            "decision_digest": binding["decision_digest"],
            "dispatch_digest": binding["dispatch_digest"],
            "scheduler_instance_id": binding["scheduler_instance_id"],
            "artifact_sha256": artifact_sha,
        }
        if task.get("_test_omit_artifact_authority"):
            artifact_meta.pop("authority_decision_id", None)
        try:
            assert_artifact_does_not_infer_authority(
                artifact_meta=artifact_meta, binding=binding)
        except BindingError as be:
            self.log_verification({
                "ts": get_utc_now_str(), "task_id": task_id, "factory": pod,
                "verdict": "FAIL", "code": be.code, "detail": be.detail,
                "authority_decision_id": binding.get("authority_decision_id"),
            })
            self._release_lease_logged(
                task_id, lease["lease_id"], reason=f"artifact_authority:{be.code}")
            return False

        # Validator cannot COMPLETE without the same authority binding
        if task.get("_test_strip_validator_authority"):
            val = {**val, "authority_decision_id": None,
                   "decision_digest": None, "dispatch_digest": None}
        elif not val.get("authority_decision_id"):
            # Normal path: stamp binding onto validator result (explicit, not inferred)
            val = {**val, "authority_decision_id": binding["authority_decision_id"],
                   "decision_digest": binding["decision_digest"],
                   "dispatch_digest": binding["dispatch_digest"]}
        if (not val.get("authority_decision_id")
                or val.get("authority_decision_id") != binding["authority_decision_id"]
                or val.get("decision_digest") != binding["decision_digest"]
                or val.get("dispatch_digest") != binding["dispatch_digest"]):
            self.log_verification({
                "ts": get_utc_now_str(), "task_id": task_id, "factory": pod,
                "verdict": "FAIL", "code": "AUTHORITY_INCOMPLETE",
                "detail": "validator result authority chain incomplete or mismatched",
                "authority_decision_id": binding.get("authority_decision_id"),
            })
            self._release_lease_logged(
                task_id, lease["lease_id"], reason="validator_authority_incomplete")
            return False

        # Recompute pass after authority checks
        passed = bool(dispatch_ok and val.get("verdict") == "PASS")
        verdict = "PASS" if passed else "FAIL"

        # 4b. Result envelope (what came back, bound to what went out)
        self.log_result_envelope({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
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
            "authority_class": binding["authority_class"],
            "authority_decision_id": binding["authority_decision_id"],
            "authority_status": binding["authority_status"],
            "decision_digest": binding["decision_digest"],
            "dispatch_digest": binding["dispatch_digest"],
            "scheduler_instance_id": binding["scheduler_instance_id"],
            "cost_usd": (spend_entry or {}).get("cost_usd"),
            "cost_state": (spend_entry or {}).get("cost_state", "UNMETERED"),
            "cost_measurement": (spend_entry or {}).get("measurement"),
            "in_chars": (spend_entry or {}).get("in_chars"),
            "out_chars": (spend_entry or {}).get("out_chars"),
        })

        # Write terminal authority-bound artifact manifest (not inferable from task id)
        manifest_path = ROOT / "artifacts" / "factory" / f"{task_id}.manifest.json"
        manifest_path.write_text(json.dumps(artifact_meta, indent=2, sort_keys=True) + "\n")

        self.log_verification({
            "ts": get_utc_now_str(),
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "factory": pod,
            "verdict": verdict,
            "dispatch_ok": dispatch_ok,
            "validator": val.get("validator"),
            "validator_verdict": val.get("verdict"),
            "checks": val.get("checks", []),
            "failed_checks": val.get("failed_checks", []),
            "artifact_sha256": artifact_sha,
            "authority_class": binding["authority_class"],
            "authority_decision_id": binding["authority_decision_id"],
            "authority_status": binding["authority_status"],
            "decision_digest": binding["decision_digest"],
            "dispatch_digest": binding["dispatch_digest"],
            "scheduler_instance_id": binding["scheduler_instance_id"],
            "details": f"exit={exit_code} status={status_val} validator={val.get('verdict')}"
        })
        
        # Decide the new status ONCE (this mutates self.retries — must not run per retry).
        if passed:
            new_status = "COMPLETED"
        else:
            retry_count = self.retries.get(task_id, 0) + 1
            self.retries[task_id] = retry_count
            new_status = "FAILED" if retry_count >= self.max_retries else "PENDING"

        # Persist it with locked-retry: a peer holding the write lock must never turn a
        # completed task's result into a lost write / a dead cycle.
        def _persist() -> None:
            conn = _sqlite_connect(self.db_path)
            try:
                conn.execute("""
                    UPDATE mission_control_tasks
                    SET status = ?, updated_at = ?, evidence_path = ?
                    WHERE task_id = ?
                """, (new_status, get_utc_now_str(), f"artifacts/evidence/{task_id}_proof.json", task_id))
                conn.commit()
            finally:
                conn.close()

        _with_locked_retry(_persist, what=f"persist_status:{task_id}")
            
        # 5. Release lease -- AND RECORD WHAT ACTUALLY HAPPENED.
        # Never write RELEASED unless the lock file was actually removed.
        self._release_lease_logged(
            task_id, lease["lease_id"], reason="terminal_path")
        
        return passed

    def concurrency_report(self) -> Dict[str, Any]:
        """Report EFFECTIVE concurrency, never the aspirational number.

        With the legacy global mutex this had to read:
            concurrency_mode: GLOBAL_SERIAL, effective_limit: 1, status: DEGRADED
        Per-task leases remove the shared lock, so effective == configured.
        """
        per_task = isinstance(self.lease_manager, PerTaskLeaseManager)
        # RUNTIME TRUTH: structural capacity (a class name) is NOT evidence that two tasks
        # ever actually ran at once. `effective_limit` used to be inferred from an isinstance
        # check -- that is an assertion, not a measurement. Effective concurrency is OBSERVED
        # from the lease ledger (overlapping ACTIVE lease intervals) or it is UNKNOWN.
        observed = self.observed_peak_concurrency()
        return {
            "concurrency_mode": "PER_TASK_LEASE" if per_task else "GLOBAL_SERIAL",
            "configured_limit": self.concurrency_limit,
            "structural_capacity": self.concurrency_limit if per_task else 1,
            "observed_peak_concurrency": observed,          # int, or "UNKNOWN"
            "effective_limit": observed if isinstance(observed, int) else "UNKNOWN",
            "status": ("OK" if isinstance(observed, int) and observed >= 2
                       else "UNPROVEN" if per_task else "DEGRADED"),
            "lease_backend": type(self.lease_manager).__name__,
            "note": ("Per-task lock records. effective_limit is OBSERVED from overlapping "
                     "leases; UNKNOWN until a real overlap is recorded."
                     if per_task else
                     "Single global mutex: only one task can hold a lease at a time."),
        }

    def observed_peak_concurrency(self):
        """Max simultaneously-held leases OBSERVED from AUTHORITATIVE LEASE INTERVALS.

        A first cut summed +1 on {ACQUIRED, DISPATCH_START} and -1 on {RELEASED, ...}. That
        DOUBLE-COUNTED every task (one lease emits BOTH ACQUIRED and DISPATCH_START), so a
        single task netted +1 and the peak inflated ~2x -- it could report 4 when only 2
        tasks ever overlapped. A concurrency number that is wrong in the flattering direction
        is exactly the fake-green this system exists to prevent.

        Correct method: pair events by lease_id into [acquired, released] intervals and sweep.
        An unreleased lease (crashed worker) stays open to the end of the window -- honest,
        since it IS still held.
        """
        if not self.lease_log.exists():
            return "UNKNOWN"
        opened: Dict[str, str] = {}     # lease_id -> acquired ts
        closed: Dict[str, str] = {}     # lease_id -> released ts
        last_ts = ""
        for line in self.lease_log.read_text().splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            lid, st, ts = e.get("lease_id"), e.get("status"), e.get("ts")
            if not lid or not ts:
                continue                 # HELD_/DENIED_ rows carry no lease: never counted
            last_ts = max(last_ts, ts)
            if st == "ACQUIRED":
                opened.setdefault(lid, ts)
            elif st in ("RELEASED", "COMPLETED", "FAILED"):
                closed.setdefault(lid, ts)
        if not opened:
            return "UNKNOWN"

        events = []
        for lid, a in opened.items():
            r = closed.get(lid, last_ts)     # still-held lease: open to end of window
            events.append((a, +1))
            events.append((r, -1))
        # -1 before +1 at an identical timestamp: a release at time T does not overlap an
        # acquire at time T. Never round in the flattering direction.
        events.sort(key=lambda x: (x[0], x[1]))
        cur = peak = 0
        for _, d in events:
            cur += d
            peak = max(peak, cur)
        return peak if peak > 0 else "UNKNOWN"

    def run_once(self) -> Dict[str, Any]:
        # RECLAIM EXPIRED LEASES FIRST. Phase A 2026-07-14 FAILED because this did not exist:
        # is_expired() was defined and never called, so a killed worker pinned its slot forever.
        # The TTL is now enforced, not decorative.
        try:
            _reclaimed = self.lease_manager.reclaim_expired_leases()
            for _r in _reclaimed:
                self.log_lease({
                    "ts": get_utc_now_str(),
                    "task_id": _r.get("task_id"),
                    "lease_id": _r.get("lease_id"),
                    "status": "LEASE_RECLAIMED_EXPIRED",
                    "lock_file_removed": True,
                    "held_seconds": _r.get("held_seconds"),
                    "reason": _r.get("reclaim_reason") or _r.get("status"),
                })
                logger.warning(
                    f"{_r.get('task_id')}: LEASE RECLAIMED (expired, held "
                    f"{_r.get('held_seconds')}s) — slot freed")
        except Exception as _re:
            logger.error(f"lease reclamation failed: {_re}")

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
