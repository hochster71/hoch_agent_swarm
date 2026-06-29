import os
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "unit"

class RegressionGenerator:
    def __init__(self):
        os.makedirs(TESTS_DIR, exist_ok=True)
        
    def generate_regression_test(self, test_name: str, assert_logic: str) -> str:
        test_file = TESTS_DIR / f"test_regression_{test_name}.py"
        content = f"""# Auto-generated regression test
def test_regression_{test_name}():
    # Assertion logic
    {assert_logic}
"""
        with open(test_file, "w") as f:
            f.write(content)
        return str(test_file)
