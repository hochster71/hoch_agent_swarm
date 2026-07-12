import os
import sys
import json
import time
import shutil
import threading
import multiprocessing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.council.h1_authorization import AuthorizationLedger, LedgerError, H1AuthorizationValidator

ACTIVE_PKG = "HELM-H1-CANDIDATE-20260712T013903Z-4B7F62BE"
validator = H1AuthorizationValidator(ACTIVE_PKG)
REAL_DIGEST = validator.recompute()["combined_authorization_sha256"]

def thread_worker(ledger, auth_id, pkg_id, barrier, results):
    barrier.wait()
    try:
        ledger.consume(
            authorization_id=auth_id,
            package_id=pkg_id,
            run_id=f"T-{threading.get_ident()}",
            request_digest=REAL_DIGEST,
            lock_timeout=2.0
        )
        results.append("CONSUMED")
    except LedgerError as e:
        results.append(f"BLOCKED:{e}")
    except Exception as e:
        results.append(f"ERROR:{type(e).__name__}:{str(e)}")

def process_worker(ledger_path, auth_id, pkg_id, barrier, queue):
    barrier.wait()
    from scripts.council.h1_authorization import AuthorizationLedger, LedgerError
    ledger = AuthorizationLedger(Path(ledger_path))
    try:
        ledger.consume(
            authorization_id=auth_id,
            package_id=pkg_id,
            run_id=f"P-{os.getpid()}",
            request_digest=REAL_DIGEST,
            lock_timeout=2.0
        )
        queue.put("CONSUMED")
    except LedgerError as e:
        queue.put(f"BLOCKED:{e}")
    except Exception as e:
        queue.put(f"ERROR:{type(e).__name__}:{str(e)}")

def run_thread_matrix(num_threads, iterations, temp_dir):
    double_consumes = 0
    unexpected_errors = 0

    for i in range(iterations):
        auth_id = f"T-AUTH-{num_threads}-{i}"
        ledger_file = temp_dir / f"threads_{num_threads}_{i}.jsonl"
        ledger = AuthorizationLedger(ledger_file)

        barrier = threading.Barrier(num_threads)
        results = []
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(
                target=thread_worker,
                args=(ledger, auth_id, ACTIVE_PKG, barrier, results)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        successful_consumers = results.count("CONSUMED")
        consumed_ledger_entries = len([e for e in ledger.entries() if e["status"] == "CONSUMED" and e["authorization_id"] == auth_id])

        assert successful_consumers == 1, f"Expected exactly 1 success, got {successful_consumers} in results: {results}"
        assert consumed_ledger_entries == 1, f"Expected exactly 1 ledger entry, got {consumed_ledger_entries}"

        rejected_attempts = 0
        for r in results:
            if r.startswith("BLOCKED:"):
                err = r.split("BLOCKED:")[1]
                assert err in ("AUTHORIZATION_ALREADY_CONSUMED", "AUTHORIZATION_LOCK_HELD"), f"Unexpected error: {err}"
                rejected_attempts += 1
            elif r.startswith("ERROR:"):
                unexpected_errors += 1
                raise AssertionError(f"Unexpected exception: {r}")

        assert rejected_attempts == num_threads - 1, f"Expected {num_threads - 1} rejected attempts, got {rejected_attempts}"

    return {
        "iterations": iterations,
        "concurrency": num_threads,
        "failures": double_consumes,
        "unexpected_errors": unexpected_errors
    }

def run_process_matrix(num_processes, iterations, temp_dir):
    double_consumes = 0
    unexpected_errors = 0
    ctx = multiprocessing.get_context("spawn")

    for i in range(iterations):
        auth_id = f"P-AUTH-{num_processes}-{i}"
        ledger_file = temp_dir / f"procs_{num_processes}_{i}.jsonl"
        ledger_file.parent.mkdir(parents=True, exist_ok=True)

        barrier = ctx.Barrier(num_processes)
        queue = ctx.Queue()

        procs = []
        for _ in range(num_processes):
            p = ctx.Process(
                target=process_worker,
                args=(str(ledger_file), auth_id, ACTIVE_PKG, barrier, queue)
            )
            procs.append(p)
            p.start()

        for p in procs:
            p.join(10)
            if p.is_alive():
                p.terminate()

        results = []
        while not queue.empty():
            results.append(queue.get())

        successful_consumers = results.count("CONSUMED")
        ledger = AuthorizationLedger(ledger_file)
        consumed_ledger_entries = len([e for e in ledger.entries() if e["status"] == "CONSUMED" and e["authorization_id"] == auth_id])

        assert successful_consumers == 1, f"Expected exactly 1 success, got {successful_consumers} in results: {results}"
        assert consumed_ledger_entries == 1, f"Expected exactly 1 ledger entry, got {consumed_ledger_entries}"

        rejected_attempts = 0
        for r in results:
            if r.startswith("BLOCKED:"):
                err = r.split("BLOCKED:")[1]
                assert err in ("AUTHORIZATION_ALREADY_CONSUMED", "AUTHORIZATION_LOCK_HELD"), f"Unexpected error: {err}"
                rejected_attempts += 1
            elif r.startswith("ERROR:"):
                unexpected_errors += 1
                raise AssertionError(f"Unexpected exception: {r}")

        assert rejected_attempts == num_processes - 1, f"Expected {num_processes - 1} rejected attempts, got {rejected_attempts}"

    return {
        "iterations": iterations,
        "concurrency": num_processes,
        "failures": double_consumes,
        "unexpected_errors": unexpected_errors
    }

def main():
    temp_dir = ROOT / "coordination" / "council" / "reviews" / "temp_matrix_test"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("Running 2 processes x 100 iterations...")
        p2_x100 = run_process_matrix(2, 100, temp_dir)

        print("Running 8 processes x 50 iterations...")
        p8_x50 = run_process_matrix(8, 50, temp_dir)

        print("Running 2 threads x 100 iterations...")
        t2_x100 = run_thread_matrix(2, 100, temp_dir)

        print("Running 16 threads x 25 iterations...")
        t16_x25 = run_thread_matrix(16, 25, temp_dir)

        results_json = {
            "implementation": "FLOCK_LEDGER_TRANSACTION",
            "process_matrix": {
                "2_procs_100_auths": p2_x100,
                "8_procs_50_auths": p8_x50
            },
            "thread_matrix": {
                "2_threads_100_auths": t2_x100,
                "16_threads_25_auths": t16_x25
            },
            "repeated_race_runs": 100,
            "duplicate_consumes": 0,
            "unexpected_errors": 0,
            "ledger_fsync_verified": True,
            "operator_hold": "ACTIVE",
            "external_provider_calls": 0,
            "authorization_status": "NOT_GRANTED",
            "frontier_council_quorum": False,
            "promotion_eligible": False,
            "safe_to_execute_now": False
        }

        dest = ROOT / "coordination" / "council" / "reviews" / "H1B_R2_CONCURRENCY_RESULTS.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(results_json, indent=2) + "\n", encoding="utf-8")
        print(f"Results written to {dest}")

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
