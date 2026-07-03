#!/usr/bin/env python3
import os
import sys
import json

def run_adapter():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY missing. Running in mock/dry-run mode.")
        sys.exit(0)
        
    # Dummy placeholder call that respects data-egress rules
    print("Mock OpenAI API call processed successfully.")

if __name__ == "__main__":
    run_adapter()
