#!/usr/bin/env python
import json
import os
import shutil
import sys
import warnings

from datetime import datetime

from hoch_agent_swarm.crew import HochAgentSwarm
from hoch_agent_swarm.artifact_validation import (
    ArtifactValidationError,
    ALL_CANONICAL_ARTIFACT_PATHS,
    ANTIGRAVITY_PLAN_PATH,
    SECURITY_AUDIT_PATH,
    validate_all_artifacts,
)
from hoch_agent_swarm.run_report import RunReport, STATUS_PASS, STATUS_FAIL

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# ---------------------------------------------------------------------------
# Artifact archive helpers
# ---------------------------------------------------------------------------

_ARCHIVE_DIR = "artifacts/crew_runs"

# All canonical paths to archive before overwrite; defined in artifact_validation.py
_CANONICAL_ARTIFACTS = ALL_CANONICAL_ARTIFACT_PATHS


def _archive_existing_artifacts(run_timestamp: str) -> list[tuple[str, str]]:
    """
    Before a crew run overwrites canonical artifact files, copy current
    versions into artifacts/crew_runs/<timestamp>/ so prior output is
    not silently lost.

    artifacts/crew_runs/ is gitignored, so archives are local-only.

    Returns:
        List of (source_path, archived_path) pairs for every artifact that
        was actually archived, for inclusion in the run report.
    """
    archive_dir = os.path.join(_ARCHIVE_DIR, run_timestamp)
    archived_pairs: list[tuple[str, str]] = []

    for src_path in _CANONICAL_ARTIFACTS:
        if os.path.isfile(src_path) and os.path.getsize(src_path) > 0:
            os.makedirs(archive_dir, exist_ok=True)
            dest_name = os.path.basename(src_path)
            dest_path = os.path.join(archive_dir, dest_name)
            shutil.copy2(src_path, dest_path)
            archived_pairs.append((src_path, dest_path))
            print(f"  [archive] {src_path} → {dest_path}")

    if archived_pairs:
        print()

    return archived_pairs


def _run_validation() -> dict[str, str]:
    """
    Run artifact validation after crew kickoff.
    Raises ArtifactValidationError on failure — crew run is not considered
    successful until all artifacts pass.

    Returns:
        Dict mapping canonical artifact path → "VALID" for all paths that
        passed validation (used to populate run report).
    """
    print("\n[validate] Running artifact validation...")
    validate_all_artifacts(strict=True)
    print("[validate] All artifacts passed validation.")
    return {p: "VALID" for p in ALL_CANONICAL_ARTIFACT_PATHS}


def _inputs_summary(inputs: dict) -> dict:
    """
    Extract a safe, non-secret summary of inputs for the run report.
    Drops the raw trigger payload and any key containing 'secret' or 'key'.
    """
    SKIP_KEYS = {"crewai_trigger_payload"}
    return {
        k: v
        for k, v in inputs.items()
        if k not in SKIP_KEYS
        and not any(word in k.lower() for word in ("secret", "key", "token", "password"))
        and isinstance(v, (str, int, float, bool))
    }


def _write_report(report: RunReport, run_timestamp: str) -> str:
    """Write the run report to the run archive directory and return its path."""
    run_dir = os.path.join(_ARCHIVE_DIR, run_timestamp)
    report_path = report.write(run_dir)
    print(f"\n[report] Run report written: {report_path}")
    return report_path


# ---------------------------------------------------------------------------
# Shared inputs builder
# ---------------------------------------------------------------------------

def _default_inputs(topic: str = "AI LLMs") -> dict:
    return {
        "topic": topic,
        "current_year": str(datetime.now().year),
        "antigravity_role": (
            "Agentic development cockpit, artifact reviewer, "
            "implementation planner, and IDE-level orchestrator."
        ),
        "crewai_role": (
            "Local bounded multi-agent runtime for deterministic "
            "Hoch Agent Swarm execution."
        ),
        "integration_mode": (
            "Antigravity plans and edits; CrewAI executes bounded local crews; "
            "artifacts are reviewed before promotion."
        ),
    }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run():
    """
    Run the crew, then validate all canonical output artifacts.
    Writes a run report to artifacts/crew_runs/<timestamp>/run_report.json.
    Raises on invalid output — does not silently continue.
    """
    run_timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    inputs = _default_inputs()
    report = RunReport.start(
        workflow_name="hoch_agent_swarm",
        inputs_summary=_inputs_summary(inputs),
    )

    try:
        archived_pairs = _archive_existing_artifacts(run_timestamp)
        report.record_archived_artifacts(archived_pairs)

        crew_output = HochAgentSwarm().crew().kickoff(inputs=inputs)

        validation_results = _run_validation()
        
        # Build custom metrics
        from datetime import timezone
        from hoch_agent_swarm.model_router import ModelRouter
        
        tasks_metrics = []
        role_to_key = {
            "Swarm Asset Mapper": "asset_mapper",
            "Swarm Process Architect": "swarm_architect",
            "Swarm Agent Combinator": "agent_combinator",
            "Swarm Security Auditor": "security_operator",
            "Swarm Execution Scheduler": "execution_planner",
            "Release Synthesis Director": "synthesis_director",
            "Antigravity Integration Operator": "antigravity_integration_operator",
        }
        
        task_to_artifact_path = {
            "Swarm Asset Mapper": "artifacts/research/asset_map.md",
            "Swarm Process Architect": "",
            "Swarm Agent Combinator": "",
            "Swarm Security Auditor": "artifacts/security_reviews/security_audit_report.md",
            "Swarm Execution Scheduler": "artifacts/reports/execution_plan.md",
            "Release Synthesis Director": "artifacts/reports/release_packet.md",
            "Antigravity Integration Operator": "artifacts/antigravity/antigravity_execution_plan.md",
        }
        
        total_runtime = 0.0
        if report.started_at:
            try:
                start_dt = datetime.fromisoformat(report.started_at)
                total_runtime = (datetime.now(timezone.utc) - start_dt).total_seconds()
            except Exception:
                total_runtime = 300.0
        
        num_tasks = len(crew_output.tasks_output) if crew_output and getattr(crew_output, "tasks_output", None) else 7
        avg_task_duration = total_runtime / num_tasks if num_tasks > 0 else 40.0
        
        for i, t_out in enumerate(getattr(crew_output, "tasks_output", None) or []):
            agent_role = getattr(t_out, "agent", "unknown").strip()
            agent_key = role_to_key.get(agent_role, "unknown")
            resolved = ModelRouter.resolved_models.get(agent_key, {"model": "unknown", "fallback": False})
            
            artifact_path = task_to_artifact_path.get(agent_role, "")
            artifact_quality = "NOT_APPLICABLE"
            if artifact_path:
                abs_path = os.path.abspath(artifact_path)
                if abs_path in validation_results:
                    artifact_quality = validation_results[abs_path]
                elif artifact_path in validation_results:
                    artifact_quality = validation_results[artifact_path]
                else:
                    artifact_quality = "VALID" if os.path.exists(artifact_path) else "MISSING"
                    
            tasks_metrics.append({
                "task_name": getattr(t_out, "name", None) or f"task_{i+1}",
                "agent_role": agent_role,
                "agent_key": agent_key,
                "model": resolved["model"],
                "fallback_event": resolved["fallback"],
                "runtime_seconds_estimate": int(avg_task_duration),
                "status": "success",
                "artifact_quality": artifact_quality
            })
            
        token_usage_raw = {}
        if crew_output and getattr(crew_output, "token_usage", None):
            try:
                token_usage_raw = {
                    "total_tokens": getattr(crew_output.token_usage, "total_tokens", 0),
                    "prompt_tokens": getattr(crew_output.token_usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(crew_output.token_usage, "completion_tokens", 0),
                    "successful_requests": getattr(crew_output.token_usage, "successful_requests", 0),
                }
            except Exception:
                try:
                    token_usage_raw = dict(crew_output.token_usage)
                except Exception:
                    pass
                    
        metrics = {
            "total_token_usage": token_usage_raw,
            "tasks": tasks_metrics,
            "total_runtime_seconds": int(total_runtime)
        }
        report.record_metrics(metrics)

        report.record_canonical_artifacts(ALL_CANONICAL_ARTIFACT_PATHS, validation_results)
        report.finish(STATUS_PASS)

    except ArtifactValidationError as e:
        report.record_canonical_artifacts(ALL_CANONICAL_ARTIFACT_PATHS)
        report.add_error(f"Artifact validation failed: {e}")
        # Build failure metrics
        metrics = {
            "total_token_usage": {},
            "tasks": [
                {
                    "task_name": "unknown",
                    "agent_role": "unknown",
                    "agent_key": "unknown",
                    "model": "unknown",
                    "fallback_event": False,
                    "runtime_seconds_estimate": 0,
                    "status": "failed",
                    "artifact_quality": "INVALID"
                }
            ],
            "total_runtime_seconds": 0
        }
        report.record_metrics(metrics)
        report.finish(STATUS_FAIL)
        _write_report(report, run_timestamp)
        raise

    except Exception as e:
        report.record_canonical_artifacts(ALL_CANONICAL_ARTIFACT_PATHS)
        report.add_error(str(e))
        # Build failure metrics
        metrics = {
            "total_token_usage": {},
            "tasks": [
                {
                    "task_name": "unknown",
                    "agent_role": "unknown",
                    "agent_key": "unknown",
                    "model": "unknown",
                    "fallback_event": False,
                    "runtime_seconds_estimate": 0,
                    "status": "failed",
                    "artifact_quality": "INVALID"
                }
            ],
            "total_runtime_seconds": 0
        }
        report.record_metrics(metrics)
        report.finish(STATUS_FAIL)
        _write_report(report, run_timestamp)
        raise Exception(f"An error occurred while running the crew: {e}")

    _write_report(report, run_timestamp)


def train():
    """
    Train the crew for a given number of iterations.
    """
    try:
        HochAgentSwarm().crew().train(
            n_iterations=int(sys.argv[1]),
            filename=sys.argv[2],
            inputs=_default_inputs(),
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        HochAgentSwarm().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")


def test():
    """
    Test the crew execution and returns the results.
    """
    try:
        HochAgentSwarm().crew().test(
            n_iterations=int(sys.argv[1]),
            eval_llm=sys.argv[2],
            inputs=_default_inputs(),
        )
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")


def run_with_trigger():
    """
    Run the crew with trigger payload.
    topic and current_year are extracted from the payload when present;
    deterministic defaults are used otherwise to prevent blank task interpolation.
    Validates artifacts after execution — raises on invalid output.
    Writes a run report to artifacts/crew_runs/<timestamp>/run_report.json.
    """
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": trigger_payload.get("topic", "Hoch Agent Swarm Antigravity integration"),
        "current_year": str(datetime.now().year),
        "antigravity_role": trigger_payload.get(
            "antigravity_role",
            "Agentic development cockpit, artifact reviewer, "
            "implementation planner, and IDE-level orchestrator.",
        ),
        "crewai_role": trigger_payload.get(
            "crewai_role",
            "Local bounded multi-agent runtime for deterministic "
            "Hoch Agent Swarm execution.",
        ),
        "integration_mode": trigger_payload.get(
            "integration_mode",
            "Antigravity plans and edits; CrewAI executes bounded local crews; "
            "artifacts are reviewed before promotion.",
        ),
    }

    run_timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    report = RunReport.start(
        workflow_name="hoch_agent_swarm",
        inputs_summary=_inputs_summary(inputs),
    )

    try:
        archived_pairs = _archive_existing_artifacts(run_timestamp)
        report.record_archived_artifacts(archived_pairs)

        result = HochAgentSwarm().crew().kickoff(inputs=inputs)

        validation_results = _run_validation()
        report.record_canonical_artifacts(ALL_CANONICAL_ARTIFACT_PATHS, validation_results)
        report.finish(STATUS_PASS)

    except ArtifactValidationError as e:
        report.record_canonical_artifacts(ALL_CANONICAL_ARTIFACT_PATHS)
        report.add_error(f"Artifact validation failed: {e}")
        report.finish(STATUS_FAIL)
        _write_report(report, run_timestamp)
        raise

    except Exception as e:
        report.record_canonical_artifacts(ALL_CANONICAL_ARTIFACT_PATHS)
        report.add_error(str(e))
        report.finish(STATUS_FAIL)
        _write_report(report, run_timestamp)
        raise Exception(f"An error occurred while running the crew with trigger: {e}")

    _write_report(report, run_timestamp)
    return result
