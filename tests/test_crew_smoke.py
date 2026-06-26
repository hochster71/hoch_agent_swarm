"""
Smoke tests for Hoch Agent Swarm workflow integrity.

These tests verify:
1. The crew can be instantiated (7 agents, 7 tasks wired correctly).
2. Durable artifact output paths are configured on the right tasks.
3. Context dependencies are declared between tasks.
4. After a real run, artifact files exist, are non-empty, and do not
   contain garbage patterns produced by a poorly-prompted LLM.

Run with:
    uv run pytest tests/test_crew_smoke.py -v
"""

import os
import re
import pytest

from hoch_agent_swarm.crew import HochAgentSwarm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GARBAGE_PATTERNS = [
    r"random\.uniform",       # Python expression
    r"\blambda\b",            # Python keyword
    r'"dependencies"\s*:',    # JSON fragment
    r"class\s+\w+\(",         # Python class definition
    r"def\s+\w+\(",           # Python function definition
    r"import\s+\w+",          # Python import
    r"```python",             # Fenced Python code block
]

SECURITY_AUDIT_PATH = "artifacts/security_reviews/security_audit_report.md"
ANTIGRAVITY_PLAN_PATH = "artifacts/antigravity/antigravity_execution_plan.md"

ANTIGRAVITY_REQUIRED_HEADINGS = [
    "# Hoch Agent Swarm Antigravity Execution Plan",
    "## Mission",
    "## Inputs Reviewed",
    "## Crew Output Chain",
    "## Security Audit Summary",
    "## Antigravity Integration Steps",
    "## Local-Only Constraints",
    "## Validation Checklist",
    "## Next Actions",
]

SECURITY_REQUIRED_HEADINGS = [
    "# Security Audit Report",
    "## Scope",
    "## Findings",
    "## Verdict",
]


# ---------------------------------------------------------------------------
# Crew instantiation tests (no LLM call required)
# ---------------------------------------------------------------------------

class TestCrewInstantiation:
    """Tests that the crew object is structurally sound."""

    def setup_method(self):
        self.swarm = HochAgentSwarm()
        self.crew = self.swarm.crew()

    def test_crew_has_seven_agents(self):
        assert len(self.crew.agents) == 7, (
            f"Expected 7 agents, got {len(self.crew.agents)}"
        )

    def test_crew_has_seven_tasks(self):
        assert len(self.crew.tasks) == 7, (
            f"Expected 7 tasks, got {len(self.crew.tasks)}"
        )

    def test_expected_agent_roles_present(self):
        roles = [a.role for a in self.crew.agents]
        for expected in [
            "Swarm Asset Mapper",
            "Swarm Process Architect",
            "Swarm Agent Combinator",
            "Swarm Security Auditor",
            "Swarm Execution Scheduler",
            "Release Synthesis Director",
            "Antigravity Integration Operator",
        ]:
            assert any(expected in r for r in roles), (
                f"Agent role '{expected}' not found in crew. Found: {roles}"
            )

    def test_no_agent_allows_delegation(self):
        """All agents must have allow_delegation=False per the manifest."""
        for agent in self.crew.agents:
            assert agent.allow_delegation is False, (
                f"Agent '{agent.role}' has allow_delegation=True — forbidden by manifest"
            )

    def test_all_agents_have_max_iter(self):
        for agent in self.crew.agents:
            assert agent.max_iter is not None and agent.max_iter > 0, (
                f"Agent '{agent.role}' missing max_iter"
            )

    def test_security_audit_task_has_output_file(self):
        """audit_security_task must write a durable artifact."""
        # Match by expected output file path since description wording may vary
        audit_task = next(
            (
                t for t in self.crew.tasks
                if t.output_file and "security_reviews" in t.output_file
            ),
            None,
        )
        assert audit_task is not None, (
            "No task with output_file pointing to security_reviews/ found — "
            "audit_security_task is not durable"
        )

    def test_antigravity_task_has_output_file(self):
        """antigravity_integration_task must write to the canonical plan path."""
        ag_task = next(
            (
                t for t in self.crew.tasks
                if t.output_file and "antigravity_execution_plan" in t.output_file
            ),
            None,
        )
        assert ag_task is not None, (
            "No task with output_file pointing to antigravity_execution_plan found"
        )

    def test_tasks_have_context_wiring(self):
        """
        All tasks except the root (map_assets_task) must declare at least one
        context dependency so downstream outputs are formally passed through.
        """
        # map_assets_task is the root — it has no prior task to depend on
        ROOT_TASK_AGENT_ROLE = "Swarm Asset Mapper"

        non_root_tasks = [
            t for t in self.crew.tasks
            if not (t.agent and ROOT_TASK_AGENT_ROLE in (t.agent.role or ""))
        ]

        for task in non_root_tasks:
            assert task.context and len(task.context) > 0, (
                f"Task assigned to agent '{getattr(task.agent, 'role', 'unknown')}' "
                f"has no context= wiring. All non-root tasks must explicitly declare dependencies."
            )


# ---------------------------------------------------------------------------
# Artifact quality tests (run only when artifacts exist from a prior crew run)
# ---------------------------------------------------------------------------

def artifact_exists(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 0


@pytest.mark.skipif(
    not artifact_exists(SECURITY_AUDIT_PATH),
    reason=f"Artifact not yet generated: {SECURITY_AUDIT_PATH}",
)
class TestSecurityAuditArtifact:

    def setup_method(self):
        with open(SECURITY_AUDIT_PATH, "r") as f:
            self.content = f.read()

    def test_security_audit_is_non_empty(self):
        assert len(self.content.strip()) > 0

    def test_security_audit_has_required_headings(self):
        for heading in SECURITY_REQUIRED_HEADINGS:
            assert heading in self.content, (
                f"Required heading '{heading}' missing from security audit report"
            )

    def test_security_audit_no_garbage_patterns(self):
        for pattern in GARBAGE_PATTERNS:
            assert not re.search(pattern, self.content), (
                f"Garbage pattern '{pattern}' found in security audit report"
            )


@pytest.mark.skipif(
    not artifact_exists(ANTIGRAVITY_PLAN_PATH),
    reason=f"Artifact not yet generated: {ANTIGRAVITY_PLAN_PATH}",
)
class TestAntigravityPlanArtifact:

    def setup_method(self):
        with open(ANTIGRAVITY_PLAN_PATH, "r") as f:
            self.content = f.read()

    def test_antigravity_plan_is_non_empty(self):
        assert len(self.content.strip()) > 0

    def test_antigravity_plan_has_all_required_headings(self):
        for heading in ANTIGRAVITY_REQUIRED_HEADINGS:
            assert heading in self.content, (
                f"Required heading '{heading}' missing from Antigravity execution plan"
            )

    def test_antigravity_plan_no_garbage_patterns(self):
        for pattern in GARBAGE_PATTERNS:
            assert not re.search(pattern, self.content), (
                f"Garbage pattern '{pattern}' found in Antigravity execution plan"
            )
