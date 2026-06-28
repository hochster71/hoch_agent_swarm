import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from hoch_agent_swarm.crew import HochAgentSwarm
from hoch_agent_swarm.artifact_validation import (
    validate_all_artifacts,
    _extract_section_content,
    ALL_CANONICAL_ARTIFACT_PATHS,
    SECURITY_AUDIT_PATH,
    ANTIGRAVITY_PLAN_PATH
)

DB_PATH = "cybersecurity_diagrams.db"

def get_eligible_diagrams(max_items=1, stale_hours=24):
    """
    Find diagrams that:
    1. Have status is NULL, 'PENDING', or 'FAILED'
    2. OR mitigations is NULL or empty
    3. OR analyzed_at is older than stale_hours hours.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    stale_limit = datetime.now() - timedelta(hours=stale_hours)
    
    cursor.execute("""
        SELECT * FROM diagrams
        WHERE status IS NULL 
           OR status = 'PENDING'
           OR status = 'FAILED'
           OR status = 'NON-COMPLIANT'
           OR mitigations IS NULL
           OR LENGTH(TRIM(mitigations)) = 0
           OR analyzed_at IS NULL
           OR datetime(analyzed_at) < datetime(?)
        ORDER BY id ASC
        LIMIT ?
    """, (stale_limit.isoformat(), max_items))
    
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_diagram_record(diagram_id, mitigations, status, quality_score, artifact_links):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE diagrams
        SET mitigations = ?,
            status = ?,
            quality_score = ?,
            artifact_links = ?,
            analyzed_at = ?
        WHERE id = ?
    """, (
        mitigations,
        status,
        quality_score,
        json.dumps(artifact_links),
        datetime.now().isoformat(),
        diagram_id
    ))
    conn.commit()
    conn.close()

def parse_audit_verdict(audit_path):
    """Extract verdict from the security audit report."""
    if not os.path.exists(audit_path):
        return "FAILED"
    with open(audit_path, "r", encoding="utf-8") as f:
        content = f.read()
    verdict_text = _extract_section_content(content, "## Verdict")
    if not verdict_text:
        return "FAILED"
    if "COMPLIANT" in verdict_text.upper() or "PASS" in verdict_text.upper():
        return "COMPLIANT"
    elif "NON-COMPLIANT" in verdict_text.upper() or "FAIL" in verdict_text.upper():
        return "NON-COMPLIANT"
    return "COMPLIANT"  # Default fallback if valid

def calculate_quality_score(validation_passed, audit_path, plan_path):
    """Calculate quality score between 0.0 and 100.0."""
    if not validation_passed:
        return 0.0
    
    score = 50.0  # Base score for passing validation
    
    # Audit report length contribution (up to 25 pts)
    if os.path.exists(audit_path):
        size = os.path.getsize(audit_path)
        score += min(25.0, size / 100.0)
        
    # Integration plan length contribution (up to 25 pts)
    if os.path.exists(plan_path):
        size = os.path.getsize(plan_path)
        score += min(25.0, size / 150.0)
        
    return min(100.0, round(score, 1))

def process_batch(max_items=1):
    eligible = get_eligible_diagrams(max_items=max_items)
    if not eligible:
        print("[batch] No eligible diagrams found in queue.")
        return True
        
    print(f"[batch] Found {len(eligible)} diagrams to process in this batch.")
    
    all_success = True
    for row in eligible:
        diagram_id = row['id']
        title = row['title']
        print(f"\n==================================================")
        print(f"[batch] Processing Diagram ID {diagram_id}: {title}")
        print(f"==================================================")
        
        # Build trigger inputs for HochAgentSwarm
        inputs = {
            "topic": f"Batch Analysis of {title}: {row['description']}",
            "current_year": str(datetime.now().year),
            "antigravity_role": "Agentic security auditor and designer.",
            "crewai_role": f"Hoch Agent Swarm analyzing {row['architecture_type']}.",
            "integration_mode": (
                f"Analyze components {row['components']} and threat vectors {row['threat_vectors']} "
                "to compile mitigations into reports."
            )
        }
        
        # Programmatically run crew
        print("[batch] Kicking off HochAgentSwarm...")
        try:
            crew = HochAgentSwarm()
            crew.crew().kickoff(inputs=inputs)
            print("[batch] Crew run completed.")
        except Exception as e:
            print(f"[batch] Crew run failed: {e}")
            update_diagram_record(diagram_id, "", "FAILED", 0.0, [])
            all_success = False
            continue
            
        # Validate output artifacts
        print("[batch] Running semantic quality gates...")
        validation_passed = True
        try:
            validate_all_artifacts(strict=True)
            print("[batch] All quality validation checks PASSED.")
        except Exception as e:
            print(f"[batch] Semantic validation failed: {e}")
            validation_passed = False
            
        # Determine status and extract details
        status = parse_audit_verdict(SECURITY_AUDIT_PATH) if validation_passed else "FAILED"
        score = calculate_quality_score(validation_passed, SECURITY_AUDIT_PATH, ANTIGRAVITY_PLAN_PATH)
        
        # Gather links to generated reports
        artifact_links = {}
        for path in ALL_CANONICAL_ARTIFACT_PATHS:
            if os.path.exists(path):
                artifact_links[os.path.basename(path)] = os.path.abspath(path)
                
        # Extract mitigation plan text
        mitigations = ""
        if os.path.exists(ANTIGRAVITY_PLAN_PATH):
            with open(ANTIGRAVITY_PLAN_PATH, "r", encoding="utf-8") as f:
                mitigations = f.read()
                
        # Save to database
        update_diagram_record(diagram_id, mitigations, status, score, artifact_links)
        print(f"[batch] SQLite updated for Diagram ID {diagram_id}: status={status}, quality_score={score}")
        
    return all_success

if __name__ == "__main__":
    max_items = 1
    if len(sys.argv) > 1:
        try:
            max_items = int(sys.argv[1])
        except ValueError:
            print("Usage: python run_batch_swarm_analysis.py [max_items]")
            sys.exit(1)
            
    success = process_batch(max_items=max_items)
    sys.exit(0 if success else 1)
