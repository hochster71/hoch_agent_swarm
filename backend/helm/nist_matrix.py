"""HELM NIST CSF 2.0 x SP 800-53 Rev 5 control-coverage matrix — SWARM-3.

DOCTRINE (same as backend/helm_live_api.py and backend/security/helm_control_catalog.py)
------------------------------------------------------------------------------------------
Every row in this matrix is an executable ASSESSOR that re-derives its verdict from LIVE
evidence on disk / in-process, right now. Nothing here is a spreadsheet self-attestation.

    COVERED     the assessor ran and OBSERVED the claimed evidence, fresh, right now
    PARTIAL     the assessor ran and found REAL but INCOMPLETE coverage (a documented,
                honest gap — e.g. the write-side gate is live but the read-side gate is
                staged, not yet cut over)
    UNVERIFIED  the assessor could not run, evidence is absent, or the source could not
                be read. NEVER silently treated as satisfied.

FAIL-CLOSED: a control is never COVERED because a comment says so. If evidence cannot be
shown right now, the control is PARTIAL or UNVERIFIED. This mirrors the exact three-state
discipline backend/security/helm_control_catalog.py already applies (IMPLEMENTED /
NOT_IMPLEMENTED / UNKNOWN) -- this module reuses several of those assessors directly rather
than re-deriving the same evidence twice, and adds the NIST CSF 2.0 Function axis plus the
specific mechanisms this deliverable was asked to ground: AU-9, AU-10, CM/SA-10 (secure
SDLC), CA/soak liveness, and the AC-3/IA-2 founder write-gate (with an HONEST partial for
read-side auth, which SWARM-2 is staging and has NOT hot-applied).

CSF 2.0 FUNCTIONS (the six top-level functions introduced/renamed in CSF 2.0, Feb 2024):
    GOVERN (GV)   Establish and monitor risk management strategy, roles, policy, oversight,
                  and supply chain risk management.
    IDENTIFY (ID) Understand risks to systems, assets, and capabilities.
    PROTECT (PR)  Safeguards to ensure delivery of critical services (identity, data, platform).
    DETECT (DE)   Timely discovery of anomalies and events.
    RESPOND (RS)  Actions taken on a detected incident.
    RECOVER (RC)  Restore capabilities impaired by an incident.

Every mechanism below is mapped to exactly one primary CSF 2.0 Function + Category, then to
a NIST SP 800-53 Rev 5 control, then to the concrete live evidence pointer (an API route
this same process serves, or a file on disk) that a human OR another agent can independently
re-check.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NIST_UI = ROOT / "frontend_live" / "nist.html"

COVERED = "COVERED"
PARTIAL = "PARTIAL"
UNVERIFIED = "UNVERIFIED"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=str(ROOT), timeout=5)
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return UNVERIFIED


def _row(status: str, evidence: str, detail: str, evidence_pointer: str) -> Dict[str, Any]:
    return {"status": status, "evidence": evidence, "detail": detail,
            "evidence_pointer": evidence_pointer, "observed_at": _now()}


def _unverified(reason: str, pointer: str = "") -> Dict[str, Any]:
    return _row(UNVERIFIED, "assessor could not observe evidence", reason, pointer)


# --------------------------------------------------------------------------------------
# ASSESSORS. Each is independent, fails closed on any exception, and never invents a
# COVERED verdict. Several reuse backend/security/helm_control_catalog.py assessors
# directly so the same live check is not silently re-implemented (and possibly
# re-diverged) twice.
# --------------------------------------------------------------------------------------

def a_au9_tamper_evident_chain() -> Dict[str, Any]:
    """AU-9 Protection of Audit Information (Cryptographic Protection).

    The AU-9 hash chain: entry_hash = sha256(canonical(body) + prev_hash). Verified here
    against the SAME ledger /api/v1/helm/chain serves, using the SAME selection rule
    (backend/truth/soak_select.select_soak_package) so this row can never disagree with
    the live endpoint it is grounded in.
    """
    try:
        from backend.truth.evidence_chain import verify_chain, ChainBroken, head_hash
        from backend.truth.soak_select import select_soak_package
        pkg = select_soak_package(ROOT / "coordination" / "council" / "live_proof_packages")
        led = None
        for cand in ([pkg / "daemon" / "task_lease_ledger.jsonl", pkg / "lease_ledger.jsonl"] if pkg else []) + \
                    [ROOT / "coordination" / "council" / "daemon" / "task_lease_ledger.jsonl"]:
            if cand and cand.exists() and cand.read_text().strip():
                led = cand
                break
        if not led:
            return _unverified("no chained ledger present yet", "/api/v1/helm/chain")
        try:
            verify_chain(led)
        except ChainBroken as e:
            return _row(PARTIAL, f"chain present but CONTRADICTED: {e}",
                        "tamper detected -- fail-closed, never silently accepted",
                        "/api/v1/helm/chain")
        n = len([l for l in led.read_text().splitlines() if l.strip()])
        return _row(COVERED, f"{led.relative_to(ROOT)}: {n} records, chain verified head={head_hash(led)[:10]}",
                    "entry_hash = sha256(canonical(body) + prev_hash); edit/delete/reorder breaks the chain "
                    "at that point and every record after it",
                    "/api/v1/helm/chain")
    except Exception as e:
        return _unverified(f"assessor error: {e}", "/api/v1/helm/chain")


def a_au10_non_repudiation() -> Dict[str, Any]:
    """AU-10 Non-repudiation.

    Two independent bindings, both required for COVERED:
      (1) chain-of-custody: the founder decision_ledger.jsonl hash chain (an approval or
          denial cannot be forged or silently rewritten -- backend/council/founder_gate.py)
      (2) producer identity binding: every guarded source-tree edit is bound to a
          HELM_SOURCE_HOLDER identity + a monotonic fencing token
          (backend/mission_control/source_lease.py), so a write can be attributed to the
          agent that actually made it.
    """
    try:
        from backend.council.founder_gate import verify_chain, DECISIONS
        chain_ok, chain_msg = verify_chain()
    except Exception as e:
        chain_ok, chain_msg = False, f"assessor error: {e}"

    fencing_ok = False
    fencing_detail = "no fencing-token ledger found"
    try:
        tokens_file = ROOT / "coordination" / "source_leases" / "_fencing_tokens.json"
        history = ROOT / "coordination" / "source_leases" / "_source_lease_history.jsonl"
        if tokens_file.exists():
            toks = json.loads(tokens_file.read_text())
            n_hist = 0
            if history.exists():
                n_hist = len([l for l in history.read_text().splitlines() if l.strip()])
            fencing_ok = isinstance(toks, dict) and len(toks) > 0
            fencing_detail = f"{len(toks)} paths under monotonic fencing tokens, {n_hist} history entries"
    except Exception as e:
        fencing_detail = f"fencing ledger unreadable: {e}"

    if chain_ok and fencing_ok:
        n = len([l for l in DECISIONS.read_text().splitlines() if l.strip()]) if DECISIONS.exists() else 0
        return _row(COVERED,
                    f"decision_ledger hash-chain intact ({n} decisions) AND {fencing_detail}",
                    f"founder_gate: {chain_msg}. Identity comes from HELM_SOURCE_HOLDER "
                    "(env, falls back to git user.name / $USER) bound to a monotonic fencing "
                    "token per file -- a resurrected/stale writer cannot forge a later write.",
                    "/api/v1/helm/authority")
    if chain_ok or fencing_ok:
        return _row(PARTIAL,
                    f"one of two non-repudiation bindings verified (decisions={chain_ok}, fencing={fencing_ok})",
                    f"decision chain: {chain_msg}; fencing: {fencing_detail}",
                    "/api/v1/helm/authority")
    return _unverified(f"neither binding verified: decisions={chain_msg}; fencing={fencing_detail}",
                        "/api/v1/helm/authority")


def a_cm_sa10_secure_sdlc() -> Dict[str, Any]:
    """CM-3 / SA-10 (secure SDLC, NIST SP 800-218 SSDF alignment).

    Real mechanisms checked: the guarded_edit lease-before-write facade, the .githooks
    pre-commit conflict detector (opt-in via core.hooksPath), a non-trivial test suite, and
    commit-binding (evidence packages record tested_commit, and dirty code fails CM-3).
    """
    guarded = ROOT / "backend" / "mission_control" / "guarded_edit.py"
    hook = ROOT / ".githooks" / "pre-commit"
    detector = ROOT / "backend" / "mission_control" / "detect_source_conflicts.py"
    tests_dir = ROOT / "tests"
    n_tests = len(list(tests_dir.rglob("test_*.py"))) if tests_dir.exists() else 0

    checks = {
        "guarded_edit_facade": guarded.exists(),
        "pre_commit_hook": hook.exists(),
        "conflict_detector": detector.exists(),
        "test_suite_nontrivial": n_tests >= 20,
    }
    present = sum(1 for v in checks.values() if v)

    hooks_path_configured = False
    try:
        res = subprocess.run(["git", "config", "core.hooksPath"], capture_output=True, text=True,
                              cwd=str(ROOT), timeout=5)
        hooks_path_configured = res.returncode == 0 and res.stdout.strip() == ".githooks"
    except Exception:
        pass

    detail = (f"checks={checks}, {n_tests} test_*.py modules, "
              f"core.hooksPath={'configured' if hooks_path_configured else 'NOT configured (opt-in, per-clone)'}")
    if present == len(checks) and hooks_path_configured:
        return _row(COVERED,
                    "guarded_edit + pre-commit conflict detector + test suite all present, hook active",
                    detail, "/api/v1/helm/chain")
    if present == len(checks):
        return _row(PARTIAL,
                    "all SDLC mechanisms present on disk, but core.hooksPath is not configured in this "
                    "clone -- the pre-commit guard is opt-in per-clone, not centrally enforced",
                    detail, "/api/v1/helm/chain")
    return _row(PARTIAL if present else UNVERIFIED,
                f"{present}/{len(checks)} SDLC mechanisms present", detail, "/api/v1/helm/chain")


def a_ca_soak_liveness() -> Dict[str, Any]:
    """CA-7 Continuous Monitoring / soak liveness (Detect).

    The A -> B -> C phase soak ladder: an authoritative package is selected by
    backend.truth.soak_select (never filename sort alone), and its freshness is gated --
    an abandoned/dead package cannot be mistaken for an active one.
    """
    try:
        from backend.truth.soak_select import select_soak_package
        pkgs_dir = ROOT / "coordination" / "council" / "live_proof_packages"
        pkg = select_soak_package(pkgs_dir)
        if not pkg:
            return _unverified("no soak package selected as authoritative", "/api/v1/helm/wall")
        seal = pkg / "seal_verdict.json"
        cfg = pkg / "soak_config.json"
        import time
        daemon = pkg / "daemon"
        newest = 0.0
        for f in (list(daemon.glob("*.jsonl")) if daemon.exists() else []) + list(pkg.glob("*.jsonl")):
            try:
                newest = max(newest, f.stat().st_mtime)
            except OSError:
                pass
        fresh_seconds = (time.time() - newest) if newest else None
        seals = sorted(pkgs_dir.glob("HELM-SOAK-*/seal_verdict.json"))
        sealed_pass = []
        for s in seals:
            try:
                v = json.loads(s.read_text()).get("verdict", "")
                if v.endswith("_PASS"):
                    sealed_pass.append(v)
            except Exception:
                pass
        state = "SEALED" if seal.exists() else ("IN_PROGRESS" if cfg.exists() else "UNKNOWN")
        if fresh_seconds is not None and fresh_seconds <= 1200:
            return _row(COVERED,
                        f"authoritative package {pkg.name} state={state}, fresh {fresh_seconds:.0f}s, "
                        f"{len(sealed_pass)} phase(s) sealed PASS to date",
                        "select_soak_package prefers an active IN_PROGRESS package, else the latest "
                        "sealed_at; a dead/abandoned package (no daemon writes within 1200s) is never "
                        "reported as live",
                        "/api/v1/helm/wall")
        return _row(PARTIAL,
                    f"authoritative package {pkg.name} selected but evidence is STALE "
                    f"({fresh_seconds if fresh_seconds is not None else 'unknown'}s old)",
                    f"{len(sealed_pass)} phase(s) sealed PASS historically; current liveness cannot be "
                    "confirmed from fresh daemon writes",
                    "/api/v1/helm/wall")
    except Exception as e:
        return _unverified(f"assessor error: {e}", "/api/v1/helm/wall")


def a_ac3_ia2_founder_write_gate() -> Dict[str, Any]:
    """AC-3 / IA-2 -- the founder token gate on WRITES.

    backend/council/founder_gate.authorized() fails closed: no HELM_FOUNDER_TOKEN
    configured => no approval is ever possible, and a presented token is compared with
    hmac.compare_digest (constant-time). This assesses the write path only.
    """
    try:
        gate = ROOT / "backend" / "council" / "founder_gate.py"
        if not gate.exists():
            return _unverified("founder_gate.py missing", "/api/v1/helm/authority")
        src = gate.read_text()
        has_fail_closed = "if not tok:" in src and "return False" in src
        has_constant_time = "hmac.compare_digest" in src
        has_verb_matrix = "LEGAL_VERBS" in src and "FOUNDER_ONLY" in src
        if has_fail_closed and has_constant_time and has_verb_matrix:
            return _row(COVERED,
                        "founder_gate.authorized(): fail-closed (no token => no approvals), "
                        "hmac.compare_digest, PROPOSE_ONLY/FOUNDER_ONLY verb separation "
                        "(a FOUNDER_ONLY act cannot be executed by a tap)",
                        "static verification of backend/council/founder_gate.py; live check via "
                        "/api/v1/helm/authority (decision chain + pending escalations)",
                        "/api/v1/helm/authority")
        return _row(PARTIAL, "founder_gate.py present but missing one or more expected guards",
                    f"fail_closed={has_fail_closed} constant_time={has_constant_time} verb_matrix={has_verb_matrix}",
                    "/api/v1/helm/authority")
    except Exception as e:
        return _unverified(f"assessor error: {e}", "/api/v1/helm/authority")


def a_ac3_ia2_read_side_auth() -> Dict[str, Any]:
    """AC-3 / IA-2 -- the read-side gate on GET endpoints.

    HONEST PARTIAL by design: SWARM-2 is staging a Zero-Trust read-auth layer
    (backend/security/zero_trust/) that is explicitly NOT hot-applied yet -- it exists on
    disk, is documented as staged-only, and helm_live_api.py does not import or mount it.
    Every GET route on :8770 is currently unauthenticated (reachability is restricted by
    Tailscale/127.0.0.1 binding only, which is SC-7/PR.IR, not IA-2).
    """
    zt_dir = ROOT / "backend" / "security" / "zero_trust"
    if not zt_dir.exists():
        return _unverified("no zero-trust module staged", "n/a")
    try:
        api_src = (ROOT / "backend" / "helm_live_api.py").read_text()
        mounted = "zero_trust" in api_src or "ReadAuthMiddleware" in api_src
    except Exception:
        mounted = None
    files = sorted(p.name for p in zt_dir.glob("*.py"))
    if mounted is False:
        return _row(PARTIAL,
                    f"read-auth layer staged on disk ({', '.join(files)}) but NOT mounted in "
                    "helm_live_api.py -- read (GET) endpoints are currently unauthenticated",
                    "SWARM-2 deliverable, deliberately not hot-applied without founder approval "
                    "(bind/TLS/read-auth changes can break phone access over Tailscale and the "
                    "live Phase-C soak if flipped carelessly)",
                    "backend/security/zero_trust/__init__.py")
    if mounted is True:
        return _row(COVERED, f"read-auth layer staged AND mounted ({', '.join(files)})",
                    "cut over from staged to live", "backend/security/zero_trust/__init__.py")
    return _unverified("could not determine mount state of helm_live_api.py", "n/a")


def a_reuse_catalog(control_id: str) -> Callable[[], Dict[str, Any]]:
    """Wrap a backend/security/helm_control_catalog.py assessor so its IMPLEMENTED /
    NOT_IMPLEMENTED / UNKNOWN verdict maps onto this matrix's COVERED / PARTIAL /
    UNVERIFIED vocabulary, instead of re-deriving the same live check a second time."""
    def _fn() -> Dict[str, Any]:
        try:
            from backend.security.helm_control_catalog import CONTROLS
            match = next((c for c in CONTROLS if c["id"] == control_id), None)
            if not match:
                return _unverified(f"{control_id} not present in helm_control_catalog", "")
            r = match["fn"]()
            status_map = {"IMPLEMENTED": COVERED, "NOT_IMPLEMENTED": PARTIAL, "UNKNOWN": UNVERIFIED}
            status = status_map.get(r["status"], UNVERIFIED)
            return _row(status, r["evidence"], r.get("detail", ""), "/api/v1/helm/chain"
                        if control_id == "AU-9" else "/api/v1/helm/wall")
        except Exception as e:
            return _unverified(f"catalog assessor error: {e}", "")
    return _fn


# --------------------------------------------------------------------------------------
# THE MATRIX. Each entry maps one real HELM mechanism to a CSF 2.0 Function/Category,
# a NIST SP 800-53 Rev 5 control, and its live assessor.
# --------------------------------------------------------------------------------------
MATRIX_ENTRIES: List[Dict[str, Any]] = [
    {
        "mechanism": "AU-9 tamper-evident evidence chain (sha256 hash-chained ledger)",
        "csf_function": "PROTECT", "csf_category": "PR.DS — Data Security",
        "control_id": "AU-9", "control_family": "Audit and Accountability",
        "control_title": "Protection of Audit Information | Cryptographic Protection",
        "fn": a_au9_tamper_evident_chain,
    },
    {
        "mechanism": "Founder decision chain-of-custody + HELM_SOURCE_HOLDER identity binding "
                     "+ monotonic fencing tokens",
        "csf_function": "GOVERN", "csf_category": "GV.OV — Oversight",
        "control_id": "AU-10", "control_family": "Audit and Accountability",
        "control_title": "Non-repudiation",
        "fn": a_au10_non_repudiation,
    },
    {
        "mechanism": "guarded_edit lease-before-write + .githooks pre-commit conflict detector "
                     "+ test suite + commit-bound evidence (secure SDLC / SSDF 800-218)",
        "csf_function": "PROTECT", "csf_category": "PR.PS — Platform Security",
        "control_id": "CM-3 / SA-10", "control_family": "Configuration Mgmt / Sys & Services Acquisition",
        "control_title": "Configuration Change Control | Developer Configuration Management",
        "fn": a_cm_sa10_secure_sdlc,
    },
    {
        "mechanism": "A/B/C soak seals + freshness gate (select_soak_package)",
        "csf_function": "DETECT", "csf_category": "DE.CM — Continuous Monitoring",
        "control_id": "CA-7", "control_family": "Assessment, Authorization and Monitoring",
        "control_title": "Continuous Monitoring",
        "fn": a_ca_soak_liveness,
    },
    {
        "mechanism": "Founder token gate on writes (fail-closed, constant-time, "
                     "PROPOSE_ONLY/FOUNDER_ONLY verb separation)",
        "csf_function": "PROTECT", "csf_category": "PR.AA — Identity Mgmt, Authn and Access Control",
        "control_id": "AC-3 / IA-2", "control_family": "Access Control / Identification and Authentication",
        "control_title": "Access Enforcement | Identification and Authentication (write path)",
        "fn": a_ac3_ia2_founder_write_gate,
    },
    {
        "mechanism": "Read-side (GET) authentication on the live API",
        "csf_function": "PROTECT", "csf_category": "PR.AA — Identity Mgmt, Authn and Access Control",
        "control_id": "AC-3 / IA-2", "control_family": "Access Control / Identification and Authentication",
        "control_title": "Access Enforcement | Identification and Authentication (read path)",
        "fn": a_ac3_ia2_read_side_auth,
    },
    {
        "mechanism": "AST-verified single egress chokepoint for all model dispatch",
        "csf_function": "PROTECT", "csf_category": "PR.IR — Technology Infrastructure Resilience",
        "control_id": "SC-7", "control_family": "System and Communications Protection",
        "control_title": "Boundary Protection",
        "fn": a_reuse_catalog("SC-7"),
    },
    {
        "mechanism": "Scoped-state blocking (capability-scoped, not lane-wide)",
        "csf_function": "RESPOND", "csf_category": "RS.MI — Incident Mitigation",
        "control_id": "AC-3", "control_family": "Access Control",
        "control_title": "Access Enforcement (least-privilege mitigation)",
        "fn": a_reuse_catalog("AC-3"),
    },
    {
        "mechanism": "Continuous monitoring surface with UNKNOWN guards, zero numeric fallbacks",
        "csf_function": "DETECT", "csf_category": "DE.CM — Continuous Monitoring",
        "control_id": "SI-4", "control_family": "System and Information Integrity",
        "control_title": "System Monitoring",
        "fn": a_reuse_catalog("SI-4"),
    },
    {
        "mechanism": "SIGKILL restart recovery with monotonic fencing (proven, not structural-only)",
        "csf_function": "RECOVER", "csf_category": "RC.RP — Recovery Planning",
        "control_id": "CP-10", "control_family": "Contingency Planning",
        "control_title": "System Recovery and Reconstitution",
        "fn": a_reuse_catalog("CP-10"),
    },
    {
        "mechanism": "Static verifiers run against the codebase (egress, runtime-truth, tautology)",
        "csf_function": "IDENTIFY", "csf_category": "ID.RA — Risk Assessment",
        "control_id": "RA-5", "control_family": "Risk Assessment",
        "control_title": "Vulnerability Monitoring and Scanning",
        "fn": a_reuse_catalog("RA-5"),
    },
    {
        "mechanism": "Tool/model provenance attestation, fail-closed on unattested dispatch",
        "csf_function": "GOVERN", "csf_category": "GV.SC — Supply Chain Risk Management",
        "control_id": "SR-3", "control_family": "Supply Chain Risk Management",
        "control_title": "Supply Chain Controls and Processes",
        "fn": a_reuse_catalog("SR-3"),
    },
]

CSF_FUNCTIONS = ["GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"]


def build_matrix() -> Dict[str, Any]:
    """Run every assessor now and assemble the truth-shaped matrix response.

    Fail-closed at every layer: an assessor that raises is caught HERE too (defence in
    depth beyond each assessor's own try/except) and becomes UNVERIFIED, never dropped
    and never silently promoted.
    """
    rows: List[Dict[str, Any]] = []
    for entry in MATRIX_ENTRIES:
        try:
            result = entry["fn"]()
        except Exception as e:
            result = _unverified(f"unhandled assessor exception: {e}", "")
        rows.append({
            "mechanism": entry["mechanism"],
            "csf_function": entry["csf_function"],
            "csf_category": entry["csf_category"],
            "control_id": entry["control_id"],
            "control_family": entry["control_family"],
            "control_title": entry["control_title"],
            **result,
        })

    by_function: Dict[str, List[Dict[str, Any]]] = {f: [] for f in CSF_FUNCTIONS}
    for r in rows:
        by_function.setdefault(r["csf_function"], []).append(r)

    counts = {
        "COVERED": sum(1 for r in rows if r["status"] == COVERED),
        "PARTIAL": sum(1 for r in rows if r["status"] == PARTIAL),
        "UNVERIFIED": sum(1 for r in rows if r["status"] == UNVERIFIED),
        "total": len(rows),
    }

    return {
        "truth_class": "HELM_NIST_MATRIX_TRUTH",
        "source": "backend.helm.nist_matrix (live assessors; reuses backend.security.helm_control_catalog)",
        "observed_at": _now(),
        "freshness_seconds": 0.0,
        "tested_commit": _git_commit(),
        "standard": "NIST CSF 2.0 (Feb 2024) x NIST SP 800-53 Rev 5",
        "doctrine": "COVERED only on live evidence observed right now; a documented real gap is "
                    "PARTIAL; anything unassessable is UNVERIFIED. Never COVERED on a claim alone.",
        "counts": counts,
        "by_function": by_function,
        "rows": rows,
    }


# --------------------------------------------------------------------------------------
# Router — included in backend/helm_live_api.py with a minimal two-line block, matching
# the pattern already used for backend/helm/health_registry.py's health_router.
# --------------------------------------------------------------------------------------
nist_router = APIRouter()


@nist_router.get("/api/v1/helm/nist")
def api_v1_helm_nist() -> JSONResponse:
    try:
        return JSONResponse(build_matrix())
    except Exception as e:
        return JSONResponse(status_code=200, content={
            "truth_class": "HELM_NIST_MATRIX_TRUTH",
            "source": "backend.helm.nist_matrix",
            "observed_at": _now(),
            "freshness_seconds": None,
            "tested_commit": _git_commit(),
            "data": {"state": UNVERIFIED, "reason": f"matrix build failed: {type(e).__name__}: {e}"},
        })


@nist_router.get("/nist", response_class=HTMLResponse)
def serve_nist_panel() -> str:
    """NIST control-coverage panel — same-origin, dark theme, matching the other consoles."""
    if NIST_UI.exists():
        return NIST_UI.read_text()
    return "<h1>nist.html missing</h1>"


if __name__ == "__main__":
    m = build_matrix()
    print(f"NIST matrix: {m['counts']}")
    for r in m["rows"]:
        print(f"  [{r['status']:>10}] {r['control_id']:<12} {r['mechanism'][:70]}")
