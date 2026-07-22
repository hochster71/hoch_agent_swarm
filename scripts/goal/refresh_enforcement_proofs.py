#!/usr/bin/env python3
"""Enforcement-proof evidence refresher — commit-bound artifacts for the GOV/ES
requirements whose evidence previously pointed at production *source files*.

Defect fixed (2026-07-22, Builder: Claude, founder-directed critical-path work):
  REQ-GOV-002, REQ-GOV-003 and REQ-ES-002 used a production .py file as
  evidence_path, so each went EVIDENCE_STALE whenever its source was simply
  unchanged for >168h — even while its validator suite passed. Evidence
  freshness must mean "the proofs were re-demonstrated recently", not "the
  source was edited recently".

  For each requirement below, this script re-runs the REAL validator suite
  and, ONLY on a genuinely passing run, writes:
    1. coordination/council/live_proof_packages/<REQ>-<UTC>/test_results.json
       (immutable timestamped package — existing H1B closure convention)
    2. a stable per-requirement pointer under coordination/council/
       (the requirement's evidence_path target)

  v2 binding (founder verification items, 2026-07-22): each record is
  cryptographically bound to the git commit + dirty flag, the validator suite
  digest, the production-code digests, the goal-requirements CONFIG digest,
  the execution environment, and the timestamp. If the validator or config
  changes, scripts/goal/verify_enforcement_proofs.py flags the old proof
  INVALID — a stale-bound proof never satisfies the requirement.

  NO-FAKE-GREEN: these artifacts alone cannot make a requirement pass. The
  goal engine still executes each validator itself on every recompute; the
  artifact carries only the freshness/evidence half, and it is written
  exclusively by a passing run. A failing suite leaves the stable pointer
  untouched, so the requirement ages out and fails closed. There is exactly
  one write site for the stable pointer, inside the passing branch.

Run:  .venv/bin/python scripts/goal/refresh_enforcement_proofs.py [REQ-ID ...]
      (no args = refresh all three)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "coordination" / "council" / "live_proof_packages"
CONFIG_PATH = "config/goal_requirements.json"
SCHEMA = "ENFORCEMENT_PROOF_v2"

REQUIREMENTS = {
    "REQ-GOV-002": {
        "statement": ("Founder authorization is fully bound (id, package, digests, "
                      "providers, models, caps, expiry) and atomically consumed "
                      "exactly once; replay is impossible."),
        "suite": "tests/test_h1b_authorization_enforcement.py",
        "extra_args": [],
        "production_evidence": ["scripts/council/h1_authorization.py"],
        "stable_pointer": "coordination/council/h1b_enforcement_proof.json",
        "min_passed": 24,  # acceptance: "24 enforcement proofs pass against production code"
    },
    "REQ-GOV-003": {
        "statement": ("Mock or dry-run evidence can never produce frontier quorum, "
                      "promotion, or safe-to-execute."),
        "suite": "tests/test_h1b_authorization_enforcement.py",
        "extra_args": ["-k", "quorum or mock or dry_run or advisory or partial"],
        "production_evidence": ["scripts/council/aggregate.py"],
        "stable_pointer": "coordination/council/h1b_quorum_proof.json",
        "min_passed": 1,
    },
    "REQ-ES-002": {
        "statement": "The dispatch loop is the only spawn point for model CLIs.",
        "suite": "tests/test_h1d_dispatch.py",
        "extra_args": [],
        "production_evidence": ["scripts/council/dispatch.py"],
        "stable_pointer": "coordination/council/h1d_dispatch_proof.json",
        "min_passed": 1,
    },
}


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _run_validator(spec: dict) -> subprocess.CompletedProcess:
    """The ONLY execution path: the real pytest entry point on the real suite.
    Isolated here so tests can prove no alternate path fabricates a PASS."""
    cmd = [sys.executable, "-m", "pytest", spec["suite"], "-q", *spec["extra_args"]]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)


def refresh(req_id: str) -> bool:
    spec = REQUIREMENTS[req_id]
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    bound_files = [spec["suite"], *spec["production_evidence"], CONFIG_PATH]
    for rel in bound_files:
        if not (ROOT / rel).exists():
            print(f"[{req_id}] FAIL-CLOSED: {rel} missing; nothing written.")
            return False

    run = _run_validator(spec)
    out = run.stdout or ""
    tail = "\n".join(out.strip().splitlines()[-3:])
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", out)) else 0

    ok = (run.returncode == 0 and failed == 0 and errors == 0
          and passed >= spec["min_passed"])
    if not ok:
        print(f"[{req_id}] FAIL-CLOSED: suite did not pass "
              f"(rc={run.returncode}, passed={passed}, failed={failed}, "
              f"errors={errors}). Stable evidence pointer NOT updated.\n{tail}")
        return False

    record = {
        "schema": SCHEMA,
        "requirement": req_id,
        "statement": spec["statement"],
        "command": " ".join(["python", "-m", "pytest", spec["suite"], "-q",
                             *spec["extra_args"]]),
        "result": {"passed": passed, "failed": failed, "errors": errors,
                   "returncode": run.returncode, "summary_tail": tail},
        "required_min_passes": spec["min_passed"],
        "executed_at_utc": now.isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "validator_digest": _sha256(ROOT / spec["suite"]),
        "config_digest": _sha256(ROOT / CONFIG_PATH),
        "digests": {rel: _sha256(ROOT / rel) for rel in bound_files},
        "evidence_manifest": bound_files,
        "runner": {"python": sys.version.split()[0], "platform": sys.platform,
                   "interpreter": sys.executable},
        "written_by": "scripts/goal/refresh_enforcement_proofs.py",
        "doctrine": ("no_fake_green: goal engine still re-runs the validator itself; "
                     "this artifact only evidences a genuine passing run and is never "
                     "written on failure; verify_enforcement_proofs.py invalidates it "
                     "on validator/config drift"),
    }

    pkg = PACKAGE_DIR / f"{req_id}-{stamp}"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "test_results.json").write_text(json.dumps(record, indent=2) + "\n",
                                           encoding="utf-8")
    pointer = ROOT / spec["stable_pointer"]
    pointer.write_text(json.dumps(
        {**record, "immutable_package": str(pkg.relative_to(ROOT))}, indent=2) + "\n",
        encoding="utf-8")
    print(f"[{req_id}] OK: {passed} proofs passed; package {pkg.relative_to(ROOT)}; "
          f"stable evidence refreshed at {spec['stable_pointer']}.")
    return True


def main() -> int:
    targets = sys.argv[1:] or list(REQUIREMENTS)
    unknown = [t for t in targets if t not in REQUIREMENTS]
    if unknown:
        print(f"FAIL-CLOSED: unknown requirement id(s) {unknown}; "
              f"known: {list(REQUIREMENTS)}")
        return 2
    results = {t: refresh(t) for t in targets}
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
