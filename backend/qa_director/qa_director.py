import subprocess

class QADirector:
    def __init__(self):
        pass
        
    def run_qa_suite(self) -> dict:
        # Run tests and collect evidence
        try:
            res = subprocess.run(["pytest", "tests/unit/test_claim_guard.py"], capture_output=True, text=True)
            return {
                "exit_code": res.returncode,
                "output": res.stdout,
                "success": res.returncode == 0
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "output": str(e),
                "success": False
            }
