#!/usr/bin/env python3
"""Mechanical acceptance evaluation of a harvested full-suite proof artifact (v1).

Council directive (2026-07-20): the decisive comparison is SET EQUALITY of failed test
IDs against the expected WIP set — never merely a count. This evaluator takes the
harvest artifact (harvest_full_suite_proof.py output) and the pinned expected-residue
file, and emits the machine-evaluated acceptance fields. It computes; it does not
narrate. Two judgments are kept separate: (1) did the suite behave exactly as
predicted, and (2) can the result be bound to a promotable commit.

Usage: python3 scripts/goal/evaluate_full_suite_acceptance.py <harvest_artifact.json>
Exit:  0 = evaluation written (whatever the verdict — honesty over green)
       2 = inputs missing/invalid (fail-closed: no verdict)
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = ROOT / "coordination/evidence/sbom_cve_20260719/runtime/expected_full_suite_residue.json"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: evaluate_full_suite_acceptance.py <harvest_artifact.json>", file=sys.stderr)
        return 2
    art_path = Path(sys.argv[1])
    if not art_path.is_file() or not EXPECTED.is_file():
        print(f"FAIL-CLOSED: missing input ({art_path if not art_path.is_file() else EXPECTED})", file=sys.stderr)
        return 2
    import hashlib
    art = json.loads(art_path.read_text())
    expected_bytes = EXPECTED.read_bytes()
    expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()
    exp = json.loads(expected_bytes)
    # control 6: schema validation BEFORE trusting content - a correctly hashed malformed
    # baseline must still fail closed
    if exp.get("schema") != "HELM_EXPECTED_SUITE_RESIDUE_v1" or \
       not isinstance(exp.get("expected_wip_failed_ids"), list) or \
       not isinstance(exp.get("expected_skips", {}).get("expected_total_skipped"), int) or \
       not all(isinstance(i, str) and "::" in i for i in exp["expected_wip_failed_ids"]):
        print("FAIL-CLOSED: baseline schema invalid (id/types/test-id format)", file=sys.stderr)
        return 2
    # BD-F5 hardening: the baseline is shared mutable state on a multi-agent machine.
    # An empty expected set is NEVER a valid baseline for this campaign - it silently
    # converts "all WIP passed" into acceptance (fake-green-adjacent). Fail closed.
    if not exp.get("expected_wip_failed_ids"):
        # an empty expected set is valid ONLY under an explicit, recorded re-pin authorization
        # (BD-F5: silent emptying converts "all WIP passed" into acceptance). The authorization
        # block must name who, when, and the isolated evidence that justified the re-pin.
        auth = exp.get("re_pin_authorization") or {}
        if not (auth.get("authorized") is True and auth.get("authorized_by")
                and auth.get("authorized_at") and auth.get("supporting_evidence")
                and auth.get("prior_expected_failure_count") is not None
                and auth.get("new_expected_failure_count") == 0):
            print("FAIL-CLOSED: expected_wip_failed_ids is empty/missing WITHOUT a complete "
                  "re_pin_authorization block (authorized_by/authorized_at/evidence) - baseline "
                  "invalid or mutated (BD-F5); restore from provenance or record the re-pin",
                  file=sys.stderr)
            return 2
    if art.get("schema") != "HELM_FULL_SUITE_PROOF_v1":
        print("FAIL-CLOSED: artifact schema mismatch", file=sys.stderr)
        return 2

    res = art["result"]
    observed_failed = set(res.get("failed_test_ids") or [])
    expected_failed = set(exp["expected_wip_failed_ids"])
    error_modules = list(res.get("collection_error_modules") or [])

    collection_accepted = (not res.get("collection_interrupted")) and not error_modules
    unexpected_failures = sorted(observed_failed - expected_failed)
    missing_expected = sorted(expected_failed - observed_failed)
    failure_set_matches = observed_failed == expected_failed

    expected_skips = exp["expected_skips"]["expected_total_skipped"]
    observed_skips = res.get("skipped", 0)
    skip_count_matches = observed_skips == expected_skips
    # identity-level skip verification requires -rs in the pytest command; count-only otherwise
    skip_ids_verifiable = ("-rs" in art["execution"].get("pytest_command", "")
                           and res.get("skipped_entries") is not None)
    skip_set_verdict = None
    if skip_ids_verifiable:
        skipped_locs = {e["location"].strip() for e in res["skipped_entries"]}
        legacy = set(exp["expected_skips"]["legacy_lane_modules"])
        missing_legacy = sorted(m for m in legacy if not any(loc.startswith(m) for loc in skipped_locs))
        skip_set_verdict = {"legacy_modules_all_skipped": not missing_legacy,
                           "missing_legacy_skips": missing_legacy,
                           "observed_skip_locations": sorted(skipped_locs)}

    # council criterion (2026-07-20): the evaluator INDEPENDENTLY requires execution-control
    # evidence - the launcher's exit-4 gate is not the only line of defense. An artifact with
    # no execution_controls block, or with exclusive_lane_verified false, is INVALID
    # (environment not controlled), never merely failed.
    controls = art.get("execution_controls") or {}
    controls_verified = controls.get("exclusive_lane_verified") is True
    # council criterion: rc recorded independently of parsed summary; both must agree.
    # A nonzero rc in a CONTROLLED environment is a rejection ground, never an environment
    # invalidation - keep the two classification categories separate.
    rc = controls.get("pytest_return_code")
    rc_ok = (rc == 0) if rc is not None else None  # None = rc not recorded (pre-v2.1 artifact)
    accepted = (controls_verified and collection_accepted and failure_set_matches
                and skip_count_matches
                and (rc_ok is not False)
                and (skip_set_verdict is None or skip_set_verdict["legacy_modules_all_skipped"]))
    worktree_clean = art["candidate_identity"]["worktree_clean"]

    evaluation = {
        "schema": "HELM_FULL_SUITE_ACCEPTANCE_v1",
        "evaluated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "harvest_artifact": str(art_path),
        "harvest_log_sha256": art["execution"]["log_sha256"],
        "expected_residue_file": str(EXPECTED.relative_to(ROOT)),
        "expected_residue_sha256": expected_sha256,
        "collection_accepted": collection_accepted,
        "failure_set_matches_expected": failure_set_matches,
        "skip_count_matches_expected": skip_count_matches,
        "skip_set_matches_expected": (None if not skip_ids_verifiable
                                      else skip_set_verdict["legacy_modules_all_skipped"]),
        "skip_set_detail": skip_set_verdict,
        "skip_verification_basis": ("IDENTITY" if skip_ids_verifiable else
                                    "COUNT_ONLY — pytest command lacked -rs; clean-candidate qualification run must include it"),
        "unexpected_failure_ids": unexpected_failures,
        "missing_expected_failure_ids": missing_expected,
        "unexpected_error_modules": error_modules,
        "observed": {"failed": len(observed_failed), "skipped": observed_skips,
                     "passed": res.get("passed"), "collection_interrupted": res.get("collection_interrupted")},
        "execution_controls_verified": controls_verified,
        "pytest_return_code": rc,
        "pytest_return_code_ok": rc_ok,
        "execution_controls_violations": controls.get("violations", "NO_CONTROLS_BLOCK"),
        "acceptance_result": ("PASS_PRE_FREEZE" if accepted and not worktree_clean else
                              "PASS_CLEAN_CANDIDATE" if accepted and worktree_clean else
                              "INVALID_ENVIRONMENT_NOT_CONTROLLED" if not controls_verified else
                              "REJECTED"),
        "regression_evidence_accepted": accepted,
        "promotion_binding_eligible": worktree_clean and accepted,
        "qualification": ("CLEAN_CANDIDATE" if worktree_clean else "PRE_FREEZE_HEAD_PLUS_WORKTREE"),
        "divergence_note": (None if accepted else
                            "any unexpected failure reopens classification; any missing expected failure requires "
                            "investigation (collection drift / file changes during execution / environment divergence / "
                            "accidental exclusion) — per council rule, never celebrated"),
    }
    out = art_path.with_name(art_path.stem + "_acceptance.json")
    import os as _os, tempfile as _tf
    fd, tmp = _tf.mkstemp(dir=str(out.parent))
    with _os.fdopen(fd, "w") as f:
        json.dump(evaluation, f, indent=2); f.flush(); _os.fsync(f.fileno())
    _os.replace(tmp, str(out))
    print(json.dumps(evaluation, indent=2))
    print(f"\nevaluation -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
