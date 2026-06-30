#!/usr/bin/env python3
import os
import sys
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "local_inventory.json")

TARGET_DIRS = [
    os.path.expanduser("~/hoch_agent_swarm"),
    os.path.expanduser("~/hoch_agent_swarm_prompt_library")
]

def scan_directory(dir_path):
    if not os.path.exists(dir_path):
        return None

    file_count = 0
    total_size = 0
    extensions = {}

    for root, dirs, files in os.walk(dir_path):
        # Skip git and venv folders
        if '.git' in root or '.venv' in root or 'node_modules' in root:
            continue
        for f in files:
            fp = os.path.join(root, f)
            try:
                if os.path.isfile(fp) and not os.path.islink(fp):
                    file_count += 1
                    total_size += os.path.getsize(fp)
                    ext = os.path.splitext(f)[1].lower() or "no_extension"
                    extensions[ext] = extensions.get(ext, 0) + 1
            except Exception:
                pass

    # Check git uncommitted status
    uncommitted = []
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=dir_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if res.returncode == 0:
            uncommitted = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    return {
        "path": dir_path,
        "name": os.path.basename(dir_path),
        "file_count": file_count,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "extensions": extensions,
        "uncommitted_files_count": len(uncommitted),
        "uncommitted_files": uncommitted[:15] # Top 15 uncommitted files
    }

def main():
    print("==================================================")
    print("INGESTING LOCAL HARD DRIVE PROJECT INVENTORY (T008)")
    print("==================================================")

    inventory = []
    for d in TARGET_DIRS:
        print(f"Scanning local directory: {d}...")
        res = scan_directory(d)
        if res:
            inventory.append(res)
            print(f" • Done: {res['file_count']} files, {res['total_size_mb']} MB, {res['uncommitted_files_count']} uncommitted items.")
        else:
            print(f" • Warning: Directory {d} does not exist.")

    # Save to JSON
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2)

    print(f"Success: Wrote local inventory to {OUTPUT_PATH}.")

if __name__ == "__main__":
    main()
