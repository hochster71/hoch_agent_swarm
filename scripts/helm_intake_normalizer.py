#!/usr/bin/env python3
import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from council_respond import ask_openai_compat, ask_anthropic, ENV, ROSTER

INTAKE_PROMPT = """You are the HELM Intake Normalizer.
Your job is to take raw pasted information and convert it into a valid, structured JSON packet matching the HELM_COUNCIL_ALIGNMENT_PACKET schema.

Output ONLY valid JSON. No markdown backticks, no preamble, no conversational text.

JSON Schema:
{
  "mission_name": "HELM · Hoch Ecosystem Logic Matrix · Live Command",
  "north_star_goal": "string",
  "primary_system": "string",
  "factories": [ "string" ],
  "current_objective": "string",
  "non_negotiable_doctrine": [ "string" ],
  "required_outputs": [ "string" ],
  "council_routing": {
    "council_assignments": [
      { "member": "string", "task": "string" }
    ]
  },
  "jira_backlog": [
    {
      "key": "string (e.g. HCF-ATO-001)",
      "issue_type": "Epic|Story|Task|Sub-task|Bug",
      "summary": "string",
      "factory": "HCF|HASF|HRF|HMF|HSF|HPF|HFF|CORE",
      "mission_area": "runtime|cybersecurity|orchestration|dashboard|evidence|deployment",
      "description": "string",
      "acceptance_criteria": [ "string" ],
      "evidence_required": [ "string" ],
      "owner": "HELM|AG IDE|SecurityScan-W1|ConMon-Sentinel|Founder|Gordy",
      "status_gate": "UNKNOWN",
      "founder_gate": boolean,
      "dependencies": [ "string" ],
      "definition_of_done": [ "string" ]
    }
  ],
  "expected_outcome_state": {
    "overall_status": "IN_PROGRESS",
    "reason": "string",
    "next_action": "string",
    "promotion_allowed": false,
    "blocked_by": [ "string" ],
    "safe_to_execute_now": [ "string" ],
    "founder_gate_required": [ "string" ]
  }
}

RAW INFORMATION TO NORMALIZE:
=============================
{raw_text}
"""

def normalize(raw_text):
    # Use ChatGPT (OpenAI) as the default intake compiler
    openai_seat = next((s for s in ROSTER.get("seats", []) if s["name"] == "ChatGPT (OpenAI)"), None)
    if not openai_seat:
        # Fallback to Claude
        openai_seat = next((s for s in ROSTER.get("seats", []) if s["name"] == "Claude (Anthropic)"), None)
    
    if not openai_seat:
        print("Error: No active compiler seat found in roster.")
        sys.exit(1)
        
    prompt = INTAKE_PROMPT.format(raw_text=raw_text)
    
    print(f"Normalizing raw input using {openai_seat['name']}...")
    if openai_seat["provider"] == "anthropic":
        reply, err = ask_anthropic(openai_seat, prompt)
    else:
        reply, err = ask_openai_compat(openai_seat, prompt)
        
    if not reply:
        print(f"Error: Failed to get response from compiler. Details: {err}")
        sys.exit(1)
        
    # Clean the reply to ensure it is pure JSON
    reply = reply.strip()
    if reply.startswith("```json"):
        reply = reply[7:]
    if reply.endswith("```"):
        reply = reply[:-3]
    reply = reply.strip()
    
    try:
        data = json.loads(reply)
        return data
    except Exception as e:
        print("Error: Response was not valid JSON.")
        print("Response received:")
        print(reply)
        print("Exception:", e)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/helm_intake_normalizer.py <path_to_raw_text_file>")
        sys.exit(1)
        
    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: File {input_path} does not exist.")
        sys.exit(1)
        
    raw_text = input_path.read_text()
    normalized_data = normalize(raw_text)
    
    output_path = ROOT / "coordination/HELM_COUNCIL_ALIGNMENT_PACKET_v1.json"
    with open(output_path, "w") as f:
        json.dump(normalized_data, f, indent=2)
        
    # Also write a copy to artifacts
    artifacts_path = ROOT / "artifacts/HELM_COUNCIL_ALIGNMENT_PACKET_v1.json"
    with open(artifacts_path, "w") as f:
        json.dump(normalized_data, f, indent=2)
        
    print(f"🟢 Successfully compiled and saved to:")
    print(f"  - {output_path}")
    print(f"  - {artifacts_path}")

if __name__ == "__main__":
    main()
