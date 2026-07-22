#!/usr/bin/env python3
"""Independent verifier for the enforcement-proof evidence artifacts.

Founder verification items (2026-07-22): a proof must be cryptographically
bound to git commit, validator version, config digest, execution environment,
timestamp, and an evidence manifest — and a proof whose validator or config
has since CHANGED must no longer satisfy its requirement.

For each requirement this verifier checks, fail-closed (any miss = INVALID):
  B1  stable pointer exists, parses, schema is ENFORCEMENT_PROOF_v2,
      requirement id matches
  B2  binding fields all present (git_commit, validator_digest, config_digest,
      digests, evidence_manifest, executed_at_utc, runner, result)
  B3  validator digest matches the CURRENT suite file      (validator drift => INVALID)
  B4  config digest matches the CURRENT goal_requirements  (config drift    => INVALID)
  B5  every evidence-manifest digest matches its current file content
  B6  recorded result is a genuine pass (rc 0, 0 failed, >= min_passed)
  B7  proof age is within the requirement's freshness SLA
  B8  goal_requirements.json maps the requirement's evidence_path to this
      stable pointer (source files are traceability evidence, not freshness)
  B9  the immutable package exists and byte-matches the pointer record

Read-only: this script never writes or repairs anything.
Exit 0 only when every checked requirement is VALID.

Run:  .venv/bin/python scripts/goal/verify_enforcement_proofs.py [REQ-ID ...]
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = "config/goal_requirements.json"


def _load_specs():
    """Share the single source of truth with the refresher (no duplicate table)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import refresh_enforcement_proofs as rep
    return rep.REQUIREMENTS, rep.SCHEMA


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify(req_id: str, spec: dict, schema: str, config: dict) -> list[str]:
    """Return a list of failure strings; empty list == VALID."""
    fails: list[str] = []
    pointer = ROOT / spec["stable_pointer"]

    # B1 — pointer exists / parses / schema / id
    if not pointer.exists():
        return [f"B1 stable pointer missing: {spec['stable_pointer']}"]
    try:
        rec = json.loads(pointer.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"B1 pointer unparseable: {e}"]
    if rec.get("schema") != schema:
        fails.append(f"B1 schema {rec.get('schema')!r} != {schema!r}")
    if rec.get("requirement") != req_id:
        fails.append(f"B1 requirement {rec.get('requirement')!r} != {req_id!r}")

    # B2 — binding fields present
    required = ("git_commit", "validator_digest", "config_digest", "digests",
                "evidence_manifest", "executed_at_utc", "runner", "result",
                "immutable_package")
    missing = [k for k in required if not rec.get(k)]
    if missing:
        fails.append(f"B2 missing binding fields: {missing}")
        return fails  # nothing further is meaningful

    # B3 — validator drift invalidates
    suite = ROOT / spec["suite"]
    if not suite.exists():
        fails.append(f"B3 validator suite missing: {spec['suite']}")
    elif rec["validator_digest"] != _sha256(suite):
        fails.append("B3 VALIDATOR DRIFT: suite digest changed since proof; "
                     "old proof no longer satisfies the requirement")

    # B4 — config drift invalidates
    cfg = ROOT / CONFIG_PATH
    if rec["config_digest"] != _sha256(cfg):
        fails.append("B4 CONFIG DRIFT: goal_requirements.json changed since proof")

    # B5 — evidence manifest digests
    for rel, want in (rec.get("digests") or {}).items():
        p = ROOT / rel
        if not p.exists():
            fails.append(f"B5 manifest file missing: {rel}")
        elif _sha256(p) != want:
            fails.append(f"B5 digest mismatch (content changed since proof): {rel}")

    # B6 — genuine pass
    res = rec.get("result") or {}
    if not (res.get("returncode") == 0 and res.get("failed") == 0
            and res.get("passed", 0) >= spec["min_passed"]):
        fails.append(f"B6 recorded result is not a qualifying pass: {res}")

    # B7 — freshness SLA
    req_cfg = next((r for r in config.get("requirements", [])
                    if r.get("id") == req_id), None)
    sla = (req_cfg or {}).get("freshness_sla_hours")
    try:
        executed = datetime.datetime.fromisoformat(rec["executed_at_utc"])
        age_h = (datetime.datetime.now(datetime.timezone.utc) - executed
                 ).total_seconds() / 3600.0
        if sla is not None and age_h > float(sla):
            fails.append(f"B7 proof age {age_h:.1f}h exceeds SLA {sla}h")
    except Exception as e:
        fails.append(f"B7 unparseable executed_at_utc: {e}")

    # B8 — requirement mapping in config
    if req_cfg is None:
        fails.append(f"B8 {req_id} absent from {CONFIG_PATH}")
    elif req_cfg.get("evidence_path") != spec["stable_pointer"]:
        fails.append(f"B8 evidence_path {req_cfg.get('evidence_path')!r} does not "
                     f"reference the proof pointer {spec['stable_pointer']!r}")

    # B9 — immutable package byte-match
    pkg = ROOT / rec["immutable_package"] / "test_results.json"
    if not pkg.exists():
        fails.append(f"B9 immutable package missing: {rec['immutable_package']}")
    else:
        try:
            pkg_rec = json.loads(pkg.read_text(encoding="utf-8"))
            if pkg_rec != {k: v for k, v in rec.items() if k != "immutable_package"}:
                fails.append("B9 pointer record diverges from immutable package")
        except Exception as e:
            fails.append(f"B9 package unparseable: {e}")

    return fails


def main() -> int:
    specs, schema = _load_specs()
    config = json.loads((ROOT / CONFIG_PATH).read_text(encoding="utf-8"))
    targets = sys.argv[1:] or list(specs)
    unknown = [t for t in targets if t not in specs]
    if unknown:
        print(f"FAIL-CLOSED: unknown requirement id(s) {unknown}")
        return 2
    all_ok = True
    for req_id in targets:
        fails = verify(req_id, specs[req_id], schema, config)
        if fails:
            all_ok = False
            print(f"[{req_id}] INVALID")
            for f in fails:
                print(f"    - {f}")
        else:
            print(f"[{req_id}] VALID (bound to git, validator, config, "
                  f"environment, timestamp, manifest)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
