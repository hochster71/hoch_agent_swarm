#!/usr/bin/env python
import sys
import warnings

from datetime import datetime

from hoch_agent_swarm.crew import HochAgentSwarm

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    inputs = {
        'topic': 'AI LLMs',
        'current_year': str(datetime.now().year),
        'antigravity_role': 'Agentic development cockpit, artifact reviewer, implementation planner, and IDE-level orchestrator.',
        'crewai_role': 'Local bounded multi-agent runtime for deterministic Hoch Agent Swarm execution.',
        'integration_mode': 'Antigravity plans and edits; CrewAI executes bounded local crews; artifacts are reviewed before promotion.'
    }

    try:
        HochAgentSwarm().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year),
        'antigravity_role': 'Agentic development cockpit, artifact reviewer, implementation planner, and IDE-level orchestrator.',
        'crewai_role': 'Local bounded multi-agent runtime for deterministic Hoch Agent Swarm execution.',
        'integration_mode': 'Antigravity plans and edits; CrewAI executes bounded local crews; artifacts are reviewed before promotion.'
    }
    try:
        HochAgentSwarm().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

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
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year),
        'antigravity_role': 'Agentic development cockpit, artifact reviewer, implementation planner, and IDE-level orchestrator.',
        'crewai_role': 'Local bounded multi-agent runtime for deterministic Hoch Agent Swarm execution.',
        'integration_mode': 'Antigravity plans and edits; CrewAI executes bounded local crews; artifacts are reviewed before promotion.'
    }

    try:
        HochAgentSwarm().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    topic and current_year are extracted from the payload when present;
    deterministic defaults are used otherwise to prevent blank task interpolation.
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
            "Agentic development cockpit, artifact reviewer, implementation planner, and IDE-level orchestrator."
        ),
        "crewai_role": trigger_payload.get(
            "crewai_role",
            "Local bounded multi-agent runtime for deterministic Hoch Agent Swarm execution."
        ),
        "integration_mode": trigger_payload.get(
            "integration_mode",
            "Antigravity plans and edits; CrewAI executes bounded local crews; artifacts are reviewed before promotion."
        ),
    }

    try:
        result = HochAgentSwarm().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
