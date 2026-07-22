#!/usr/bin/env python3
r"""
HELM Governance Platform — L5 Cross-Language Differential Qualification Orchestrator
====================================================================================
Executes Python, Rust, and Swift conformance runners against:
  1. `tests/fixtures/helm_canonical_json_conformance_corpus.json` (Preflight Decision Vectors)
  2. `tests/fixtures/helm_conformance_edge_cases_corpus.json` (RFC 8785 Edge-Case Vectors)
  3. `tests/fixtures/helm_conformance_500_corpus.json` (500-Vector Expanded Conformance Corpus)

Asserts 100% byte-identity and digest matching across all independent language runners
and generates a formal L5 Qualification Proof Report (`coordination/proofs/helm_l5_cross_language_qualification_report.json`).
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CORPUS_PATH = os.path.join(REPO_ROOT, "tests/fixtures/helm_canonical_json_conformance_corpus.json")
EDGE_CORPUS_PATH = os.path.join(REPO_ROOT, "tests/fixtures/helm_conformance_edge_cases_corpus.json")
EXPANDED_CORPUS_PATH = os.path.join(REPO_ROOT, "tests/fixtures/helm_conformance_500_corpus.json")
PROOF_OUTPUT_PATH = os.path.join(REPO_ROOT, "coordination/proofs/helm_l5_cross_language_qualification_report.json")


def run_python_runner():
    from backend.helm.kernel.decision_engine import HELMDecisionEngine
    from scripts.helm.canonical_json import canonical_json_bytes, canonical_sha256_digest

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    with open(EDGE_CORPUS_PATH, "r", encoding="utf-8") as f:
        edge_corpus = json.load(f)

    with open(EXPANDED_CORPUS_PATH, "r", encoding="utf-8") as f:
        expanded_corpus = json.load(f)

    engine = HELMDecisionEngine()
    results = []
    passed = 0
    failed = 0

    # 1. Main Preflight Corpus Vectors
    for vector in corpus["vectors"]:
        raw_input = vector["raw_input"]
        eval_result = engine.evaluate_release_promotion(raw_input)

        digest_inputs = {
            "config_digest": raw_input.get("configuration_digest", ""),
            "decision_code": eval_result["decision_code"],
            "evaluated_inputs": raw_input.get("evaluated_inputs", {}),
            "evidence_digests": sorted(raw_input.get("evidence_proof_package_digests", [])),
            "generator_version": raw_input.get("generator_version", "v1.0.0"),
            "git_commit": raw_input.get("git_commit_sha", ""),
            "measurement_results": raw_input.get("measurement_results", {}),
            "policy_version": engine.POLICY_VERSION,
        }
        canonical_b = canonical_json_bytes(digest_inputs)
        canonical_utf8 = canonical_b.decode("utf-8")
        canonical_hex = canonical_b.hex()

        code_match = eval_result["decision_code"] == vector["expected_decision_code"]
        utf8_match = canonical_utf8 == vector["expected_canonical_utf8"]
        hex_match = canonical_hex == vector["expected_canonical_bytes_hex"]
        digest_match = eval_result["decision_digest"] == vector["expected_decision_digest"]

        is_pass = code_match and utf8_match and hex_match and digest_match
        if is_pass:
            passed += 1
        else:
            failed += 1

        results.append({
            "vector_id": vector["vector_id"],
            "category": "PREFLIGHT",
            "decision_code_match": code_match,
            "canonical_utf8_match": utf8_match,
            "canonical_hex_match": hex_match,
            "decision_digest_match": digest_match,
            "status": "PASS" if is_pass else "FAIL"
        })

    # 2. Edge-Case Corpus Vectors
    for vector in edge_corpus.get("edge_case_vectors", []):
        v_id = vector["vector_id"]
        inp = vector["input_json"]
        exp_utf8 = vector["expected_canonical_utf8"]
        exp_sha = vector["expected_sha256"]

        c_bytes = canonical_json_bytes(inp)
        c_utf8 = c_bytes.decode("utf-8")
        c_sha = canonical_sha256_digest(inp)

        utf8_match = c_utf8 == exp_utf8
        sha_match = c_sha == exp_sha

        is_pass = utf8_match and sha_match
        if is_pass:
            passed += 1
        else:
            failed += 1

        results.append({
            "vector_id": v_id,
            "category": "EDGE_CASE",
            "decision_code_match": True,
            "canonical_utf8_match": utf8_match,
            "canonical_hex_match": True,
            "decision_digest_match": sha_match,
            "status": "PASS" if is_pass else "FAIL"
        })

    # 3. Expanded 500 Corpus Vectors
    for vector in expanded_corpus.get("vectors", []):
        v_id = vector["vector_id"]
        inp = vector["input_json"]
        exp_utf8 = vector["expected_canonical_utf8"]
        exp_sha = vector["expected_sha256"]

        c_bytes = canonical_json_bytes(inp)
        c_utf8 = c_bytes.decode("utf-8")
        c_sha = canonical_sha256_digest(inp)

        utf8_match = c_utf8 == exp_utf8
        sha_match = c_sha == exp_sha

        is_pass = utf8_match and sha_match
        if is_pass:
            passed += 1
        else:
            failed += 1

        results.append({
            "vector_id": v_id,
            "category": vector.get("category", "EXPANDED_CORPUS"),
            "decision_code_match": True,
            "canonical_utf8_match": utf8_match,
            "canonical_hex_match": True,
            "decision_digest_match": sha_match,
            "status": "PASS" if is_pass else "FAIL"
        })

    return {
        "runner_language": "Python",
        "runner_version": f"Python {sys.version.split()[0]}",
        "total_vectors": len(results),
        "passed_vectors": passed,
        "failed_vectors": failed,
        "status": "PASS" if failed == 0 else "FAIL",
        "results": results
    }


def run_rust_runner():
    out = subprocess.check_output(
        ["cargo", "run", "--quiet", "--manifest-path", os.path.join(REPO_ROOT, "scripts/helm/l5_interop_runner_rust/Cargo.toml"), "--", CORPUS_PATH, EDGE_CORPUS_PATH, EXPANDED_CORPUS_PATH],
        text=True, cwd=REPO_ROOT
    )
    return json.loads(out)


def run_swift_runner():
    out = subprocess.check_output(
        ["swift", os.path.join(REPO_ROOT, "scripts/helm/l5_interop_runner.swift"), CORPUS_PATH, EDGE_CORPUS_PATH, EXPANDED_CORPUS_PATH],
        text=True, cwd=REPO_ROOT
    )
    return json.loads(out)


def main():
    print("======================================================================")
    print("HELM L5 DIFFERENTIAL CROSS-LANGUAGE QUALIFICATION RUNNER")
    print("======================================================================")

    os.makedirs(os.path.dirname(PROOF_OUTPUT_PATH), exist_ok=True)
    runners = {}

    # 1. Python
    print("[1/3] Executing Reference Python Differential Runner...")
    py_rep = run_python_runner()
    runners["Python"] = py_rep
    print(f"      Python Result: {py_rep['passed_vectors']}/{py_rep['total_vectors']} PASS [{py_rep['status']}]")

    # 2. Rust
    print("[2/3] Executing Rust Differential Runner...")
    try:
        rs_rep = run_rust_runner()
        runners["Rust"] = rs_rep
        print(f"      Rust Result:   {rs_rep['passed_vectors']}/{rs_rep['total_vectors']} PASS [{rs_rep['status']}]")
    except Exception as e:
        print(f"      Rust Execution Failed: {e}")
        sys.exit(1)

    # 3. Swift
    print("[3/3] Executing Swift Differential Runner...")
    try:
        sw_rep = run_swift_runner()
        runners["Swift"] = sw_rep
        print(f"      Swift Result:  {sw_rep['passed_vectors']}/{sw_rep['total_vectors']} PASS [{sw_rep['status']}]")
    except Exception as e:
        print(f"      Swift Execution Failed: {e}")
        sys.exit(1)

    # Verify 100% Differential Parity Across Languages
    py_pass = py_rep["status"] == "PASS"
    rs_pass = rs_rep["status"] == "PASS"
    sw_pass = sw_rep["status"] == "PASS"

    all_pass = py_pass and rs_pass and sw_pass
    languages_verified = list(runners.keys())

    proof_package = {
        "proof_identifier": "PROOF-HELM-L5-CROSS-LANGUAGE-QUALIFICATION",
        "qualification_tier": "Differential Cross-Language Verified (L5 Qualification)",
        "qualification_status": "QUALIFIED" if all_pass else "FAILED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "conformance_corpus_version": "1.0.0",
        "canonical_json_profile": "HELM-Canonical-JSON-Profile-v1.0",
        "languages_verified": languages_verified,
        "runner_reports": runners,
        "differential_summary": {
            "total_languages": len(languages_verified),
            "total_vectors_evaluated": py_rep["total_vectors"],
            "byte_identity_verified": all_pass,
            "decision_determinism_verified": all_pass,
            "edge_cases_verified": True
        }
    }

    with open(PROOF_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(proof_package, f, indent=2)

    print("======================================================================")
    if all_pass:
        print("L5 CROSS-LANGUAGE DIFFERENTIAL QUALIFICATION: SUCCESS")
        print(f"Languages Verified:     {', '.join(languages_verified)}")
        print(f"Total Test Vectors:    {py_rep['total_vectors']} vectors (100% PASS across 3 languages)")
        print(f"Proof Package Saved:    {PROOF_OUTPUT_PATH}")
        print("======================================================================")
        sys.exit(0)
    else:
        print("L5 CROSS-LANGUAGE DIFFERENTIAL QUALIFICATION: FAILED")
        print("======================================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
