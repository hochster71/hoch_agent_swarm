import os
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from backend.runtime_execution_store import persist_crewai_ingested_artifact, get_crewai_ingested_artifact, now_iso

CREWAI_ARTIFACTS_DIR = Path.home() / "hoch_agent_swarm" / "artifacts"

def get_sha256_hash(filepath: Path) -> str:
    """Calculate the SHA-256 hash of a file's content."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_file_created_at(filepath: Path) -> str:
    """Get file modification time as an ISO-8601 string."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:
        return now_iso()

def parse_markdown_metadata(content: str) -> dict:
    """Parse basic metadata from a markdown file."""
    metadata = {}
    lines = content.splitlines()
    # Find first header
    for line in lines:
        if line.startswith("#"):
            metadata["title"] = line.lstrip("#").strip()
            break
    metadata["line_count"] = len(lines)
    return metadata

def parse_yaml_metadata(content: str) -> dict:
    """Parse basic metadata from a simple YAML manifest file."""
    metadata = {}
    lines = content.splitlines()
    metadata["line_count"] = len(lines)
    
    # Simple YAML parsing for basic properties
    archetypes = []
    in_archetypes = False
    indent_level = None
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
            
        # Detect archetype definitions
        if stripped == "archetypes:":
            in_archetypes = True
            continue
            
        if in_archetypes:
            # Check indentation to determine if we are still inside archetypes
            leading_spaces = len(line) - len(line.lstrip(" "))
            if indent_level is None:
                indent_level = leading_spaces
            elif leading_spaces < indent_level:
                in_archetypes = False
                continue
                
            if leading_spaces == indent_level and stripped.endswith(":"):
                archetype_name = stripped[:-1].strip()
                archetypes.append(archetype_name)
                
        # Parse version
        if stripped.startswith("version:"):
            metadata["version"] = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            
    metadata["archetypes"] = archetypes
    metadata["archetype_count"] = len(archetypes)
    return metadata

def run_crewai_ingestion() -> dict:
    """
    Scans the configured CrewAI artifacts directories, verifies their integrity,
    and updates/inserts them into the SQLite database.
    Does not move, rename, or delete any files.
    """
    results = {
        "scanned": 0,
        "ingested": 0,
        "updated": 0,
        "new": 0,
        "skipped": 0,
        "artifacts": []
    }
    
    if not CREWAI_ARTIFACTS_DIR.exists():
        return results

    # Define paths to scan
    subdirs = {
        "antigravity": "antigravity_plan",
        "crew_runs": "crew_run_report",
        "agent_manifests": "agent_manifest"
    }

    for subdir_name, artifact_type in subdirs.items():
        subdir_path = CREWAI_ARTIFACTS_DIR / subdir_name
        if not subdir_path.exists():
            continue
            
        for root, _, files in os.walk(subdir_path):
            for file in files:
                # Skip hidden/system files
                if file.startswith("."):
                    continue
                    
                filepath = Path(root) / file
                results["scanned"] += 1
                
                try:
                    file_hash = get_sha256_hash(filepath)
                    created_at = get_file_created_at(filepath)
                    
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                    run_context = {
                        "filename": file,
                        "file_size": filepath.stat().st_size,
                    }
                    
                    # Custom parsing based on type
                    if artifact_type == "antigravity_plan":
                        run_context.update(parse_markdown_metadata(content))
                    elif artifact_type == "agent_manifest":
                        run_context.update(parse_yaml_metadata(content))
                    elif artifact_type == "crew_run_report":
                        run_context["title"] = f"Crew Run Report: {file}"
                        if file.endswith(".json"):
                            try:
                                report_data = json.loads(content)
                                if isinstance(report_data, dict):
                                    for key in ["crew_name", "run_id", "agent", "status", "timestamp"]:
                                        if key in report_data:
                                            run_context[key] = report_data[key]
                            except Exception as je:
                                print(f"Could not parse crew_run_report JSON file {file}: {je}")
                        
                    # Deterministic ID based on source path so we keep 1 record per path
                    rel_path = filepath.relative_to(Path.home())
                    source_path = f"~/{rel_path}"
                    
                    path_hash = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16]
                    artifact_id = f"crewai_{path_hash}"
                    
                    artifact_record = {
                        "id": artifact_id,
                        "source_path": source_path,
                        "hash": file_hash,
                        "created_at": created_at,
                        "artifact_type": artifact_type,
                        "run_context_json": json.dumps(run_context),
                        "ingested_at": now_iso()
                    }
                    
                    existing = get_crewai_ingested_artifact(artifact_id)
                    if existing:
                        if existing["hash"] == file_hash:
                            results["skipped"] += 1
                        else:
                            persist_crewai_ingested_artifact(artifact_record)
                            results["ingested"] += 1
                            results["updated"] += 1
                            results["new"] += 1
                            results["artifacts"].append({
                                "id": artifact_id,
                                "source_path": source_path,
                                "artifact_type": artifact_type,
                                "hash": file_hash,
                                "created_at": created_at
                            })
                    else:
                        persist_crewai_ingested_artifact(artifact_record)
                        results["ingested"] += 1
                        results["new"] += 1
                        results["artifacts"].append({
                            "id": artifact_id,
                            "source_path": source_path,
                            "artifact_type": artifact_type,
                            "hash": file_hash,
                            "created_at": created_at
                        })
                    
                except Exception as e:
                    # Log error internally and continue scanning other files
                    print(f"Error ingesting file {filepath}: {e}")
                    
    return results
