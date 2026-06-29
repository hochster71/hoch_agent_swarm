import sqlite3
import json
import os
import sys
from datetime import datetime
from hoch_agent_swarm.crew import HochAgentSwarm
from hoch_agent_swarm.artifact_validation import validate_all_artifacts

DB_PATH = "cybersecurity_diagrams.db"

def get_diagram(diagram_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diagrams WHERE id = ?", (diagram_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_mitigations(diagram_id, mitigations_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE diagrams 
        SET mitigations = ? 
        WHERE id = ?
    """, (mitigations_text, diagram_id))
    conn.commit()
    conn.close()

def run_analysis(diagram_id):
    row = get_diagram(diagram_id)
    if not row:
        print(f"Error: Diagram ID {diagram_id} not found.")
        return False
        
    print(f"\n[pipeline] Analyzing Diagram ID {diagram_id}: {row['title']}")
    print(f"[-] Architecture Type: {row['architecture_type']}")
    print(f"[-] Component Set: {row['components']}")
    print(f"[-] Input Threat Vectors: {row['threat_vectors']}")
    
    # Structure inputs for HochAgentSwarm
    inputs = {
        "topic": f"Analysis and Mitigation of {row['title']}: {row['description']}",
        "current_year": str(datetime.now().year),
        "antigravity_role": "Agentic security auditor and designer.",
        "crewai_role": f"Hoch Agent Swarm analyzing {row['architecture_type']}.",
        "integration_mode": (
            f"Analyze components {row['components']} and threat vectors {row['threat_vectors']} "
            "to compile mitigations into reports."
        )
    }
    
    print("\n[pipeline] Kicking off HochAgentSwarm crew run...")
    try:
        crew = HochAgentSwarm()
        result = crew.crew().kickoff(inputs=inputs)
        print("[pipeline] Crew execution completed successfully.")
    except Exception as e:
        print(f"[pipeline] Crew execution failed: {e}")
        return False
        
    # Run validation
    print("[pipeline] Running output validation...")
    try:
        validate_all_artifacts(strict=True)
        print("[pipeline] Output artifacts validated successfully.")
    except Exception as e:
        print(f"[pipeline] Artifact validation failed: {e}")
        return False
        
    # Read the generated Antigravity Execution Plan to extract solutions/mitigations
    plan_path = "artifacts/antigravity/antigravity_execution_plan.md"
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_content = f.read()
        
        # Save the plan text as our updated mitigations
        update_mitigations(diagram_id, plan_content)
        print(f"[pipeline] Consolidated threat model and solutions saved back to SQLite for Diagram ID {diagram_id}.")
        return True
    else:
        print(f"[pipeline] Warning: {plan_path} not found.")
        return False

if __name__ == "__main__":
    diagram_id = 1
    if len(sys.argv) > 1:
        try:
            diagram_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python run_swarm_analysis_pipeline.py [diagram_id]")
            sys.exit(1)
            
    success = run_analysis(diagram_id)
    sys.exit(0 if success else 1)
