"""collectors.py — live-state collectors for the HELM Founder Live board.

Proposed by EDR-0009. Companion to `mission_envelope.py` (EDR-0008).

TWO DIFFERENT KINDS OF TRUTH
----------------------------
    Mission Envelope  -> HISTORY.    What a mission did. Written once, at close.
    Collector Reading -> LIVE STATE. What the machine IS. Re-read at every render.

The founder's 2026-07-20 critique was precise: a board of envelopes answers "which
envelopes exist," not "what is the machine doing." This module answers the second
question by reading real system state at render time.

THE CENTRAL RULE: FRESHNESS GATES TRUTH, AND CANNOT BE OVERRIDDEN
------------------------------------------------------------------
Every HELM runtime signal on disk currently *says* healthy and is days old:

    helm_supervisor_heartbeat.json   "HEALTHY", backend PID 12846 RUNNING   6 days old
    live_telemetry_freshness.json    "status": "PASS"                      17 days old
    council_heartbeat.jsonl          "state": "ACTIVE", loop HEALTHY       36 hours old

Rendering those verbatim would be the most dangerous fake green in the system: a dead
process shown as running, with a PID that lends it false precision. So a Reading's truth
class is **computed from its age against a declared SLA**, and the payload's own opinion
of itself is never consulted:

    read succeeded, within SLA      -> OBSERVED  (advancing)
    computed from fresh inputs      -> DERIVED   (advancing)
    read succeeded, past SLA        -> CACHED    (NOT advancing)  <- the important one
    absent / unreadable / no target -> UNKNOWN   (NOT advancing)

CACHED is already non-advancing in the ratified `proof_contract` vocabulary, so a stale
"HEALTHY" is structurally incapable of turning a panel green. No new vocabulary is
introduced.

HOST SCOPE: THIS MACHINE VS. THAT MACHINE
------------------------------------------
Collectors declare what host they observe. A collector running in the Builder sandbox
CANNOT see processes on michaels-macbook-pro; it can only see files that host left
behind. Those readings are INDIRECT and are never labelled OBSERVED-live, no matter how
recent. Conflating "I read a file the Mac wrote" with "I can see the Mac" is exactly the
class of error this module exists to prevent.
"""
from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:  # pragma: no cover
    from backend.helm_runtime.mission_contract import Truth, ADVANCING
except Exception:  # pragma: no cover
    from helm_runtime.mission_contract import Truth, ADVANCING  # type: ignore

ROOT = Path(__file__).resolve().parents[2]

# Host scope
SCOPE_LOCAL = "LOCAL"        # the process running this collector
SCOPE_INDIRECT = "INDIRECT"  # a file another host left behind
SCOPE_REMOTE = "REMOTE"      # a host we would need network access to see

# The runtime host HELM actually runs on, per worker_heartbeats.json.
HELM_RUNTIME_HOST = "michaels-macbook-pro"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _file_mtime(p: Path) -> Optional[datetime]:
    """Filesystem modification time — METADATA ONLY.

    W1-002a: this value may be displayed so an operator can spot a touched file. It must
    never be assigned to produced-time. A git checkout, pull, stash pop, rsync, or backup
    restore rewrites mtime without changing content.
    """
    try:
        return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)  # mtime-metadata-ok
    except Exception:
        return None


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    s = str(raw).strip().replace("Z", "+00:00")
    # tolerate the '+00:00Z' shape seen in worker_heartbeats.json
    if s.endswith("+00:00+00:00"):
        s = s[: -len("+00:00")]
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class Reading:
    """One live observation. Truth is derived from freshness; never declared."""
    name: str
    domain: str
    scope: str
    collector: str
    sla_seconds: int
    value: Dict[str, Any] = field(default_factory=dict)
    observed_at: Optional[datetime] = None   # when the DATA was produced
    read_at: datetime = field(default_factory=_now)
    error: Optional[str] = None
    source_path: Optional[str] = None
    _computed: bool = False                  # DERIVED rather than OBSERVED
    # W1-002a provenance. file_modified_at is METADATA — it is recorded so an operator
    # can see a touched file, and is never permitted to become produced-time.
    file_modified_at: Optional[datetime] = None
    producer_id: Optional[str] = None
    sequence: Optional[int] = None

    @property
    def age_seconds(self) -> Optional[float]:
        if self.observed_at is None:
            return None
        return max(0.0, (self.read_at - self.observed_at).total_seconds())

    @property
    def is_stale(self) -> bool:
        age = self.age_seconds
        return age is not None and age > self.sla_seconds

    @property
    def truth(self) -> Truth:
        """Derived. The payload's self-description is never consulted."""
        if self.error or not self.value:
            return Truth.UNKNOWN
        if self.observed_at is None:
            return Truth.UNKNOWN
        if self.is_stale:
            return Truth.CACHED          # a stale HEALTHY is not evidence of health
        return Truth.DERIVED if self._computed else Truth.OBSERVED

    @property
    def advancing(self) -> bool:
        return self.truth in ADVANCING

    @property
    def age_human(self) -> str:
        age = self.age_seconds
        if age is None:
            return "never"
        if age < 90:
            return f"{age:.0f}s"
        if age < 5400:
            return f"{age/60:.0f}m"
        if age < 172800:
            return f"{age/3600:.1f}h"
        return f"{age/86400:.1f}d"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "scope": self.scope,
            "collector": self.collector,
            "truth": self.truth.value,
            "advancing": self.advancing,
            "stale": self.is_stale,
            "age_seconds": self.age_seconds,
            "age_human": self.age_human,
            "sla_seconds": self.sla_seconds,
            # produced_at is the authoritative data age. observed_at is retained as its
            # alias for existing consumers; file_modified_at is metadata only.
            "produced_at": self.observed_at.isoformat() if self.observed_at else None,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "collected_at": self.read_at.isoformat(),
            "file_modified_at": (self.file_modified_at.isoformat()
                                 if self.file_modified_at else None),
            "producer_id": self.producer_id,
            "sequence": self.sequence,
            "read_at": self.read_at.isoformat(),
            "value": self.value,
            "error": self.error,
            "source_path": self.source_path,
        }


# --- collector base ----------------------------------------------------------

class Collector:
    """A collector NEVER raises. A collector that fails yields an UNKNOWN Reading."""
    name = "collector"
    domain = "engineering"
    scope = SCOPE_LOCAL
    sla_seconds = 300

    def collect(self) -> List[Reading]:  # pragma: no cover - overridden
        raise NotImplementedError

    def safe_collect(self) -> List[Reading]:
        try:
            return self.collect()
        except Exception as exc:
            return [Reading(
                name=self.name, domain=self.domain, scope=self.scope,
                collector=type(self).__name__, sla_seconds=self.sla_seconds,
                error=f"collector raised: {exc}",
            )]

    def _fail(self, name: str, err: str, path: Optional[str] = None) -> Reading:
        return Reading(
            name=name, domain=self.domain, scope=self.scope,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            error=err, source_path=path,
        )


# --- 1. Git: genuinely live, this host ---------------------------------------

class GitCollector(Collector):
    """Real repository state. Observed directly, so no staleness concept applies."""
    name = "git"
    domain = "engineering"
    scope = SCOPE_LOCAL
    sla_seconds = 10

    def collect(self) -> List[Reading]:
        def git(*args: str) -> Optional[str]:
            try:
                r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                   text=True, timeout=15)
                return r.stdout.strip() if r.returncode == 0 else None
            except Exception:
                return None

        head = git("rev-parse", "--short", "HEAD")
        if head is None:
            return [self._fail("git", "git unavailable or not a repository")]

        porcelain = git("status", "--porcelain") or ""
        dirty = [l for l in porcelain.splitlines() if l.strip()]
        subject = git("log", "-1", "--pretty=%s") or ""
        commit_ts = _parse_ts(git("log", "-1", "--date=iso-strict", "--pretty=%cd"))

        return [Reading(
            name="git", domain=self.domain, scope=self.scope,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            observed_at=_now(),  # read live, right now
            source_path=str(ROOT),
            value={
                "head": head,
                "branch": git("rev-parse", "--abbrev-ref", "HEAD") or "?",
                "tree": (git("rev-parse", "HEAD^{tree}") or "?")[:12],
                "worktree": "CLEAN" if not dirty else f"DIRTY ({len(dirty)} files)",
                "dirty_count": len(dirty),
                "last_commit": subject[:60],
                "last_commit_at": commit_ts.isoformat() if commit_ts else None,
                "last_commit_age": (
                    f"{(_now()-commit_ts).total_seconds()/3600:.1f}h" if commit_ts else "?"
                ),
            },
        )]


# --- 2. Tests: live, but only if actually executed ---------------------------

class TestCollector(Collector):  # noqa: N801 - pytest may warn; not a test class
    """Runs the suite. TEST_EXECUTION -> OBSERVED. Never reports a cached result."""
    name = "tests"
    domain = "qualification"
    scope = SCOPE_LOCAL
    sla_seconds = 3600

    def __init__(self, target: str = "tests/unit", timeout: int = 180, run: bool = True):
        self.target = target
        self.timeout = timeout
        self.run = run

    def collect(self) -> List[Reading]:
        if not self.run:
            return [self._fail("tests", "not executed this cycle (run=False)")]
        started = time.time()
        try:
            r = subprocess.run(
                ["python3", "-m", "pytest", self.target, "-q", "--no-header", "-p", "no:cacheprovider"],
                cwd=ROOT, capture_output=True, text=True, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return [self._fail("tests", f"pytest exceeded {self.timeout}s")]
        except Exception as exc:
            return [self._fail("tests", f"pytest unavailable: {exc}")]

        import re
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        passed = failed = errors = 0
        for line in reversed(out.splitlines()):
            if " passed" in line or " failed" in line or " error" in line:
                for tok in ("passed", "failed", "error"):
                    m = re.search(rf"(\d+) {tok}", line)
                    if m:
                        n = int(m.group(1))
                        if tok == "passed":
                            passed = n
                        elif tok == "failed":
                            failed = n
                        else:
                            errors = n
                if passed or failed or errors:
                    break

        # A COLLECTION error is environmental (missing dependency, bad import). It is
        # NOT evidence that the code is broken — reporting it as FAIL would be fake red,
        # the mirror of fake green. If nothing ran, we do not know; say so.
        collection_broken = "during collection" in out or "ImportError while importing" in out
        missing = sorted(set(re.findall(r"No module named '([^']+)'", out)))
        executed = passed + failed > 0

        if collection_broken and not executed:
            return [Reading(
                name="tests", domain=self.domain, scope=self.scope,
                collector=type(self).__name__, sla_seconds=self.sla_seconds,
                source_path=self.target,
                error=(f"suite not executable in this environment: {errors} collection "
                       f"error(s)" + (f"; missing modules: {', '.join(missing[:4])}"
                                      if missing else "")),
                value={},   # no value -> truth UNKNOWN, never a PASS or FAIL claim
            )]

        verdict = "PASS" if r.returncode == 0 else "FAIL"
        return [Reading(
            name="tests", domain=self.domain, scope=self.scope,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            observed_at=_now(), source_path=self.target,
            value={
                "target": self.target,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "collection_errors": collection_broken,
                "missing_modules": missing,
                "exit_code": r.returncode,
                "verdict": verdict,
                "duration_s": round(time.time() - started, 1),
            },
        )]


# --- 3. Heartbeat files: INDIRECT, freshness-gated ---------------------------

class HeartbeatFileCollector(Collector):
    """Reads a heartbeat another host wrote. NEVER 'live' — INDIRECT at best.

    This is where the stale-HEALTHY danger lives. `helm_supervisor_heartbeat.json`
    says HEALTHY with running PIDs and is six days old. The SLA turns it CACHED,
    which is non-advancing, so it cannot render green.
    """
    scope = SCOPE_INDIRECT

    def __init__(self, name: str, rel_path: str, domain: str, sla_seconds: int,
                 ts_key: str = "timestamp",
                 summarize: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None):
        self.name = name
        self.rel_path = rel_path
        self.domain = domain
        self.sla_seconds = sla_seconds
        self.ts_key = ts_key
        self.summarize = summarize

    def collect(self) -> List[Reading]:
        p = ROOT / self.rel_path
        if not p.exists():
            return [self._fail(self.name, "heartbeat file absent", self.rel_path)]
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return [self._fail(self.name, f"unreadable: {exc}", self.rel_path)]

        # W1-002a: producer timestamp only. The mtime fallback that used to live here
        # let a `git checkout` / `pull` / rsync reset apparent data age without changing
        # content. Absent or malformed provenance now propagates as UNKNOWN.
        raw_ts = raw.get(self.ts_key) if isinstance(raw, dict) else None
        ts = _parse_ts(raw_ts)
        file_mtime = _file_mtime(p)   # recorded as metadata; never produced-time

        if ts is None:
            why = ("heartbeat carries no producer timestamp"
                   if raw_ts in (None, "")
                   else f"producer timestamp {raw_ts!r} is malformed")
            r = self._fail(self.name, f"{why}; file mtime is not evidence of data age",
                           self.rel_path)
            r.file_modified_at = file_mtime
            return [r]

        value = self.summarize(raw) if self.summarize else (
            raw if isinstance(raw, dict) else {"data": raw}
        )
        return [Reading(
            name=self.name, domain=self.domain, scope=self.scope,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            observed_at=ts, value=value, source_path=self.rel_path,
            file_modified_at=file_mtime,
            producer_id=raw.get("producer_id") if isinstance(raw, dict) else None,
            sequence=raw.get("sequence") if isinstance(raw, dict) else None,
        )]


class JsonlHeartbeatCollector(Collector):
    """Last line of an append-only heartbeat log."""
    scope = SCOPE_INDIRECT

    def __init__(self, name: str, rel_path: str, domain: str, sla_seconds: int,
                 summarize: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None):
        self.name = name
        self.rel_path = rel_path
        self.domain = domain
        self.sla_seconds = sla_seconds
        self.summarize = summarize

    def collect(self) -> List[Reading]:
        p = ROOT / self.rel_path
        if not p.exists():
            return [self._fail(self.name, "log absent", self.rel_path)]
        last = None
        try:
            with open(p, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        last = line
        except Exception as exc:
            return [self._fail(self.name, f"unreadable: {exc}", self.rel_path)]
        if not last:
            return [self._fail(self.name, "log empty", self.rel_path)]
        try:
            raw = json.loads(last)
        except Exception as exc:
            return [self._fail(self.name, f"last line unparseable: {exc}", self.rel_path)]

        ts = _parse_ts(raw.get("ts") or raw.get("timestamp"))
        value = self.summarize(raw) if self.summarize else raw
        return [Reading(
            name=self.name, domain=self.domain, scope=self.scope,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            observed_at=ts, value=value, source_path=self.rel_path,
        )]


# --- 4. Worker / host liveness ------------------------------------------------

class WorkerHeartbeatCollector(Collector):
    """One reading per known worker host, each independently freshness-gated."""
    name = "workers"
    domain = "engineering"
    scope = SCOPE_INDIRECT
    sla_seconds = 300

    REL = "has_live_project_tracker/data/worker_heartbeats.json"

    def collect(self) -> List[Reading]:
        p = ROOT / self.REL
        if not p.exists():
            return [self._fail("workers", "worker heartbeat file absent", self.REL)]
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return [self._fail("workers", f"unreadable: {exc}", self.REL)]

        out: List[Reading] = []
        for host, ts_raw in sorted((raw or {}).items()):
            ts = _parse_ts(ts_raw)
            out.append(Reading(
                name=f"host:{host}", domain=self.domain, scope=self.scope,
                collector=type(self).__name__, sla_seconds=self.sla_seconds,
                observed_at=ts, source_path=self.REL,
                value={"host": host, "is_helm_runtime_host": host == HELM_RUNTIME_HOST},
            ))
        return out


# --- 5. Processes: honest about what this host can and cannot see -------------

class ProcessCollector(Collector):
    """Process telemetry for the host this collector runs on — and ONLY that host.

    If the collector is not running on the HELM runtime host, it says so and returns
    UNKNOWN rather than presenting sandbox PIDs as HELM's runtime. The founder asked
    for PID / CPU / RAM; the honest answer from here is 'I am not on that machine.'
    """
    name = "processes"
    domain = "engineering"
    scope = SCOPE_LOCAL
    sla_seconds = 30

    def collect(self) -> List[Reading]:
        host = platform.node()
        if host != HELM_RUNTIME_HOST:
            return [Reading(
                name="processes", domain=self.domain, scope=SCOPE_REMOTE,
                collector=type(self).__name__, sla_seconds=self.sla_seconds,
                error=(f"collector host '{host}' is not the HELM runtime host "
                       f"'{HELM_RUNTIME_HOST}'; process table not observable from here"),
                value={},
            )]
        try:
            r = subprocess.run(["ps", "-Ao", "pid,pcpu,rss,etime,comm"],
                               capture_output=True, text=True, timeout=10)
            lines = [l for l in r.stdout.splitlines()[1:] if l.strip()]
        except Exception as exc:
            return [self._fail("processes", f"ps failed: {exc}")]
        return [Reading(
            name="processes", domain=self.domain, scope=SCOPE_LOCAL,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            observed_at=_now(), value={"host": host, "count": len(lines)},
        )]


# --- 6. Model bindings: declared config vs. observed invocation ---------------

class ModelBindingCollector(Collector):
    """Which model is bound to which role. This is CONFIG, not liveness.

    The founder asked for 'Claude Opus ACTIVE / Grok NOT INVOKED'. Role bindings are
    readable; per-model invocation state is not exposed by any HELM runtime surface
    today. Reporting a binding as 'ACTIVE' would be inventing liveness from config, so
    this collector reports the binding and marks invocation state explicitly unknown.
    """
    name = "models"
    domain = "engineering"
    scope = SCOPE_LOCAL
    sla_seconds = 86400
    REL = "coordination/governance/role_bindings.json"

    def collect(self) -> List[Reading]:
        p = ROOT / self.REL
        if not p.exists():
            return [self._fail("models", "role_bindings.json absent", self.REL)]
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return [self._fail("models", f"unreadable: {exc}", self.REL)]
        # W1-002a: role_bindings.json carries no producer timestamp. Ageing it by mtime
        # meant a git checkout reset its apparent freshness. It is configuration, not a
        # heartbeat — so it reports UNKNOWN provenance rather than inferred freshness.
        ts = _parse_ts(raw.get("produced_at") if isinstance(raw, dict) else None)
        r0 = Reading(
            name="models", domain=self.domain, scope=self.scope,
            collector=type(self).__name__, sla_seconds=self.sla_seconds,
            observed_at=ts, source_path=self.REL, _computed=True,
            file_modified_at=_file_mtime(p),
            value={
                "bindings": raw if isinstance(raw, dict) else {"data": raw},
                "invocation_state": "NOT_OBSERVABLE",
                "note": "role binding is configuration; live invocation state has no "
                        "runtime surface in HELM today",
            },
        )
        if ts is None:
            r0.error = ("role bindings carry no producer timestamp; file mtime is not "
                        "evidence of data age")
        return [r0]


# --- registry ----------------------------------------------------------------

def _supervisor_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    procs = raw.get("processes") or {}
    return {
        "declared_status": raw.get("status"),
        "supervisor_pid": raw.get("supervisor_pid"),
        "processes": {k: v.get("status") for k, v in procs.items()},
        "pids": {k: v.get("pid") for k, v in procs.items()},
    }


def _council_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    lm = raw.get("loop_metrics") or {}
    mis = lm.get("missions") or {}
    return {
        "cycle": raw.get("cycle"),
        "declared_state": raw.get("state"),
        "declared_health": (raw.get("loop_health") or {}).get("state"),
        "dispatched": mis.get("dispatched"),
        "passed": mis.get("passed"),
        "failed": mis.get("failed"),
        "security_posture_percent": raw.get("security_posture_percent"),
        "open_findings": raw.get("open_findings"),
    }


def _sentinel_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "provable_now": raw.get("provable_now"),
        "unknown": raw.get("unknown"),
        "checks": {c.get("check"): c.get("detail") for c in (raw.get("cycle_results") or [])},
    }


def default_collectors(run_tests: bool = True) -> List[Collector]:
    return [
        GitCollector(),
        TestCollector(run=run_tests),
        ProcessCollector(),
        ModelBindingCollector(),
        WorkerHeartbeatCollector(),
        HeartbeatFileCollector(
            "helm_supervisor", "has_live_project_tracker/data/helm_supervisor_heartbeat.json",
            "engineering", sla_seconds=300, summarize=_supervisor_summary),
        HeartbeatFileCollector(
            "ag_daemon", "has_live_project_tracker/data/ag_daemon_heartbeat_status.json",
            "engineering", sla_seconds=300, ts_key="last_observed_heartbeat"),
        JsonlHeartbeatCollector(
            "council_loop", "coordination/council/council_heartbeat.jsonl",
            "factory", sla_seconds=600, summarize=_council_summary),
        JsonlHeartbeatCollector(
            "qa_sentinel", "coordination/founder/qa_sentinel_heartbeat.jsonl",
            "qualification", sla_seconds=1800, summarize=_sentinel_summary),
        HeartbeatFileCollector(
            "telemetry_freshness", "has_live_project_tracker/data/live_telemetry_freshness.json",
            "engineering", sla_seconds=1800, ts_key="generated_at"),
    ]


def collect_all(collectors: Optional[List[Collector]] = None,
                run_tests: bool = True) -> List[Reading]:
    cs = collectors if collectors is not None else default_collectors(run_tests=run_tests)
    out: List[Reading] = []
    for c in cs:
        out.extend(c.safe_collect())
    return out


def domain_verdict(readings: List[Reading], domain: str) -> str:
    """A domain is OBSERVED only if it has at least one advancing reading."""
    rs = [r for r in readings if r.domain == domain]
    if not rs:
        return "NO_COLLECTOR"
    if any(r.advancing for r in rs):
        return "OBSERVED"
    if any(r.truth == Truth.CACHED for r in rs):
        return "STALE"
    return "UNREACHABLE"
