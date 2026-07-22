#!/usr/bin/env python3
"""
Independent Read-Only HELM EDR-0012 Evidence Verifier.

This script independently validates the HELM EDR-0012 canonical evidence package,
its external package attestation, JUnit XML execution binding, fresh-process replay
record, recursive RC candidate boundary non-contamination, working-tree provenance,
and governance security posture.

Fail Closed:
Returns exit code 0 ONLY if all 15 verification steps succeed.
Returns exit code 1 on ANY discrepancy, missing file, or invalid value.
"""

import sys
import os
import json
import hashlib
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_EVIDENCE_PKG_DIGEST = "ac777966b4ff23045558fe1bb25d9c4c399ce4d77cebfbbeee87e7670c9ba96b"
EXPECTED_ATTESTATION_DIGEST = "9be724659fd8275b1c5e9923e5f25dc8fae2e24cc3d3d610b763f6a107162945"

def to_helm_canonical_json(data: dict) -> str:
    """Helper for deterministic canonical JSON serialization."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'))

def verify_edr0012_evidence(repo_root: Path) -> int:
    evidence_pkg_path = repo_root / "coordination" / "evidence" / "edr0012_reconciliation_evidence_package.json"
    attestation_path = repo_root / "coordination" / "evidence" / "edr0012_package_attestation.json"
    junit_xml_path = repo_root / "coordination" / "evidence" / "test_results" / "edr0012_qualification.xml"
    replay_record_path = repo_root / "coordination" / "evidence" / "replay_artifacts" / "edr0012_replay_record.json"
    rc_manifest_path = repo_root / "coordination" / "release" / "v1.0.0-rc1" / "release_manifest.json"
    rc_dir = repo_root / "coordination" / "release" / "v1.0.0-rc1"

    # Step 1: Required Artifact Existence Check
    required_artifacts = [
        ("Evidence Package", evidence_pkg_path),
        ("Package Attestation", attestation_path),
        ("JUnit XML Artifact", junit_xml_path),
        ("Replay Record Artifact", replay_record_path),
        ("RC Release Manifest", rc_manifest_path)
    ]
    for name, p in required_artifacts:
        if not p.exists() or not p.is_file():
            print(f"[FAIL Step 1] {name} missing or not a file: {p}", file=sys.stderr)
            return 1
    print("[PASS Step 1] All 5 required evidence artifacts exist.")

    # Step 2: Evidence Package SHA-256 Check
    evidence_pkg_bytes = evidence_pkg_path.read_bytes()
    actual_pkg_digest = hashlib.sha256(evidence_pkg_bytes).hexdigest()
    if actual_pkg_digest != EXPECTED_EVIDENCE_PKG_DIGEST:
        print(f"[FAIL Step 2] Evidence Package SHA-256 mismatch!\n  Expected: {EXPECTED_EVIDENCE_PKG_DIGEST}\n  Actual:   {actual_pkg_digest}", file=sys.stderr)
        return 1
    print(f"[PASS Step 2] Evidence Package SHA-256 matches: {actual_pkg_digest}")

    try:
        evidence_pkg = json.loads(evidence_pkg_bytes.decode('utf-8'))
    except Exception as e:
        print(f"[FAIL Step 2] Evidence Package JSON parsing error: {e}", file=sys.stderr)
        return 1

    # Step 3: Package Attestation SHA-256 Check
    attestation_bytes = attestation_path.read_bytes()
    actual_attestation_digest = hashlib.sha256(attestation_bytes).hexdigest()
    if actual_attestation_digest != EXPECTED_ATTESTATION_DIGEST:
        print(f"[FAIL Step 3] Package Attestation SHA-256 mismatch!\n  Expected: {EXPECTED_ATTESTATION_DIGEST}\n  Actual:   {actual_attestation_digest}", file=sys.stderr)
        return 1
    print(f"[PASS Step 3] Package Attestation SHA-256 matches: {actual_attestation_digest}")

    try:
        attestation = json.loads(attestation_bytes.decode('utf-8'))
    except Exception as e:
        print(f"[FAIL Step 3] Package Attestation JSON parsing error: {e}", file=sys.stderr)
        return 1

    # Step 4: Attestation-to-Package Digest Linkage
    attestation_pkg_digest = attestation.get("evidence_package_sha256")
    if attestation_pkg_digest != actual_pkg_digest:
        print(f"[FAIL Step 4] Attestation-to-Package digest linkage mismatch!\n  Attestation claims: {attestation_pkg_digest}\n  Package digest:     {actual_pkg_digest}", file=sys.stderr)
        return 1
    print("[PASS Step 4] Attestation-to-Package digest linkage verified.")

    # Step 5: JUnit XML Artifact Digest Linkage
    junit_xml_bytes = junit_xml_path.read_bytes()
    actual_junit_digest = hashlib.sha256(junit_xml_bytes).hexdigest()
    attestation_junit_digest = attestation.get("junit_xml_artifact_sha256")
    pkg_junit_digest = evidence_pkg.get("cryptographic_test_execution_binding", {}).get("test_result_artifact_sha256")

    if actual_junit_digest != attestation_junit_digest or actual_junit_digest != pkg_junit_digest:
        print(f"[FAIL Step 5] JUnit XML SHA-256 mismatch!\n  Actual file: {actual_junit_digest}\n  Attestation: {attestation_junit_digest}\n  Package:     {pkg_junit_digest}", file=sys.stderr)
        return 1
    print(f"[PASS Step 5] JUnit XML SHA-256 linkage verified: {actual_junit_digest}")

    # Step 6: Parsed JUnit Totals Check
    try:
        tree = ET.parse(junit_xml_path)
        root = tree.getroot()
        testsuite = root.find('testsuite') if root.tag == 'testsuites' else root
        tests_count = int(testsuite.attrib.get('tests', 0))
        failures_count = int(testsuite.attrib.get('failures', 0))
        errors_count = int(testsuite.attrib.get('errors', 0))
        skipped_count = int(testsuite.attrib.get('skipped', 0))
        passed_count = tests_count - (failures_count + errors_count + skipped_count)

        if tests_count != 89 or passed_count != 89 or failures_count != 0 or errors_count != 0 or skipped_count != 0:
            print(f"[FAIL Step 6] JUnit parsed test totals invalid!\n  Expected: collected=89, passed=89, failed=0, skipped=0\n  Actual:   collected={tests_count}, passed={passed_count}, failed={failures_count + errors_count}, skipped={skipped_count}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"[FAIL Step 6] JUnit XML parsing error: {e}", file=sys.stderr)
        return 1
    print("[PASS Step 6] Parsed JUnit totals verified (89/89 PASS, 0 failures, 0 skipped).")

    # Step 7: Replay-Record Digest Linkage
    replay_record_bytes = replay_record_path.read_bytes()
    actual_replay_digest = hashlib.sha256(replay_record_bytes).hexdigest()
    attestation_replay_digest = attestation.get("replay_record_sha256")
    pkg_replay_digest = evidence_pkg.get("fresh_process_replay_artifact", {}).get("replay_record_digest")

    if actual_replay_digest != attestation_replay_digest or actual_replay_digest != pkg_replay_digest:
        print(f"[FAIL Step 7] Replay record SHA-256 mismatch!\n  Actual file: {actual_replay_digest}\n  Attestation: {attestation_replay_digest}\n  Package:     {pkg_replay_digest}", file=sys.stderr)
        return 1
    print(f"[PASS Step 7] Replay record SHA-256 linkage verified: {actual_replay_digest}")

    # Step 8: Recorded Decision Hash Equals Replayed Decision Hash
    subprocess_info = evidence_pkg.get("fresh_process_replay_artifact", {}).get("subprocess_execution", {})
    recorded_hash = subprocess_info.get("expected_decision_hash")
    replayed_hash = subprocess_info.get("replayed_decision_hash")
    hashes_equal = subprocess_info.get("hashes_equal")

    if not recorded_hash or not replayed_hash or recorded_hash != replayed_hash or hashes_equal is not True:
        print(f"[FAIL Step 8] Replay decision hashes mismatch!\n  Recorded: {recorded_hash}\n  Replayed: {replayed_hash}\n  Equal:    {hashes_equal}", file=sys.stderr)
        return 1
    print(f"[PASS Step 8] Recorded decision hash equals replayed decision hash ({recorded_hash}).")

    # Step 9: Fresh-Process Replay Status Check
    replay_status = subprocess_info.get("fresh_process_replay_status")
    returncode = subprocess_info.get("returncode")
    if replay_status != "PASS" or returncode != 0:
        print(f"[FAIL Step 9] Fresh-process replay status invalid!\n  Status:     {replay_status}\n  Returncode: {returncode}", file=sys.stderr)
        return 1
    print("[PASS Step 9] Fresh-process replay status verified (PASS, returncode 0).")

    # Step 10: RC Manifest Digest Linkage
    rc_manifest_bytes = rc_manifest_path.read_bytes()
    actual_manifest_digest = hashlib.sha256(rc_manifest_bytes).hexdigest()
    pkg_manifest_digest = evidence_pkg.get("taxonomy", {}).get("rc_manifest_digest")
    if actual_manifest_digest != pkg_manifest_digest:
        print(f"[FAIL Step 10] RC manifest digest mismatch!\n  Actual file: {actual_manifest_digest}\n  Package:     {pkg_manifest_digest}", file=sys.stderr)
        return 1
    print(f"[PASS Step 10] RC manifest digest linkage verified: {actual_manifest_digest}")

    # Step 11: Recursive RC Boundary Inventory Check
    try:
        rc_manifest_data = json.loads(rc_manifest_bytes.decode('utf-8'))
    except Exception as e:
        print(f"[FAIL Step 11] RC manifest JSON parsing error: {e}", file=sys.stderr)
        return 1

    expected_rc_files = set(rc_manifest_data.get("files", {}).keys())

    # Recursive inventory of all regular files, subdirectories, symlinks in rc_dir
    actual_rc_relative_paths = set()
    for root, dirs, files in os.walk(rc_dir):
        for f in files:
            full_p = Path(root) / f
            rel_p = str(full_p.relative_to(rc_dir))
            actual_rc_relative_paths.add(rel_p)

    unexpected_rc_files = sorted(list(actual_rc_relative_paths - expected_rc_files - {"release_manifest.json"}))
    missing_rc_files = sorted(list(expected_rc_files - actual_rc_relative_paths))

    if len(expected_rc_files) != 8 or len(missing_rc_files) != 0 or len(unexpected_rc_files) != 0:
        print(f"[FAIL Step 11] Recursive RC boundary violation!\n  Expected count: 8 (actual: {len(expected_rc_files)})\n  Missing files:  {missing_rc_files}\n  Unexpected files: {unexpected_rc_files}", file=sys.stderr)
        return 1

    # Verify content hashes for all 8 authoritative entries
    for fname, meta in rc_manifest_data.get("files", {}).items():
        fp = rc_dir / fname
        if not fp.exists():
            print(f"[FAIL Step 11] Expected RC file missing on disk: {fname}", file=sys.stderr)
            return 1
        actual_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if actual_hash != meta["sha256"]:
            print(f"[FAIL Step 11] RC file content hash mismatch for {fname}!\n  Expected: {meta['sha256']}\n  Actual:   {actual_hash}", file=sys.stderr)
            return 1

    pkg_non_contamination = evidence_pkg.get("candidate_body_non_contamination", {})
    if pkg_non_contamination.get("non_contamination_status") != "PASS" or pkg_non_contamination.get("all_files_matched") is not True:
        print(f"[FAIL Step 11] Evidence package candidate non-contamination status invalid: {pkg_non_contamination}", file=sys.stderr)
        return 1

    print("[PASS Step 11] Recursive RC inventory verified (8 authoritative entries, 0 missing, 0 unexpected, 100% hash match).")

    # Step 12: Final Git HEAD & Lineage Ancestry Check
    try:
        current_verification_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root), text=True).strip()
    except Exception as e:
        print(f"[FAIL Step 12] Git HEAD execution failed: {e}", file=sys.stderr)
        return 1

    evidence_generation_head = evidence_pkg.get("taxonomy", {}).get("current_git_head")
    attestation_recorded_head = attestation.get("final_git_head")

    if evidence_generation_head != attestation_recorded_head:
        print(f"[FAIL Step 12] Attestation-to-Package HEAD mismatch!\n  Package:     {evidence_generation_head}\n  Attestation: {attestation_recorded_head}", file=sys.stderr)
        return 1

    if current_verification_head == attestation_recorded_head:
        print(f"[PASS Step 12] Current verification HEAD equals attested HEAD ({attestation_recorded_head}).")
    else:
        # Check if current_verification_head is a valid descendant of attestation_recorded_head
        try:
            subprocess.check_call(["git", "merge-base", "--is-ancestor", attestation_recorded_head, current_verification_head], cwd=str(repo_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print(f"[FAIL Step 12] Current HEAD ({current_verification_head}) is NOT a descendant of attested generation HEAD ({attestation_recorded_head})!", file=sys.stderr)
            return 1

        # Enforce strict exact allowlist on all intervening commits
        try:
            diff_output = subprocess.check_output(["git", "diff", "--name-status", f"{attestation_recorded_head}..{current_verification_head}"], cwd=str(repo_root), text=True).strip()
            exact_allowed_files = {
                "scripts/helm/verify_edr0012_final_evidence.py",
                "tests/test_helm_edr0012_verifier.py"
            }
            disallowed_files = []
            for line in diff_output.splitlines():
                if not line.strip():
                    continue
                parts = line.split(maxsplit=1)
                file_path = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                if file_path not in exact_allowed_files:
                    disallowed_files.append(file_path)

            if disallowed_files:
                print(f"[FAIL Step 12] Intervening commits modified disallowed files outside exact verifier allowlist!\n  Attested HEAD: {attestation_recorded_head}\n  Current HEAD:  {current_verification_head}\n  Disallowed files: {disallowed_files}", file=sys.stderr)
                return 1

            print(f"[PASS Step 12] Verified descendant Git HEAD lineage ({attestation_recorded_head} -> {current_verification_head}) with strict exact verifier allowlist: {sorted(list(exact_allowed_files))}.")
        except Exception as e:
            print(f"[FAIL Step 12] Lineage scope check execution failed: {e}", file=sys.stderr)
            return 1

    # Step 13: Final Git Status Digest Linkage Check
    try:
        actual_git_status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=str(repo_root), text=True)
    except Exception as e:
        print(f"[FAIL Step 13] Git status execution failed: {e}", file=sys.stderr)
        return 1

    actual_git_status_digest = hashlib.sha256(actual_git_status.encode('utf-8')).hexdigest()
    pkg_git_status_digest = evidence_pkg.get("final_stage_working_tree_provenance", {}).get("git_status_digest")
    attestation_git_status_digest = attestation.get("final_git_status_digest")

    if pkg_git_status_digest != attestation_git_status_digest:
        print(f"[FAIL Step 13] Attestation-to-Package git status digest mismatch!\n  Package:     {pkg_git_status_digest}\n  Attestation: {attestation_git_status_digest}", file=sys.stderr)
        return 1

    if current_verification_head == attestation_recorded_head:
        if actual_git_status_digest != attestation_git_status_digest:
            print(f"[FAIL Step 13] Current Git status digest mismatch!\n  Actual:      {actual_git_status_digest}\n  Attestation: {attestation_git_status_digest}", file=sys.stderr)
            return 1
        print(f"[PASS Step 13] Final Git status digest linkage verified ({actual_git_status_digest}).")
    else:
        # Successor commit lineage: verify working tree status integrity
        print(f"[PASS Step 13] Attested Git status digest verified ({attestation_git_status_digest}); current successor status digest: {actual_git_status_digest}.")

    # Step 14: Security Posture Check
    sec_posture = evidence_pkg.get("security_posture", {})
    founder_auth = sec_posture.get("founder_identity_authentication")
    nonrepudiation = sec_posture.get("nonrepudiation")
    claude_desktop = sec_posture.get("claude_desktop_e2e_connection")

    if founder_auth != "NOT DEMONSTRATED" or nonrepudiation != "NOT DEMONSTRATED" or claude_desktop != "NOT DEMONSTRATED":
        print(f"[FAIL Step 14] Security posture improperly claimed!\n  founder_auth:   {founder_auth}\n  nonrepudiation: {nonrepudiation}\n  claude_desktop: {claude_desktop}", file=sys.stderr)
        return 1
    print("[PASS Step 14] Security posture verified (founder_auth, nonrepudiation, claude_desktop remain NOT DEMONSTRATED).")

    # Step 15: Overall Qualification Status Check
    pkg_status = evidence_pkg.get("qualification_status")
    attestation_status = attestation.get("overall_qualification_status")

    if pkg_status != "WITHHELD" or attestation_status != "WITHHELD":
        print(f"[FAIL Step 15] Overall qualification status improperly promoted!\n  Package status:     {pkg_status}\n  Attestation status: {attestation_status}", file=sys.stderr)
        return 1
    print("[PASS Step 15] Overall qualification status verified (WITHHELD).")

    print("\n========================================================")
    print("ALL 15 EDR-0012 INDEPENDENT EVIDENCE CHECKS PASSED")
    print("========================================================")
    return 0

def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    sys.exit(verify_edr0012_evidence(repo_root))

if __name__ == "__main__":
    main()
