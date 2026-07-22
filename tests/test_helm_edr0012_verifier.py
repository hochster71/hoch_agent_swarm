import sys
import json
import hashlib
import tempfile
import shutil
import subprocess
import pytest
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from scripts.helm.verify_edr0012_final_evidence import verify_edr0012_evidence

@pytest.fixture
def temp_evidence_tree(tmp_path, monkeypatch):
    """Creates a complete valid mock evidence tree for negative testing."""
    real_evidence_dir = repo_root / "coordination" / "evidence"
    real_rc_dir = repo_root / "coordination" / "release" / "v1.0.0-rc1"

    mock_repo = tmp_path / "mock_repo"
    mock_evidence = mock_repo / "coordination" / "evidence"
    mock_rc = mock_repo / "coordination" / "release" / "v1.0.0-rc1"

    mock_evidence.mkdir(parents=True, exist_ok=True)
    (mock_evidence / "test_results").mkdir(parents=True, exist_ok=True)
    (mock_evidence / "replay_artifacts").mkdir(parents=True, exist_ok=True)
    mock_rc.mkdir(parents=True, exist_ok=True)

    # Initialize temporary git repository
    subprocess.check_call(["git", "init"], cwd=str(mock_repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "test@helm.local"], cwd=str(mock_repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.name", "Test User"], cwd=str(mock_repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Copy actual evidence artifacts
    shutil.copy(real_evidence_dir / "edr0012_reconciliation_evidence_package.json", mock_evidence / "edr0012_reconciliation_evidence_package.json")
    shutil.copy(real_evidence_dir / "edr0012_package_attestation.json", mock_evidence / "edr0012_package_attestation.json")
    shutil.copy(real_evidence_dir / "test_results" / "edr0012_qualification.xml", mock_evidence / "test_results" / "edr0012_qualification.xml")
    shutil.copy(real_evidence_dir / "replay_artifacts" / "edr0012_replay_record.json", mock_evidence / "replay_artifacts" / "edr0012_replay_record.json")

    # Copy actual RC files
    for item in real_rc_dir.iterdir():
        if item.is_file():
            shutil.copy(item, mock_rc / item.name)

    subprocess.check_call(["git", "add", "."], cwd=str(mock_repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "initial", "--allow-empty"], cwd=str(mock_repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Overwrite git head in attestation and package to match this temp repo HEAD
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(mock_repo), text=True).strip()
    git_status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=str(mock_repo), text=True)
    git_status_digest = hashlib.sha256(git_status.encode("utf-8")).hexdigest()

    pkg_file = mock_evidence / "edr0012_reconciliation_evidence_package.json"
    pkg_data = json.loads(pkg_file.read_text())
    pkg_data["taxonomy"]["current_git_head"] = git_head
    pkg_data["final_stage_working_tree_provenance"]["git_status_digest"] = git_status_digest
    pkg_bytes = json.dumps(pkg_data, sort_keys=True, separators=(',', ':')).encode()
    pkg_file.write_bytes(pkg_bytes)

    att_file = mock_evidence / "edr0012_package_attestation.json"
    att_data = json.loads(att_file.read_text())
    att_data["final_git_head"] = git_head
    att_data["final_git_status_digest"] = git_status_digest
    att_data["evidence_package_sha256"] = hashlib.sha256(pkg_bytes).hexdigest()
    att_bytes = json.dumps(att_data, sort_keys=True, separators=(',', ':')).encode()
    att_file.write_bytes(att_bytes)

    monkeypatch.setattr("scripts.helm.verify_edr0012_final_evidence.EXPECTED_EVIDENCE_PKG_DIGEST", hashlib.sha256(pkg_bytes).hexdigest())
    monkeypatch.setattr("scripts.helm.verify_edr0012_final_evidence.EXPECTED_ATTESTATION_DIGEST", hashlib.sha256(att_bytes).hexdigest())

    return mock_repo

def test_verifier_negative_case1_pkg_digest_mismatch(temp_evidence_tree, monkeypatch):
    """1. Evidence package digest mismatch fails closed."""
    pkg_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_reconciliation_evidence_package.json"
    pkg_file.write_text('{"tampered": true}')
    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case2_attestation_digest_mismatch(temp_evidence_tree):
    """2. Attestation digest mismatch fails closed."""
    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_file.write_text('{"tampered": true}')
    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case3_attestation_wrong_pkg_linkage(temp_evidence_tree, monkeypatch):
    """3. Attestation points to wrong package digest fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_data = json.loads(att_file.read_text())
    att_data["evidence_package_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    att_bytes = json.dumps(att_data, sort_keys=True, separators=(',', ':')).encode()
    att_file.write_bytes(att_bytes)

    monkeypatch.setattr(verifier_mod, "EXPECTED_ATTESTATION_DIGEST", hashlib.sha256(att_bytes).hexdigest())
    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case4_junit_xml_digest_mismatch(temp_evidence_tree, monkeypatch):
    """4. JUnit XML digest mismatch fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    junit_file = temp_evidence_tree / "coordination" / "evidence" / "test_results" / "edr0012_qualification.xml"
    junit_file.write_text("<testsuites><testsuite tests='89' failures='0'/></testsuites>")
    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case5_junit_xml_failed_test(temp_evidence_tree, monkeypatch):
    """5. JUnit XML contains a failed test fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    junit_file = temp_evidence_tree / "coordination" / "evidence" / "test_results" / "edr0012_qualification.xml"
    tampered_xml = "<testsuites><testsuite tests='89' failures='1'/></testsuites>"
    junit_file.write_text(tampered_xml)
    tampered_xml_digest = hashlib.sha256(tampered_xml.encode()).hexdigest()

    # Tamper attestation & pkg to match xml digest so it reaches step 6
    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_data = json.loads(att_file.read_text())
    att_data["junit_xml_artifact_sha256"] = tampered_xml_digest
    att_bytes = json.dumps(att_data, sort_keys=True, separators=(',', ':')).encode()
    att_file.write_bytes(att_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_ATTESTATION_DIGEST", hashlib.sha256(att_bytes).hexdigest())

    pkg_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_reconciliation_evidence_package.json"
    pkg_data = json.loads(pkg_file.read_text())
    pkg_data["cryptographic_test_execution_binding"]["test_result_artifact_sha256"] = tampered_xml_digest
    pkg_bytes = json.dumps(pkg_data, sort_keys=True, separators=(',', ':')).encode()
    pkg_file.write_bytes(pkg_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_EVIDENCE_PKG_DIGEST", hashlib.sha256(pkg_bytes).hexdigest())

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case6_replay_hashes_diverge(temp_evidence_tree, monkeypatch):
    """6. Replay decision hashes diverge fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    pkg_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_reconciliation_evidence_package.json"
    pkg_data = json.loads(pkg_file.read_text())
    pkg_data["fresh_process_replay_artifact"]["subprocess_execution"]["hashes_equal"] = False
    pkg_data["fresh_process_replay_artifact"]["subprocess_execution"]["replayed_decision_hash"] = "divergent_hash"
    pkg_bytes = json.dumps(pkg_data, sort_keys=True, separators=(',', ':')).encode()
    pkg_file.write_bytes(pkg_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_EVIDENCE_PKG_DIGEST", hashlib.sha256(pkg_bytes).hexdigest())

    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_data = json.loads(att_file.read_text())
    att_data["evidence_package_sha256"] = hashlib.sha256(pkg_bytes).hexdigest()
    att_bytes = json.dumps(att_data, sort_keys=True, separators=(',', ':')).encode()
    att_file.write_bytes(att_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_ATTESTATION_DIGEST", hashlib.sha256(att_bytes).hexdigest())

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case7_rc_file_missing(temp_evidence_tree, monkeypatch):
    """7. RC candidate file missing fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    target_rc_file = temp_evidence_tree / "coordination" / "release" / "v1.0.0-rc1" / "version_info.json"
    target_rc_file.unlink()

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case8_unexpected_nested_rc_file(temp_evidence_tree, monkeypatch):
    """8. Unexpected nested RC file fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    nested_dir = temp_evidence_tree / "coordination" / "release" / "v1.0.0-rc1" / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)
    (nested_dir / "unauthorized_file.txt").write_text("unauthorized")

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case9_manifest_content_hash_mismatch(temp_evidence_tree, monkeypatch):
    """9. Manifest content hash mismatch fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    rc_file = temp_evidence_tree / "coordination" / "release" / "v1.0.0-rc1" / "version_info.json"
    rc_file.write_text('{"modified": true}')

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case10_qualification_status_promoted(temp_evidence_tree, monkeypatch):
    """10. Qualification status changed from WITHHELD fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    pkg_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_reconciliation_evidence_package.json"
    pkg_data = json.loads(pkg_file.read_text())
    pkg_data["qualification_status"] = "APPROVED"
    pkg_bytes = json.dumps(pkg_data, sort_keys=True, separators=(',', ':')).encode()
    pkg_file.write_bytes(pkg_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_EVIDENCE_PKG_DIGEST", hashlib.sha256(pkg_bytes).hexdigest())

    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_data = json.loads(att_file.read_text())
    att_data["evidence_package_sha256"] = hashlib.sha256(pkg_bytes).hexdigest()
    att_bytes = json.dumps(att_data, sort_keys=True, separators=(',', ':')).encode()
    att_file.write_bytes(att_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_ATTESTATION_DIGEST", hashlib.sha256(att_bytes).hexdigest())

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case11_founder_auth_falsely_claimed(temp_evidence_tree, monkeypatch):
    """11. Founder authentication falsely changed to DEMONSTRATED fails closed."""
    import scripts.helm.verify_edr0012_final_evidence as verifier_mod
    pkg_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_reconciliation_evidence_package.json"
    pkg_data = json.loads(pkg_file.read_text())
    pkg_data["security_posture"]["founder_identity_authentication"] = "DEMONSTRATED"
    pkg_bytes = json.dumps(pkg_data, sort_keys=True, separators=(',', ':')).encode()
    pkg_file.write_bytes(pkg_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_EVIDENCE_PKG_DIGEST", hashlib.sha256(pkg_bytes).hexdigest())

    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_data = json.loads(att_file.read_text())
    att_data["evidence_package_sha256"] = hashlib.sha256(pkg_bytes).hexdigest()
    att_bytes = json.dumps(att_data, sort_keys=True, separators=(',', ':')).encode()
    att_file.write_bytes(att_bytes)
    monkeypatch.setattr(verifier_mod, "EXPECTED_ATTESTATION_DIGEST", hashlib.sha256(att_bytes).hexdigest())

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1

def test_verifier_negative_case12_missing_artifact_path(temp_evidence_tree):
    """12. Required artifact path missing or malformed fails closed."""
    att_file = temp_evidence_tree / "coordination" / "evidence" / "edr0012_package_attestation.json"
    att_file.unlink()

    ret = verify_edr0012_evidence(temp_evidence_tree)
    assert ret == 1
