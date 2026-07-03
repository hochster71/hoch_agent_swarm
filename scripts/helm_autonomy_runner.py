#!/usr/bin/env python3
import sys
import json
import time
import http.client
import os
from datetime import datetime
from pathlib import Path

# Add scripts directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent))
from helm_policy_engine import PolicyEngine

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
STATE_FILE = DATA_DIR / "helm_runtime_state.json"
LOG_FILE = DATA_DIR / "helm_execution_log.json"
REGISTRY_FILE = DATA_DIR / "helm_agent_registry.json"

policy_engine = PolicyEngine()

def get_current_utc():
    return datetime.utcnow().isoformat() + "Z"

def log_message(msg):
    print(f"[{get_current_utc()}] [HELM-RUNNER] {msg}")

def query_llm(prompt, tier="light", agent_id="hasf_scoring_agent"):
    # Policy enforcement check
    adapter_id = "ollama_native" if tier == "light" else "lmstudio"
    action = "query_light_model" if tier == "light" else "query_heavy_model"
    allowed, reason = policy_engine.check(agent_id, adapter_id, action)
    if not allowed:
        log_message(f"Policy Engine BLOCKED execution: {reason}")
        return f"Error: Policy violation: {reason}", "none", "none"
    # Target configurations
    native_cfg = {
        "host": "localhost",
        "port": 11434,
        "model": "qwen2.5:1.5b-instruct",
        "timeout": 90,
        "label": "Native Ollama qwen2.5:1.5b-instruct",
        "provider": "ollama_native"
    }
    tunnel_cfg = {
        "host": "localhost",
        "port": 1234,
        "model": "google/gemma-4-12b-qat",
        "timeout": 90,
        "label": "LM Studio tunnel google/gemma-4-12b-qat",
        "provider": "lmstudio"
    }

    # Route order based on tier
    if tier == "heavy":
        steps = [tunnel_cfg, native_cfg]
    else:
        steps = [native_cfg, tunnel_cfg]

    for step in steps:
        try:
            log_message(f"Attempting inference via {step['label']} on port {step['port']}...")
            conn = http.client.HTTPConnection(step["host"], step["port"], timeout=step["timeout"])
            payload = json.dumps({
                "model": step["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "stream": False
            })
            conn.request("POST", "/v1/chat/completions", payload, {
                "Content-Type": "application/json"
            })
            res = conn.getresponse()
            if res.status == 200:
                data = json.loads(res.read().decode())
                return data["choices"][0]["message"]["content"], step["model"], step["provider"]
            else:
                log_message(f"Adapter port {step['port']} returned HTTP {res.status}")
        except Exception as e:
            log_message(f"Inference on port {step['port']} failed: {e}")

    return "Error: All routed model backends failed.", "none", "none"

def execute_scoring_task(task_desc, tier="light", agent_id="hasf_scoring_agent"):
    log_message("Executing product candidate scoring task...")
    prompt = f"""
Analyze the following Product 002 candidates against these HASF mission filters:
1. CyberQRG-AI (cyberqrg-ai) - AI security QR code vulnerability scanner.
2. HOCH HASF Soccer Intelligence Platform (hoch-hasf-soccer) - Sports prediction intelligence.
3. OmniSeek / OmniSeek Sentinel (omniseek-sentinel) - Semantic search aggregator.
4. AquaForge (aquaforge) - IoT water analytics telemetry.

Provide a markdown report ranking them 1-4 with a brief utility score and rationale based on actual human utility, automation capability, and security impact.
Respond ONLY with clean markdown.
"""
    return query_llm(prompt, tier=tier, agent_id=agent_id)

def execute_roadmap_task(task_desc, tier="light", agent_id="hasf_scoring_agent"):
    log_message("Executing CyberQRG-AI roadmap generation task...")
    prompt = """
Generate a development roadmap for Product 002: CyberQRG-AI (AI security QR code vulnerability scanner).
Detail key phases for a local mobile-first implementation (e.g. Phase 1: Camera capture & API setup, Phase 2: Redirect parsing, Phase 3: Local LLM evaluation integration).
Respond ONLY with clean markdown.
"""
    return query_llm(prompt, tier=tier, agent_id=agent_id)

def execute_gate_package_task(task_desc, tier="heavy", agent_id="hasf_builder_agent"):
    log_message("Executing Product 002 candidate gate package task...")
    prompt = """
Generate a comprehensive Product 002 gate review package for CyberQRG-AI.
Detail:
1. Candidate Security Profile (OWASP Top 10 mobile concerns for QR scanner).
2. Automation workflow evaluation.
3. Live validation path (e.g. founder approval gated link).
Respond ONLY with clean markdown.
"""
    return query_llm(prompt, tier=tier, agent_id=agent_id)

def main():
    log_message("HELM Autonomy Runner Daemon started.")
    
    # Verify state directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        try:
            # Update state file to IDLE preserving other fields
            state_data = {}
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE, "r") as sf:
                        state_data = json.load(sf)
                except:
                    pass
            state_data.update({
                "status": "IDLE",
                "last_run": get_current_utc(),
                "active_task_id": None
            })
            with open(STATE_FILE, "w") as f:
                json.dump(state_data, f, indent=2)
                
            if not QUEUE_FILE.exists():
                time.sleep(5)
                continue
                
            with open(QUEUE_FILE, "r") as f:
                queue = json.load(f)
                
            queued_tasks = [t for t in queue if t["status"] == "queued"]
            if not queued_tasks:
                time.sleep(5)
                continue
                
            task = queued_tasks[0]
            task_id = task["id"]
            started_at = get_current_utc()
            
            log_message(f"Found queued task: {task_id} - '{task['description']}'")
            
            # Resolve capacity tier and details
            tier = "light"
            risk_tier = "R0"
            try:
                if REGISTRY_FILE.exists():
                    with open(REGISTRY_FILE, "r") as rf:
                        reg = json.load(rf)
                    agent_name = task.get("assigned_agent")
                    if agent_name in reg:
                        tier = reg[agent_name].get("capacity_tier", "light")
                        if tier == "heavy":
                            risk_tier = "R1"
            except Exception as e:
                log_message(f"Error loading agent registry for tiering: {e}")
                
            log_message(f"Resolved capacity tier: {tier} for agent: {task.get('assigned_agent')}")
            
            # Update state to RUNNING preserving other fields
            state_data = {}
            if STATE_FILE.exists():
                try:
                    with open(STATE_FILE, "r") as sf:
                        state_data = json.load(sf)
                except:
                    pass
            state_data.update({
                "status": "RUNNING",
                "last_run": get_current_utc(),
                "active_task_id": task_id
            })
            with open(STATE_FILE, "w") as f:
                json.dump(state_data, f, indent=2)
                
            # Update task status to in-progress
            task["status"] = "in-progress"
            with open(QUEUE_FILE, "w") as f:
                json.dump(queue, f, indent=2)
                
            # Execute
            result_text = ""
            selected_model = "none"
            selected_adapter = "none"
            file_name = "autonomous-task-proof.md"
            agent_id = task.get("assigned_agent", "hasf_scoring_agent")
            
            if "scoring report" in task["description"].lower():
                result_text, selected_model, selected_adapter = execute_scoring_task(task["description"], tier=tier, agent_id=agent_id)
                file_name = "autonomous-task-proof.md"
            elif "roadmap" in task["description"].lower():
                result_text, selected_model, selected_adapter = execute_roadmap_task(task["description"], tier=tier, agent_id=agent_id)
                file_name = "cyberqrg-roadmap-proof.md"
            elif "gate" in task["description"].lower() or "package" in task["description"].lower():
                result_text, selected_model, selected_adapter = execute_gate_package_task(task["description"], tier=tier, agent_id=agent_id)
                file_name = "cyberqrg-gate-package.md"
            else:
                result_text = f"Unmapped task template: {task['description']}"
                
            # Policy enforcement check for writing evidence
            allowed, reason = policy_engine.check(agent_id, "evidence_writer", "write_markdown_evidence")
            if not allowed:
                log_message(f"Policy Engine BLOCKED evidence writing: {reason}")
                task["status"] = "blocked"
                with open(QUEUE_FILE, "w") as f:
                    json.dump(queue, f, indent=2)
                continue
                
            # Save task results/evidence
            run_id = "20260702T222129Z-24-7-autonomy-reset"
            evidence_dir = ROOT / f"docs/evidence/runtime_scenarios/{run_id}"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            evidence_path = evidence_dir / file_name
            
            evidence_content = f"""# Autonomous Task Proof
 
* **Task ID**: {task_id}
* **Executed By**: {task['assigned_agent']} (Model: native qwen2.5:1.5b-instruct / fallback gemma-4-12b-qat)
* **Timestamp**: {get_current_utc()}
* **Status**: Complete
 
---
 
## Task Output
 
{result_text}
"""
            with open(evidence_path, "w") as f:
                f.write(evidence_content)
                
            log_message(f"Evidence written to {evidence_path.name}")
            
            # Complete task in queue
            task["status"] = "completed"
            task["completed_at"] = get_current_utc()
            task["result"] = f"file://{evidence_path}"
            
            with open(QUEUE_FILE, "w") as f:
                json.dump(queue, f, indent=2)
                
            # Write to execution log
            logs = []
            if LOG_FILE.exists():
                with open(LOG_FILE, "r") as f:
                    try:
                        logs = json.load(f)
                    except:
                        pass
            logs.append({
                "task_id": task_id,
                "agent_id": task.get("assigned_agent"),
                "lifecycle_state": "COMPLETED",
                "selected_model": selected_model,
                "selected_adapter": selected_adapter,
                "task_class": "planning" if tier == "light" else "engineering",
                "risk_tier": risk_tier,
                "evidence_path": str(evidence_path),
                "verification_result": "PASSED" if "Error" not in result_text else "FAILED",
                "retry_count": task.get("attempts", 0),
                "incident_class": "none" if "Error" not in result_text else "model_output",
                "founder_approval_required": False,
                "started_at": started_at,
                "completed_at": task["completed_at"]
            })
            with open(LOG_FILE, "w") as f:
                json.dump(logs, f, indent=2)
                
            log_message(f"Task {task_id} marked complete.")
            
        except Exception as e:
            log_message(f"Error in runner loop: {e}")
            # Record execution failure / incident class details in log file
            try:
                logs = []
                if LOG_FILE.exists():
                    with open(LOG_FILE, "r") as f:
                        logs = json.load(f)
                logs.append({
                    "task_id": task_id if 'task_id' in locals() else "unknown",
                    "agent_id": task.get("assigned_agent") if 'task' in locals() else "unknown",
                    "lifecycle_state": "FAILED",
                    "incident_class": "adapter_failure" if "Connection" in str(e) else "unknown",
                    "root_cause_candidate": str(e),
                    "recovery_action": "check_connectivity_and_retry",
                    "retry_count": task.get("attempts", 0) if 'task' in locals() else 0,
                    "escalation_state": "ESCALATED_TO_FOUNDER",
                    "adapter_id": "none",
                    "model_backend": "none",
                    "timestamp": get_current_utc()
                })
                with open(LOG_FILE, "w") as f:
                    json.dump(logs, f, indent=2)
            except Exception as le:
                log_message(f"Failed to log incident: {le}")
            time.sleep(10)
            
        time.sleep(2)

if __name__ == "__main__":
    main()
