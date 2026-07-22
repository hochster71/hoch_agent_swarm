#!/usr/bin/env python3
r"""
HELM Governance Platform — Native Java TLC Model Checker Runner (Sprint 11)
========================================================================
Executes native TLA+ TLC model checker (tlc2.TLC) via Java runtime on HELMLedger.tla and HELMDecisionStateMachine.tla.
Fails closed with explicit diagnostic logs if Java or tla2tools.jar is unavailable or if invariant violations occur.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROOFS_DIR = REPO_ROOT / "coordination" / "proofs"
TLA_DIR = REPO_ROOT / "docs" / "governance" / "formal"
TOOLS_DIR = REPO_ROOT / "tools"


def get_git_commit_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN_COMMIT_SHA"


def check_java_available() -> tuple[bool, str]:
    java_bin = shutil.which("java")
    if not java_bin:
        return False, "Java binary not found on PATH"
    try:
        res = subprocess.run([java_bin, "-version"], capture_output=True, text=True)
        version_str = res.stderr if res.stderr else res.stdout
        return True, version_str.splitlines()[0] if version_str else "Java Available"
    except Exception as e:
        return False, f"Java check failed: {str(e)}"


def run_tlc_model(tla_filename: str, cfg_filename: str) -> dict:
    tla_path = TLA_DIR / tla_filename
    cfg_path = TLA_DIR / cfg_filename

    tla_b = tla_path.read_bytes()
    cfg_b = cfg_path.read_bytes()

    has_java, java_ver = check_java_available()
    tla2tools_jar = TOOLS_DIR / "tla2tools.jar"

    if not has_java:
        return {
            "model": tla_filename.replace(".tla", ""),
            "tlc_execution_status": "FAIL_JAVA_UNAVAILABLE",
            "error_detail": f"Native TLC execution failed: {java_ver}",
            "source_commit": get_git_commit_sha(),
            "model_sha256": hashlib.sha256(tla_b).hexdigest(),
            "cfg_sha256": hashlib.sha256(cfg_b).hexdigest(),
            "states_generated": 0,
            "distinct_states": 0,
            "maximum_depth": 0,
            "result": "FAIL_CLOSED_NO_JAVA",
            "executed_at_utc": datetime.now(timezone.utc).isoformat()
        }

    if not tla2tools_jar.exists():
        return {
            "model": tla_filename.replace(".tla", ""),
            "tlc_execution_status": "FAIL_TLA2TOOLS_JAR_MISSING",
            "error_detail": f"tla2tools.jar missing at {tla2tools_jar}",
            "source_commit": get_git_commit_sha(),
            "model_sha256": hashlib.sha256(tla_b).hexdigest(),
            "cfg_sha256": hashlib.sha256(cfg_b).hexdigest(),
            "states_generated": 0,
            "distinct_states": 0,
            "maximum_depth": 0,
            "result": "FAIL_CLOSED_NO_JAR",
            "executed_at_utc": datetime.now(timezone.utc).isoformat()
        }

    start_t = time.time()
    cmd = [
        "java",
        "-cp",
        str(tla2tools_jar),
        "tlc2.TLC",
        "-config",
        str(cfg_path),
        "-workers",
        "auto",
        str(tla_path)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        elapsed_sec = round(time.time() - start_t, 3)

        raw_out = res.stdout + "\n" + res.stderr
        raw_digest = hashlib.sha256(raw_out.encode("utf-8")).hexdigest()

        # Parse TLC Output
        success = res.returncode == 0 and "Model checking completed. No error has been found." in res.stdout

        states_gen = 0
        distinct_st = 0
        depth = 0

        for line in res.stdout.splitlines():
            if "states generated" in line:
                try:
                    parts = line.split(",")
                    states_gen = int(parts[0].split(":")[1].strip())
                    distinct_st = int(parts[1].split(":")[1].strip())
                except Exception:
                    pass
            if "depth" in line.lower():
                try:
                    depth = int(line.split(":")[-1].strip())
                except Exception:
                    pass

        return {
            "model": tla_filename.replace(".tla", ""),
            "tlc_execution_status": "NATIVE_TLC_PASS" if success else "NATIVE_TLC_FAIL",
            "java_version": java_ver,
            "source_commit": get_git_commit_sha(),
            "model_sha256": hashlib.sha256(tla_b).hexdigest(),
            "cfg_sha256": hashlib.sha256(cfg_b).hexdigest(),
            "raw_output_sha256": raw_digest,
            "exit_code": res.returncode,
            "states_generated": states_gen,
            "distinct_states": distinct_st,
            "maximum_depth": depth,
            "exploration_time_sec": elapsed_sec,
            "result": "PASS" if success else "FAIL",
            "executed_at_utc": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "model": tla_filename.replace(".tla", ""),
            "tlc_execution_status": "FAIL_EXECUTION_ERROR",
            "error_detail": str(e),
            "source_commit": get_git_commit_sha(),
            "model_sha256": hashlib.sha256(tla_b).hexdigest(),
            "cfg_sha256": hashlib.sha256(cfg_b).hexdigest(),
            "result": "FAIL",
            "executed_at_utc": datetime.now(timezone.utc).isoformat()
        }


def main():
    PROOFS_DIR.mkdir(parents=True, exist_ok=True)
    print("======================================================================")
    print("HELM NATIVE JAVA TLC MODEL CHECKER RUNNER")
    print("======================================================================")

    has_java, java_ver = check_java_available()
    print(f"Java Available: {has_java} [{java_ver}]")

    ledger_proof = run_tlc_model("HELMLedger.tla", "HELMLedger.cfg")
    with open(PROOFS_DIR / "helm_native_tlc_ledger_proof.json", "w", encoding="utf-8") as f:
        json.dump(ledger_proof, f, indent=2)
    print(f"HELMLedger Native TLC Result: {ledger_proof['tlc_execution_status']}")

    decision_proof = run_tlc_model("HELMDecisionStateMachine.tla", "HELMDecisionStateMachine.cfg")
    with open(PROOFS_DIR / "helm_native_tlc_decision_proof.json", "w", encoding="utf-8") as f:
        json.dump(decision_proof, f, indent=2)
    print(f"HELMDecisionStateMachine Native TLC Result: {decision_proof['tlc_execution_status']}")
    print("======================================================================")


if __name__ == "__main__":
    main()
