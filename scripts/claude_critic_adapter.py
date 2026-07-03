#!/usr/bin/env python3
import os
import sys

def run_adapter():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY missing. Marking as DISABLED_NOT_CONFIGURED.")
        sys.exit(0)
        
    print("Mock Anthropic API call processed successfully.")

if __name__ == "__main__":
    run_adapter()
