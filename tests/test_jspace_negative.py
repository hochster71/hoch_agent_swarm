"""HJOS NEGATIVE battery — proof that the observer fails CLOSED.

An observer that cannot prove it fails closed is not an observer.

These tests assert the CONTRACT, not the colour. Nothing here demands green:
every test states what HJOS must REFUSE to do, or what it must PRESERVE when it
refuses. Mutation stays gated behind a founder-approved authorizing_policy_id;
no test here sets one on the real governance document, and every test runs in
tmp_path — the real coordination/ tree is never touched.

Sections:
  DAEMON          — supervision cannot duplicate, hang, overlap, or lose history
  CONTAINMENT     — containment cannot act unauthorized, self-verify, or lie
  LEASE HYGIENE   — hygiene cannot clobber, cannot infer orphan-hood from absence,
                    and must be exactly reversible
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import pytest

from backend.jspace.daemon import (
    DaemonLockError,
    HJOSDaemon,
    SingleInstanceLock,
)
from backend.jspace.ledger import JSpaceLedger
from backend.jspace.quarantine import (
    attest_containment_verification,
    execute_quarantine_if_allowed,
    quarantine_expired_orphan_locks,
    rollback_containment,
    validate_governance,
)

GOV_SCHEMA = "HJOS_QUARANTINE_GOVERNANCE_v1"


# --------------------------------------------------------------------------- helpers
def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write_gov(root: Path, **kw) -> Path:
    d = {
        "schema": GOV_SCHEMA,
        "automatic_quarantine_enabled": False,
        "orphan_lease_hygiene": "manual_approval",
        "authorizing_policy_id": None,
    }
    d.update(kw)
    p = root / "coordination" / "jspace" / "quarantine_governance.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    return p


def _authorized_gov(root: Path) -> Path:
    """A governance doc that WOULD authorize mutation — only ever inside tmp_path."""
    return _write_gov(
        root,
        authorizing_policy_id="FOUNDER-POLICY-TEST-0001",
        automatic_quarantine_enabled=True,
        orphan_lease_hygiene="auto",
    )


def _lease_dir(root: Path) -> Path:
    d = root / "coordination" / "leases"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_lock(root: Path, task_id: str, *, expires: str, status="ACTIVE", instance=None) -> Path:
    p = _lease_dir(root) / f"{task_id}.lock"
    p.write_text(json.dumps({
        "task_id": task_id,
        "lease_id": f"lease-{task_id}",
        "status": status,
        "expires_at": expires,
        "scheduler_instance_id": instance,
        "acquired_at": "2026-07-14T00:00:00+00:00",
    }, indent=2) + "\n", encoding="utf-8")
    return p


def _tree(root: Path):
    """Snapshot of every path + content digest under root (mutation detector)."""
    out = {}
    for p in sorted(root.rglob("*")):
        out[str(p.relative_to(root))] = _sha256(p) if p.is_file() else "<dir>"
    return out


PAST = "2000-01-01T00:00:00+00:00"
FUTURE = "2099-01-01T00:00:00+00:00"


# =========================================================================== DAEMON
def test_duplicate_daemon_is_prevented(tmp_path):
    """A second daemon instance must not run while a LIVE pid holds the lock."""
    lock_path = tmp_path / "hjos_daemon.lock"
    first = SingleInstanceLock(lock_path, instance_id="hjos-A")
    first.acquire()

    # os.getpid() is genuinely alive — no injection, real liveness check.
    held = json.loads(lock_path.read_text())
    assert held["pid"] == os.getpid()

    second = SingleInstanceLock(lock_path, instance_id="hjos-B")
    with pytest.raises(DaemonLockError) as exc:
        second.acquire()
    assert "DAEMON_ALREADY_RUNNING" in str(exc.value)

    # the incumbent lock is intact — the loser did not steal it
    assert json.loads(lock_path.read_text())["instance_id"] == "hjos-A"


def test_stale_pid_is_recovered_not_trusted(tmp_path):
    """A dead pid must be RECOVERED with provenance, never silently trusted and
    never treated as a live incumbent (which would wedge the daemon forever)."""
    lock_path = tmp_path / "hjos_daemon.lock"
    dead_pid = 2 ** 31 - 1  # cannot be a live process
    lock_path.write_text(json.dumps({
        "schema": "HJOS_DAEMON_LOCK_v1",
        "pid": dead_pid,
        "instance_id": "hjos-DEAD",
        "acquired_at": "2026-07-14T00:00:00Z",
    }), encoding="utf-8")

    lock = SingleInstanceLock(lock_path, instance_id="hjos-NEW")
    rec = lock.acquire()

    assert rec["pid"] == os.getpid()
    assert rec["instance_id"] == "hjos-NEW"
    # recovery is RECORDED, not silent
    assert rec["recovered_stale"]["stale_pid"] == dead_pid
    assert rec["recovered_stale"]["stale_instance_id"] == "hjos-DEAD"
    assert rec["recovered_stale"]["reason"] == "PID_NOT_ALIVE"


def test_unreadable_lock_is_recovered_with_reason(tmp_path):
    """A corrupt lock file must not be trusted as a live incumbent."""
    lock_path = tmp_path / "hjos_daemon.lock"
    lock_path.write_text("{ this is not json", encoding="utf-8")
    lock = SingleInstanceLock(lock_path, instance_id="hjos-NEW")
    rec = lock.acquire()
    assert rec["recovered_stale"]["reason"] == "LOCK_UNREADABLE"


def test_overlapping_cycle_is_prevented(tmp_path):
    """Two concurrent run_cycle calls must not both execute the cycle body."""
    ledger_root = tmp_path / "jspace"
    ledger_root.mkdir(parents=True)
    _write_gov(tmp_path)

    entered = threading.Event()
    release = threading.Event()
    calls = []

    def slow_cycle(**kw):
        calls.append(1)
        entered.set()
        release.wait(timeout=5)
        return {"overall": "CONFIRMED_LIVE"}

    d = HJOSDaemon(
        repo_root=tmp_path, ledger_root=ledger_root,
        cycle_fn=slow_cycle, cycle_timeout_s=5.0, instance_id="hjos-1",
    )
    out = {}
    t = threading.Thread(target=lambda: out.update({"first": d.run_cycle()}))
    t.start()
    assert entered.wait(timeout=5), "cycle body never started"

    second = d.run_cycle()  # must return immediately, not queue or re-enter
    assert second["cycle_ran"] is False
    assert second["status"] == "SKIPPED_OVERLAP"
    assert second["reason"] == "CYCLE_IN_PROGRESS"

    release.set()
    t.join(timeout=5)
    assert out["first"]["status"] == "OK"
    assert calls == [1], "cycle body must execute exactly once"


def test_cycle_timeout_is_handled_not_hung(tmp_path):
    """A wedged cycle must time out, be counted as a failure, and must not block
    the supervisor — and a still-running zombie must not be overlapped."""
    ledger_root = tmp_path / "jspace"
    ledger_root.mkdir(parents=True)
    _write_gov(tmp_path)

    release = threading.Event()

    def hung_cycle(**kw):
        release.wait(timeout=30)
        return {"overall": "CONFIRMED_LIVE"}

    d = HJOSDaemon(
        repo_root=tmp_path, ledger_root=ledger_root,
        cycle_fn=hung_cycle, cycle_timeout_s=0.25, instance_id="hjos-1",
    )
    t0 = time.time()
    r = d.run_cycle()
    elapsed = time.time() - t0

    assert r["status"] == "TIMEOUT"
    assert r["cycle_ran"] is False
    assert elapsed < 5.0, "supervisor hung waiting on the cycle"
    assert d.status()["consecutive_failures"] == 1

    # the abandoned cycle is still in flight: the next cycle must NOT overlap it
    nxt = d.run_cycle()
    assert nxt["status"] == "SKIPPED_OVERLAP"
    assert nxt["reason"] == "PREVIOUS_CYCLE_STILL_RUNNING"

    release.set()


def test_consecutive_failure_count_is_exposed(tmp_path):
    """Failures are counted, exposed, and reset only by a real success."""
    ledger_root = tmp_path / "jspace"
    ledger_root.mkdir(parents=True)
    _write_gov(tmp_path)

    boom = {"fail": True}

    def flaky(**kw):
        if boom["fail"]:
            raise RuntimeError("observer blew up")
        return {"overall": "CONFIRMED_LIVE"}

    d = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                   cycle_fn=flaky, instance_id="hjos-1")
    d.run_cycle()
    d.run_cycle()
    st = d.status()
    assert st["consecutive_failures"] == 2
    assert st["last_status"] == "ERROR"
    assert "observer blew up" in st["last_error"]
    # degraded is surfaced, not swallowed
    assert st["degraded"] is True

    boom["fail"] = False
    r = d.run_cycle()
    assert r["status"] == "OK"
    assert d.status()["consecutive_failures"] == 0
    assert d.status()["degraded"] is False

    # the count survives a restart (new object, same ledger root)
    d2 = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                    cycle_fn=flaky, instance_id="hjos-2")
    assert d2.status()["cycles_run"] == 3


def test_process_restart_does_not_rewrite_the_ledger(tmp_path):
    """Restart must APPEND. Pre-existing ledger bytes must survive byte-identical."""
    ledger_root = tmp_path / "jspace"
    ledger_root.mkdir(parents=True)
    _write_gov(tmp_path)

    events = ledger_root / "events.jsonl"
    pre = json.dumps({"event_id": "JEVT-PRIOR", "event_type": "HJOS_CYCLE_END"}) + "\n"
    events.write_text(pre, encoding="utf-8")
    pre_bytes = events.read_bytes()

    def cycle(**kw):
        with events.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event_id": "JEVT-NEW", "event_type": "HJOS_CYCLE_END"}) + "\n")
        return {"overall": "CONFIRMED_LIVE"}

    d1 = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                    cycle_fn=cycle, instance_id="hjos-1")
    d1.run_cycle()
    d1.stop()

    # --- process restart ---
    d2 = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                    cycle_fn=cycle, instance_id="hjos-2")
    d2.start()
    d2.run_cycle()

    after = events.read_bytes()
    assert after.startswith(pre_bytes), "restart rewrote/truncated prior ledger history"
    assert after.count(b"JEVT-PRIOR") == 1
    assert after.count(b"JEVT-NEW") == 2

    # the daemon's own log is append-only too, and carries both instances
    log = (ledger_root / "daemon.jsonl").read_text().splitlines()
    instances = {json.loads(l)["instance_id"] for l in log if l.strip()}
    assert {"hjos-1", "hjos-2"} <= instances
    assert d2.status()["cycles_run"] == 2  # counter continued, was not reset


def test_invalid_policy_fails_closed(tmp_path):
    """A governance doc that LOOKS authorizing but is invalid must NOT authorize
    mutation. An unknown schema version is not a licence to move files."""
    ledger_root = tmp_path / "jspace"
    ledger_root.mkdir(parents=True)
    _write_gov(
        tmp_path,
        schema="HJOS_QUARANTINE_GOVERNANCE_v99_FROM_THE_FUTURE",
        authorizing_policy_id="LOOKS-LEGIT-0001",
        automatic_quarantine_enabled=True,
        orphan_lease_hygiene="auto",
    )
    lock = _write_lock(tmp_path, "SOAK-OLD", expires=PAST, instance=None)
    before = _tree(_lease_dir(tmp_path))

    d = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                   cycle_fn=lambda **kw: {"overall": "CONFIRMED_LIVE"}, instance_id="hjos-1")
    pf = d.preflight()
    assert pf["ok"] is False
    assert pf["fail_closed"] is True
    assert pf["mutation_authorized"] is False
    assert any("SCHEMA" in r for r in pf["reasons"])

    r = d.run_cycle()
    assert r["cycle_ran"] is False
    assert r["status"] == "FAIL_CLOSED"

    # and the containment path itself refuses, regardless of the daemon
    logs = []
    q = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="s",
        evidence=[str(lock)], cycle_id="C", observer="o",
        ledger_append=logs.append, repo_root=tmp_path,
    )
    assert q["executed"] is False
    assert q["blocked"] == "GOVERNANCE_DENY_INVALID_POLICY_DOC"
    assert _tree(_lease_dir(tmp_path)) == before, "invalid policy still mutated state"


def test_non_string_policy_id_fails_closed(tmp_path):
    """authorizing_policy_id must be a real approved id, not a truthy value."""
    _write_gov(tmp_path, authorizing_policy_id=1, automatic_quarantine_enabled=True,
               orphan_lease_hygiene="auto")
    lock = _write_lock(tmp_path, "SOAK-OLD", expires=PAST, instance=None)
    logs = []
    q = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="s", evidence=[str(lock)],
        cycle_id="C", observer="o", ledger_append=logs.append, repo_root=tmp_path,
    )
    assert q["executed"] is False
    assert q["blocked"] == "GOVERNANCE_DENY_NO_APPROVED_POLICY"
    assert lock.exists()


def test_missing_ledger_fails_closed(tmp_path):
    """No ledger => no observation. The daemon must refuse to run rather than
    observe with no audit trail, and must not conjure the ledger into existence."""
    ledger_root = tmp_path / "jspace"  # deliberately NOT created
    _write_gov(tmp_path)
    calls = []

    d = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                   cycle_fn=lambda **kw: calls.append(1), instance_id="hjos-1")
    pf = d.preflight()
    assert pf["ok"] is False
    assert pf["fail_closed"] is True
    assert "LEDGER_MISSING" in pf["reasons"]

    r = d.run_cycle()
    assert r["status"] == "FAIL_CLOSED"
    assert r["cycle_ran"] is False
    assert calls == [], "daemon ran a cycle with no ledger to record it in"
    assert not ledger_root.exists(), "daemon auto-created the ledger it should have failed on"
    assert d.status()["consecutive_failures"] == 1


def test_missing_governance_file_fails_closed(tmp_path):
    """No governance document at all => mutation denied (not defaulted to allow)."""
    ledger_root = tmp_path / "jspace"
    ledger_root.mkdir(parents=True)
    d = HJOSDaemon(repo_root=tmp_path, ledger_root=ledger_root,
                   cycle_fn=lambda **kw: {"overall": "CONFIRMED_LIVE"}, instance_id="hjos-1")
    pf = d.preflight()
    assert pf["mutation_authorized"] is False
    v = validate_governance({"_missing": True})
    assert v["valid"] is False


# ====================================================================== CONTAINMENT
def test_containment_requires_policy_authorization(tmp_path):
    """Extends the existing gate test: prove the DENY also leaves the disk alone
    and writes a NONE-authority ledger row."""
    _write_gov(tmp_path, authorizing_policy_id=None, automatic_quarantine_enabled=True)
    lock = _write_lock(tmp_path, "VICTIM", expires=PAST)
    before = _tree(_lease_dir(tmp_path))

    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="VICTIM",
        evidence=[str(lock)], cycle_id="C1", observer="jspace_security_sentinel",
        ledger_append=logs.append, repo_root=tmp_path,
    )
    assert r["executed"] is False
    assert r["blocked"] == "GOVERNANCE_DENY_NO_APPROVED_POLICY"
    assert r["governance_policy_id"] is None
    assert _tree(_lease_dir(tmp_path)) == before
    assert logs and logs[-1]["execution_authority"] == "NONE"


def test_unsupported_class_is_denied_and_creates_nothing(tmp_path):
    """Even fully authorized, a class outside the charter must be refused, and
    the refusal must not leave a quarantine directory behind."""
    _authorized_gov(tmp_path)
    _write_lock(tmp_path, "VICTIM", expires=PAST)
    before = _tree(_lease_dir(tmp_path))

    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="please_delete_everything", subject="VICTIM",
        evidence=[], cycle_id="C1", observer="o",
        ledger_append=logs.append, repo_root=tmp_path,
    )
    assert r["executed"] is False
    assert r["blocked"] in ("CLASS_NOT_PERMITTED", "CHARTER_DENY")
    assert _tree(_lease_dir(tmp_path)) == before


def test_false_positive_does_not_mutate_state(tmp_path):
    """An authorized containment whose evidence matches nothing must be a NO-OP.
    It must not even leave an empty quarantine directory — a false positive that
    mutates the tree is a false positive that lies about what it touched."""
    _authorized_gov(tmp_path)
    _write_lock(tmp_path, "INNOCENT", expires=FUTURE)
    before = _tree(_lease_dir(tmp_path))

    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="ghost",
        evidence=["coordination/leases/DOES_NOT_EXIST.lock"],
        cycle_id="C1", observer="o", ledger_append=logs.append, repo_root=tmp_path,
    )
    assert r["executed"] is False
    assert r["blocked"] == "NO_MATCHING_EVIDENCE"
    assert r["artifacts"] == []
    assert _tree(_lease_dir(tmp_path)) == before, "false positive mutated the lease tree"


def test_original_observation_is_immutable_after_containment(tmp_path):
    """Containment must never rewrite the observation that triggered it."""
    _authorized_gov(tmp_path)
    ledger = JSpaceLedger(tmp_path / "jspace")
    obs = {
        "schema": "JSPACE_ASSESSMENT_v1",
        "observation_id": "JOBS-TEST-1",
        "subject": "VICTIM",
        "assessment": "CONTRADICTED",
        "observer": "jspace_evidence_auditor",
        "state_mutated": False,
    }
    ledger.assessments_path.write_text(json.dumps(obs, sort_keys=True) + "\n", encoding="utf-8")
    before_digest = _sha256(ledger.assessments_path)

    lock = _write_lock(tmp_path, "VICTIM", expires=PAST)
    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="VICTIM",
        evidence=[str(lock)], cycle_id="C1", observer="jspace_evidence_auditor",
        observation_id="JOBS-TEST-1",
        ledger_append=ledger.record_containment, repo_root=tmp_path,
    )
    assert r["executed"] is True

    assert _sha256(ledger.assessments_path) == before_digest, \
        "containment rewrote the original observation"
    rows = ledger.read_jsonl(ledger.quarantine_requests_path)
    assert rows[-1]["observation_id"] == "JOBS-TEST-1"  # linked, not overwritten
    assert json.loads(ledger.assessments_path.read_text().strip()) == obs


def test_observer_cannot_mark_its_own_containment_independently_verified(tmp_path):
    """Independent verification cannot be self-issued. The observer that contained
    is exactly the party that cannot certify the containment."""
    _authorized_gov(tmp_path)
    lock = _write_lock(tmp_path, "VICTIM", expires=PAST)
    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="VICTIM",
        evidence=[str(lock)], cycle_id="C1", observer="jspace_security_sentinel",
        ledger_append=logs.append, repo_root=tmp_path,
    )
    assert r["executed"] is True
    # the containment record ships UNVERIFIED by construction
    assert r["independently_verified"] is False
    assert r["verification_authority"] == "EXTERNAL_REQUIRED"

    # the acting observer cannot attest
    with pytest.raises(PermissionError) as exc:
        attest_containment_verification(r, actor="jspace_security_sentinel",
                                        ledger_append=logs.append)
    assert "SELF_VERIFICATION" in str(exc.value)

    # nor can any other HJOS observer, nor HJOS itself
    for actor in ("jspace_meta_observer", "HJOS", "hjos_daemon"):
        with pytest.raises(PermissionError):
            attest_containment_verification(r, actor=actor, ledger_append=logs.append)

    # and the record still says unverified
    assert r["independently_verified"] is False


def test_external_actor_can_attest_and_it_is_recorded_separately(tmp_path):
    """The self-verification ban must be a real authority check, not a blanket
    refusal that makes verification impossible."""
    _authorized_gov(tmp_path)
    lock = _write_lock(tmp_path, "VICTIM", expires=PAST)
    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="VICTIM",
        evidence=[str(lock)], cycle_id="C1", observer="jspace_security_sentinel",
        ledger_append=logs.append, repo_root=tmp_path,
    )
    att = attest_containment_verification(r, actor="founder", ledger_append=logs.append)
    assert att["independently_verified"] is True
    assert att["verified_by"] == "founder"
    assert att["containment_id"] == r["containment_id"]
    assert att["schema"] == "HJOS_CONTAINMENT_VERIFICATION_v1"
    # attestation is a SEPARATE append-only row, not an edit of the containment row
    assert len(logs) == 2
    assert logs[-1]["schema"] == "HJOS_CONTAINMENT_VERIFICATION_v1"
    assert logs[0]["schema"] == "HJOS_CONTAINMENT_v1"
    assert logs[0]["containment_id"] == r["containment_id"]
    assert logs[0]["independently_verified"] is False  # the containment row still says unverified


def test_containment_writes_complete_provenance(tmp_path):
    """Containment must record who, what, when, under what authority, and the
    exact before/after bytes and paths of every artifact it touched."""
    _authorized_gov(tmp_path)
    ledger = JSpaceLedger(tmp_path / "jspace")
    lock = _write_lock(tmp_path, "VICTIM", expires=PAST)
    src_digest = _sha256(lock)

    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="VICTIM",
        evidence=[str(lock)], cycle_id="C1", observer="jspace_security_sentinel",
        ledger_append=ledger.record_containment, repo_root=tmp_path,
    )
    assert r["executed"] is True

    required = {
        "schema", "containment_id", "cycle_id", "observer", "reason", "class",
        "subject", "evidence", "executed", "execution_authority",
        "governance_policy_id", "artifacts", "started_at", "completed_at",
        "host", "pid", "independently_verified", "verification_authority",
        "rollback_supported",
    }
    missing = required - set(r)
    assert not missing, f"incomplete provenance, missing: {sorted(missing)}"
    assert r["governance_policy_id"] == "FOUNDER-POLICY-TEST-0001"
    assert r["execution_authority"] == "HJOS_CONTAINMENT_UNDER_POLICY"
    assert r["rollback_supported"] is True

    art = r["artifacts"][0]
    assert art["sha256_before"] == src_digest
    assert art["sha256_after"] == src_digest  # containment moves, it does not edit
    assert Path(art["source_path"]).name == "VICTIM.lock"
    assert (tmp_path / art["dest_path"]).exists()

    # the ledger row is the truth, not a hardcoded executed:false
    row = ledger.read_jsonl(ledger.quarantine_requests_path)[-1]
    assert row["executed"] is True
    assert row["execution_authority"] == "HJOS_CONTAINMENT_UNDER_POLICY"
    assert row["artifacts"][0]["sha256_before"] == src_digest
    assert not missing


# =================================================================== LEASE HYGIENE
def test_missing_authority_id_does_not_alone_prove_orphan(tmp_path):
    """Absence of scheduler_instance_id is NOT evidence of death. Only an EXPIRED
    lock from a non-current instance may be quarantined — and the record must say
    which criteria actually matched."""
    _authorized_gov(tmp_path)
    live_unexpired = _write_lock(tmp_path, "NO-ID-BUT-ALIVE", expires=FUTURE, instance=None)
    truly_orphan = _write_lock(tmp_path, "NO-ID-AND-EXPIRED", expires=PAST, instance=None)

    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live-1", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C1",
    )
    assert live_unexpired.exists(), "missing authority id was treated as proof of orphan"
    assert not truly_orphan.exists()

    skipped = {s["lock"]: s["reason"] for s in r["skipped"]}
    assert skipped["NO-ID-BUT-ALIVE.lock"] == "NOT_EXPIRED"
    matched = r["artifacts"][0]["criteria"]
    assert set(matched) == {"STATUS_ACTIVE", "EXPIRED", "INSTANCE_NOT_CURRENT"}


def test_quarantine_destination_collision_does_not_clobber(tmp_path):
    """Two quarantines landing on the same destination name must both survive.
    Overwriting a quarantined artifact is evidence destruction."""
    _authorized_gov(tmp_path)
    qdir = _lease_dir(tmp_path) / "_quarantine_hjos_orphans_FIXED"
    qdir.mkdir()
    incumbent = qdir / "SOAK-DEAD.lock"
    incumbent.write_text('{"task_id": "SOAK-DEAD", "generation": "first"}\n', encoding="utf-8")
    incumbent_digest = _sha256(incumbent)

    _write_lock(tmp_path, "SOAK-DEAD", expires=PAST, instance="dead-2")
    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live-1", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C2", quarantine_dir=qdir,
    )
    assert r["executed"] is True
    art = r["artifacts"][0]
    assert art["collision"] is True
    assert Path(art["dest_path"]).name != "SOAK-DEAD.lock"
    # the incumbent evidence is byte-identical — nothing was clobbered
    assert _sha256(incumbent) == incumbent_digest
    assert (tmp_path / art["dest_path"]).exists()
    assert len(list(qdir.glob("SOAK-DEAD.lock*"))) >= 2


def test_quarantined_evidence_bytes_are_not_modified(tmp_path):
    """Quarantine PRESERVES evidence. Annotations belong in a sidecar, not written
    over the artifact under audit."""
    _authorized_gov(tmp_path)
    lock = _write_lock(tmp_path, "SOAK-DEAD", expires=PAST, instance="dead-1")
    before = _sha256(lock)

    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live-1", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C1",
    )
    art = r["artifacts"][0]
    dest = tmp_path / art["dest_path"]
    assert _sha256(dest) == before, "quarantine rewrote the evidence it captured"

    sidecar = Path(str(dest) + ".hjos.json")
    assert sidecar.exists()
    ann = json.loads(sidecar.read_text())
    assert ann["release_reason"] == "HJOS_ORPHAN_EXPIRED_QUARANTINE"
    assert ann["do_not_retrofit_authority"] is True
    assert ann["sha256_before"] == before


def test_rollback_restores_exact_bytes_and_path(tmp_path):
    """Reversibility is the whole justification for 'move, don't delete'. Prove it:
    hash before == hash after, and the path is the ORIGINAL path."""
    _authorized_gov(tmp_path)
    lock = _write_lock(tmp_path, "SOAK-DEAD", expires=PAST, instance="dead-1")
    original_path = str(lock)
    before = _sha256(lock)

    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live-1", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C1",
    )
    assert r["executed"] is True
    assert not lock.exists()

    rb = rollback_containment(record=r, repo_root=tmp_path, actor="founder",
                              ledger_append=logs.append)
    assert rb["rolled_back"] is True
    assert Path(original_path).exists()
    assert _sha256(Path(original_path)) == before, "rollback did not restore exact bytes"
    assert rb["artifacts"][0]["restored_to"] == r["artifacts"][0]["source_path"]
    assert rb["artifacts"][0]["sha256_verified"] is True
    # quarantine copy is gone; nothing is left in two places
    assert not (tmp_path / r["artifacts"][0]["dest_path"]).exists()
    # rollback is attributed and append-only
    assert rb["actor"] == "founder"
    assert logs[-1]["schema"] == "HJOS_CONTAINMENT_ROLLBACK_v1"


def test_rollback_refuses_on_tampered_artifact(tmp_path):
    """If the quarantined bytes no longer match the recorded digest, rollback must
    FAIL CLOSED rather than restore something it cannot vouch for."""
    _authorized_gov(tmp_path)
    lock = _write_lock(tmp_path, "SOAK-DEAD", expires=PAST, instance="dead-1")
    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live-1", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C1",
    )
    dest = tmp_path / r["artifacts"][0]["dest_path"]
    dest.write_text('{"task_id": "TAMPERED"}\n', encoding="utf-8")  # someone edited evidence

    rb = rollback_containment(record=r, repo_root=tmp_path, actor="founder",
                              ledger_append=logs.append)
    assert rb["rolled_back"] is False
    assert rb["blocked"] == "ARTIFACT_DIGEST_MISMATCH"
    assert not lock.exists(), "restored tampered bytes to the live lease tree"
