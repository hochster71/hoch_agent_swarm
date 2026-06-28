#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/qa/run-ci-pipeline.py — CI pipeline execution helper.
"""

import sys
import subprocess

def run_ci():
    print("=== STARTING SWARM CI PIPELINE ===")
    
    # Run pytest
    print("\nRunning test suite...")
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    res = subprocess.run(["uv", "run", "pytest"], env=env, capture_output=False)
    
    if res.returncode == 0:
        print("\n=== CI PIPELINE PASSED SUCCESSFULLY ===")
        sys.exit(0)
    else:
        print("\n=== CI PIPELINE FAILED ===")
        sys.exit(res.returncode)

if __name__ == "__main__":
    run_ci()
