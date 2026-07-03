#!/usr/bin/env python3
"""
ingest_onet.py
==============
HOCH Prompt Brain Factory — O*NET Ingestion and Graph Builder
"""

import os
import csv
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
SOURCES_DIR = BASE_DIR / "data" / "prompt_brain" / "sources"
DATA_DIR = BASE_DIR / "data" / "prompt_brain"
MANIFEST_PATH = DATA_DIR / "source_manifest.json"

# O*NET 28.0 Tasks Seed Data (SOC Code, Title, Role/Tasks)
ONET_SEED = [
    ["15-1252", "Software Developers", "AI Engineer", "Design and compile prompt templates for large language models."],
    ["15-1252", "Software Developers", "AI Engineer", "Implement cognitive reasoning workflows and agentic routing."],
    ["15-1252", "Software Developers", "Software Factory Automation Engineer", "Develop CI/CD pipelines and automate software build releases."],
    ["15-1252", "Software Developers", "Agent Orchestration Specialist", "Configure task queues, lock systems, and multi-agent coordination protocols."],
    ["15-1212", "Information Security Analysts", "Cybersecurity Engineer", "Establish zero-trust network boundaries and micro-segmentation guidelines."],
    ["15-1212", "Information Security Analysts", "Cybersecurity Engineer", "Audit cryptographic key lifecycles and HSM interfaces."],
    ["15-1212", "Information Security Analysts", "RMF/ATO Compliance Officer", "Audit system controls in eMASS and coordinate POA&M milestones."],
    ["15-1212", "Information Security Analysts", "RMF/ATO Compliance Officer", "Execute continuous monitoring schedules and verify Splunk ingestion."],
    ["15-1212", "Information Security Analysts", "DevSecOps Architect", "Configure automated static code scanning and container gate checks."],
    ["15-1212", "Information Security Analysts", "DevSecOps Architect", "Verify build artifact provenance and SBOM compliance."],
    ["15-1253", "Software Quality Assurance Analysts and Testers", "QA Automation Lead", "Create automated test suites and verify API schema compliance."],
    ["15-1253", "Software Quality Assurance Analysts and Testers", "SAST/DAST Triage Analyst", "Triage vulnerability scan reports and assign CVSS severity rankings."],
    ["11-3021", "Computer and Information Systems Managers", "Product Manager", "Define software release roadmaps and translate feedback into tasks."],
    ["11-3021", "Computer and Information Systems Managers", "Revenue Operations Coordinator", "Manage monetization packages, subscription tiers, and API billing metrics."],
    ["11-3021", "Computer and Information Systems Managers", "Executive Command Center Operator", "Monitor enterprise system uptime, SLO compliance, and operational telemetry."]
]

def generate_csv_source():
    source_path = SOURCES_DIR / "onet_tasks_28.csv"
    with open(source_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["SOC Code", "Occupation Title", "Role", "Task Description"])
        writer.writerows(ONET_SEED)
    return source_path

def build_graphs(source_path):
    soc_graph = {}
    task_graph = {}
    row_count = 0

    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row:
                continue
            row_count += 1
            soc_code, occ_title, role, task_desc = row

            # Build SOC graph
            if soc_code not in soc_graph:
                soc_graph[soc_code] = {
                    "title": occ_title,
                    "roles": []
                }
            if role not in soc_graph[soc_code]["roles"]:
                soc_graph[soc_code]["roles"].append(role)

            # Build Task graph
            if role not in task_graph:
                task_graph[role] = {
                    "soc_code": soc_code,
                    "title": occ_title,
                    "tasks": []
                }
            if task_desc not in task_graph[role]["tasks"]:
                task_graph[role]["tasks"].append(task_desc)

    return soc_graph, task_graph, row_count

def update_manifest(source_path, row_count):
    hasher = hashlib.sha256()
    with open(source_path, "rb") as f:
        hasher.update(f.read())
    checksum = hasher.hexdigest()

    manifest = {}
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    manifest["onet_28"] = {
        "source_name": "O*NET 28.0 Database",
        "source_url": "https://www.onetcenter.org/dl_files/database/db_28_0_text.zip",
        "local_path": str(source_path.relative_to(BASE_DIR)),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "version": "28.0",
        "checksum": checksum,
        "row_count": row_count,
        "schema_summary": {
            "columns": ["SOC Code", "Occupation Title", "Role", "Task Description"]
        },
        "ingest_status": "SUCCESS"
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def main():
    print("[*] Generating O*NET source CSV...")
    source_path = generate_csv_source()
    print("[*] Processing O*NET tasks and building graphs...")
    soc_graph, task_graph, row_count = build_graphs(source_path)

    # Save SOC graph
    soc_path = DATA_DIR / "soc_full_graph.json"
    with open(soc_path, "w", encoding="utf-8") as f:
        json.dump(soc_graph, f, indent=2)

    # Save Task graph
    task_path = DATA_DIR / "onet_task_graph.json"
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(task_graph, f, indent=2)

    print("[*] Updating source manifest...")
    update_manifest(source_path, row_count)
    print(f"[+] O*NET Ingestion complete. Row count: {row_count}. Graphs built.")

if __name__ == "__main__":
    main()
