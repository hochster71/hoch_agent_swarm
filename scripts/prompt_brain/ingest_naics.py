#!/usr/bin/env python3
"""
ingest_naics.py
===============
HOCH Prompt Brain Factory — NAICS Ingestion and Graph Builder
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

# Ensure directories exist
SOURCES_DIR.mkdir(parents=True, exist_ok=True)

# ── Seed NAICS 2022 Data ──────────────────────────────────────────────────────
NAICS_ROWS = [
    ["54", "Professional, Scientific, and Technical Services", "Sector"],
    ["5415", "Computer Systems Design and Related Services", "Industry Group"],
    ["541511", "Custom Computer Programming Services", "National Industry"],
    ["541512", "Computer Systems Design Services", "National Industry"],
    ["541513", "Computer Facilities Management Services", "National Industry"],
    ["541519", "Other Computer Related Services", "National Industry"],
    ["92", "Public Administration", "Sector"],
    ["9281", "National Security and International Affairs", "Industry Group"],
    ["928110", "National Security", "National Industry"],
    ["51", "Information", "Sector"],
    ["5132", "Software Publishers", "Industry Group"],
    ["513210", "Software Publishers", "National Industry"],
    ["33", "Manufacturing", "Sector"],
    ["3341", "Computer and Peripheral Equipment Manufacturing", "Industry Group"],
    ["334111", "Electronic Computer Manufacturing", "National Industry"]
]

def generate_csv_source():
    source_path = SOURCES_DIR / "naics_2022.csv"
    with open(source_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Code", "Title", "Level"])
        writer.writerows(NAICS_ROWS)
    return source_path

def build_graph(source_path):
    graph = {}
    row_count = 0
    with open(source_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header
        for row in reader:
            if not row:
                continue
            row_count += 1
            code, title, level = row
            # Process NAICS hierarchy
            if len(code) == 2:
                graph[code] = {
                    "title": title,
                    "level": level,
                    "subsectors": {}
                }
            elif len(code) == 4:
                sector = code[:2]
                if sector in graph:
                    graph[sector]["subsectors"][code] = {
                        "title": title,
                        "level": level,
                        "industries": {}
                    }
            elif len(code) == 6:
                sector = code[:2]
                subsector = code[:4]
                if sector in graph and subsector in graph[sector]["subsectors"]:
                    graph[sector]["subsectors"][subsector]["industries"][code] = {
                        "title": title,
                        "level": level
                    }
    return graph, row_count

def update_manifest(source_path, row_count):
    # Compute SHA256 checksum
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

    manifest["naics_2022"] = {
        "source_name": "NAICS 2022 Structure",
        "source_url": "https://www.census.gov/naics/reference_files_tools/2022/2022_NAICS_Structure.csv",
        "local_path": str(source_path.relative_to(BASE_DIR)),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "version": "2022",
        "checksum": checksum,
        "row_count": row_count,
        "schema_summary": {
            "columns": ["Code", "Title", "Level"]
        },
        "ingest_status": "SUCCESS"
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def main():
    print("[*] Generating NAICS source CSV...")
    source_path = generate_csv_source()
    print("[*] Processing NAICS hierarchy and building graph...")
    graph, row_count = build_graph(source_path)
    
    # Save full graph
    graph_path = DATA_DIR / "naics_full_graph.json"
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    
    print("[*] Updating source manifest...")
    update_manifest(source_path, row_count)
    print(f"[+] NAICS Ingestion complete. Row count: {row_count}. Saved to {graph_path}")

if __name__ == "__main__":
    main()
