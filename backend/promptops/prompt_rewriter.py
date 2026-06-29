import uuid
from datetime import datetime

class PromptRewriter:
    def rewrite(self, weak_prompt: str, prompt_class: str) -> dict:
        mission_id = f"MSN-{uuid.uuid4().hex[:6].upper()}"
        
        # Build structure for rewrite
        objective = weak_prompt.strip()
        
        # Infer properties based on prompt class
        if prompt_class == "DOCKER_RUNTIME":
            current_proven_state = "Docker context selected; daemon is responsive. has-api, has-ui, has-worker running healthy."
            exact_scope = "backend/main.py, docker-compose.yml, Dockerfiles"
            non_goals = "Do not replace Compose with Kubernetes. Do not alter local filesystem paths."
            required_files = "docker-compose.yml"
            required_gates = "docker_truth_check.sh, docker_gate.sh"
            runtime_truth_signals = "docker_context, docker_daemon_status, has_api_status"
            evidence_path = f"docs/evidence/promptops/{datetime.now().strftime('%Y%m%d-%H%M%S')}-docker-runtime.md"
            closeout_report_schema = "status, command output, evidence_path, git_sha"
        elif prompt_class == "KUBERNETES_LANE":
            current_proven_state = "Kubernetes k3d cluster is active for local mesh tests but compose is default runtime."
            exact_scope = "scripts/k8s_gate.sh, kubernetes/deployment.yaml"
            non_goals = "Do not set Kubernetes as production canonical environment yet."
            required_files = "scripts/k8s_gate.sh"
            required_gates = "k8s_gate.sh, docker_truth_check.sh"
            runtime_truth_signals = "k8s_cluster_status, k8s_pod_status"
            evidence_path = f"docs/evidence/promptops/{datetime.now().strftime('%Y%m%d-%H%M%S')}-k8s-lane.md"
            closeout_report_schema = "status, cluster details, evidence_path"
        elif prompt_class == "SHOPPING_RESEARCH_GATE":
            current_proven_state = "Safe Bounded Mode Enforced. Purchase actions strictly blocked."
            exact_scope = "backend/operator_tasks/shopping_research_gate.py"
            non_goals = "Do not enable real purchase or saved payment changes."
            required_files = "backend/operator_tasks/shopping_research_gate.py"
            required_gates = "zero_defect_gate.sh, final_verifier_gate.sh"
            runtime_truth_signals = "shopping_research_gate_status, purchase_block_status"
            evidence_path = f"docs/evidence/promptops/{datetime.now().strftime('%Y%m%d-%H%M%S')}-shopping-gate.md"
            closeout_report_schema = "status, candidates count, blocked purchase count"
        else:
            current_proven_state = "System is in restricted local mode under Final Verifier and Runtime Truth."
            exact_scope = "Specified files in task description"
            non_goals = "Do not modify unrelated backend directories. Do not suppress active warnings."
            required_files = "Affected code files"
            required_gates = "final_verifier_gate.sh, anti_fake_gate.sh"
            runtime_truth_signals = "final_verifier_status, readiness_score"
            evidence_path = f"docs/evidence/promptops/{datetime.now().strftime('%Y%m%d-%H%M%S')}-general-run.md"
            closeout_report_schema = "status, gates passed, evidence path, commit hash"
            
        commit_policy = "feat(promptops): " + objective[:40]
        stop_conditions = "Exit immediately if any pytest fails or code does not build."
        fake_completion_controls = "Do not report task as done without raw shell command outputs."

        rewritten_contract = f"""# PromptOps Bounded Contract: {mission_id}
Class: {prompt_class}

## Objective
{objective}

## Current Proven State
{current_proven_state}

## Exact Scope
{exact_scope}

## Non-Goals
{non_goals}

## Required Files
{required_files}

## Required Gates
{required_gates}

## Telemetry Signals
{runtime_truth_signals}

## Evidence Path
{evidence_path}

## Commit Policy
{commit_policy}

## Closeout Report Schema
{closeout_report_schema}

## Stop Conditions
{stop_conditions}

## Fake-Completion Controls
{fake_completion_controls}
"""
        return {
            "mission_id": mission_id,
            "prompt_class": prompt_class,
            "objective": objective,
            "current_proven_state": current_proven_state,
            "exact_scope": exact_scope,
            "non_goals": non_goals,
            "required_files": required_files,
            "required_gates": required_gates,
            "runtime_truth_signals": runtime_truth_signals,
            "evidence_path": evidence_path,
            "commit_policy": commit_policy,
            "closeout_report_schema": closeout_report_schema,
            "stop_conditions": stop_conditions,
            "fake_completion_controls": fake_completion_controls,
            "rewritten_text": rewritten_contract
        }
