#!/usr/bin/env python
import os
import shutil
import sys
import warnings

from datetime import datetime

from hoch_agent_swarm.crew import HochAgentSwarm
from hoch_agent_swarm.artifact_validation import (
    ArtifactValidationError,
    ANTIGRAVITY_PLAN_PATH,
    SECURITY_AUDIT_PATH,
    validate_all_artifacts,
)

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# ---------------------------------------------------------------------------
# Artifact archive helpers (Step 6: prevent silent canonical overwrite)
# ---------------------------------------------------------------------------

_ARCHIVE_DIR = "artifacts/crew_runs"

_CANONICAL_ARTIFACTS = [
    SECURITY_AUDIT_PATH,
    ANTIGRAVITY_PLAN_PATH,
]


def _archive_existing_artifacts(run_timestamp: str) -> None:
    """
    Before a crew run overwrites canonical artifact files, copy current
    versions into artifacts/crew_runs/<timestamp>/ so prior output is
    not silently lost.

    artifacts/crew_runs/ is gitignored, so archives are local-only.
    """
    archive_dir = os.path.join(_ARCHIVE_DIR, run_timestamp)
    archived = []

    for src_path in _CANONICAL_ARTIFACTS:
        if os.path.isfile(src_path) and os.path.getsize(src_path) > 0:
            os.makedirs(archive_dir, exist_ok=True)
            dest_name = os.path.basename(src_path)
            dest_path = os.path.join(archive_dir, dest_name)
            shutil.copy2(src_path, dest_path)
            archived.append(f"  archived: {src_path} → {dest_path}")

    if archived:
        print("\n[archive] Prior artifacts saved before overwrite:")
        for line in archived:
            print(line)


def _run_validation() -> None:
    """
    Run artifact validation after crew kickoff.
    Raises ArtifactValidationError on failure — crew run is not considered
    successful until all artifacts pass.
    """
    print("\n[validate] Running artifact validation...")
    try:
        validate_all_artifacts(strict=True)
        print("[validate] All artifacts passed validation.")
    except ArtifactValidationError:
        raise  # re-raise so the caller sees the full error


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
    Raises on invalid output — does not silently continue.
    """
    run_timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    _archive_existing_artifacts(run_timestamp)

    try:
        HochAgentSwarm().crew().kickoff(inputs=_default_inputs())
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

    _run_validation()


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
    """
    import json

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
    _archive_existing_artifacts(run_timestamp)

    try:
        result = HochAgentSwarm().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")

    _run_validation()
    return result
