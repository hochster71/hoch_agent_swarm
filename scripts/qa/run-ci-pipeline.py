import subprocess
import time
import urllib.request
import sys
import os

BASE_URL = "http://localhost:8000"

def is_server_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=2) as response:
            return response.getcode() == 200
    except Exception:
        return False

def run_command(command: str) -> bool:
    print(f"\n==================================================")
    print(f"RUNNING: {command}")
    print(f"==================================================")
    # Run command inside repo root
    res = subprocess.run(command, shell=True, env=os.environ)
    if res.returncode != 0:
        print(f" [FAIL] Command failed with code {res.returncode}")
        return False
    print(f" [PASS] Command succeeded.")
    return True

def main():
    print("==================================================")
    print("STARTING LOCAL/CI SERVICE CONTAINER PIPELINE RUNNER")
    print("==================================================")

    # 1. Start FastAPI server process
    print("Launching FastAPI server via Uvicorn...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", "8000", "--host", "0.0.0.0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONPATH": ".", "TEST_MODE": "true"}
    )

    # 2. Wait for server to become healthy
    healthy = False
    for i in range(15):
        time.sleep(1)
        if is_server_healthy():
            healthy = True
            break
        print(f"Waiting for server to listen on port 8000 (attempt {i+1}/15)...")

    if not healthy:
        print(" [FAIL] Server failed to start or become healthy on port 8000 within 15 seconds.")
        server_process.terminate()
        sys.exit(1)
    print(" [OK] FastAPI server is live and healthy.")

    # 3. Execute pipeline tests
    success = True
    tests = [
        "npx tsx scripts/qa/test-autonomy-budget.ts",
        "npm run qa:ui-contract",
        "npm run qa:readiness",
        "npm run supply:release"
    ]

    for t in tests:
        if not run_command(t):
            success = False
            break

    # 4. Tear down FastAPI server
    print("\nTearing down FastAPI server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    print(" [OK] Server terminated cleanly.")

    # 5. Exit status
    if success:
        print("\n==================================================")
        print(" [PASS] FULL INTEGRATION PIPELINE COMPLETED SUCCESSFULLY")
        print("==================================================")
        sys.exit(0)
    else:
        print("\n==================================================")
        print(" [FAIL] INTEGRATION PIPELINE RUN FAILED")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    main()
