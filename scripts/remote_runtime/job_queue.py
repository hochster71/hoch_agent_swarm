#!/usr/bin/env python3
import os
import json

def append_to_queue(job_type: str):
    path = os.path.dirname(os.path.abspath(__file__)) + "/../../data/runtime/job_queue.jsonl"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {"job_type": job_type, "status": "QUEUED"}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True

if __name__ == "__main__":
    append_to_queue("run_health_audit")
    print("Job queued.")
