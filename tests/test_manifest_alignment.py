"""
tests/test_manifest_alignment.py — Verify manifest/runtime alignment.

Compares:
  artifacts/agent_manifests/hoch_agent_swarm_manifest.yaml
against:
  src/hoch_agent_swarm/config/agents.yaml

Ensures the runtime agent configuration stays within the bounds
declared in the manifest and that the manifest is not aspirational
beyond what the runtime enforces.

Also verifies the complete durable artifact output_file configuration
in tasks.yaml matches what is declared in artifact_validation.py.

Run with:
    uv run pytest tests/test_manifest_alignment.py -v
"""

import os
import yaml
import pytest

from hoch_agent_swarm.artifact_validation import ALL_CANONICAL_ARTIFACT_PATHS


# ---------------------------------------------------------------------------
# Fixtures — load YAML once per session
# ---------------------------------------------------------------------------

MANIFEST_PATH = "artifacts/agent_manifests/hoch_agent_swarm_manifest.yaml"
AGENTS_YAML_PATH = "src/hoch_agent_swarm/config/agents.yaml"
TASKS_YAML_PATH = "src/hoch_agent_swarm/config/tasks.yaml"


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert os.path.isfile(MANIFEST_PATH), f"Manifest not found: {MANIFEST_PATH}"
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def agents_yaml() -> dict:
    assert os.path.isfile(AGENTS_YAML_PATH), f"agents.yaml not found: {AGENTS_YAML_PATH}"
    with open(AGENTS_YAML_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def tasks_yaml() -> dict:
    assert os.path.isfile(TASKS_YAML_PATH), f"tasks.yaml not found: {TASKS_YAML_PATH}"
    with open(TASKS_YAML_PATH) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Manifest structure tests
# ---------------------------------------------------------------------------

class TestManifestStructure:

    def test_manifest_has_version(self, manifest):
        assert "version" in manifest, "Manifest must declare a version"
        assert manifest["version"], "Manifest version must be non-empty"

    def test_manifest_has_constraints(self, manifest):
        assert "constraints" in manifest, "Manifest must declare constraints"

    def test_manifest_has_archetypes(self, manifest):
        assert "archetypes" in manifest, "Manifest must declare archetypes"
        assert len(manifest["archetypes"]) > 0

    def test_manifest_archetype_count_within_max(self, manifest):
        max_archetypes = manifest["constraints"]["max_archetypes"]
        actual_archetypes = len(manifest["archetypes"])
        assert actual_archetypes <= max_archetypes, (
            f"Manifest declares {actual_archetypes} archetypes "
            f"but max_archetypes is {max_archetypes}"
        )

    def test_manifest_has_human_approval_policy(self, manifest):
        assert "human_approval_required_for" in manifest


# ---------------------------------------------------------------------------
# Runtime agent bounds — every agent must have required safety limits
# ---------------------------------------------------------------------------

class TestRuntimeAgentBounds:

    def test_all_agents_have_max_iter(self, agents_yaml):
        for agent_key, agent_cfg in agents_yaml.items():
            assert "max_iter" in agent_cfg, (
                f"Agent '{agent_key}' is missing max_iter"
            )
            assert isinstance(agent_cfg["max_iter"], int), (
                f"Agent '{agent_key}' max_iter must be an integer"
            )
            assert agent_cfg["max_iter"] > 0, (
                f"Agent '{agent_key}' max_iter must be positive"
            )

    def test_all_agents_have_max_execution_time(self, agents_yaml):
        for agent_key, agent_cfg in agents_yaml.items():
            assert "max_execution_time" in agent_cfg, (
                f"Agent '{agent_key}' is missing max_execution_time"
            )
            assert isinstance(agent_cfg["max_execution_time"], int), (
                f"Agent '{agent_key}' max_execution_time must be an integer"
            )
            assert agent_cfg["max_execution_time"] > 0, (
                f"Agent '{agent_key}' max_execution_time must be positive"
            )

    def test_all_agents_have_allow_delegation(self, agents_yaml):
        for agent_key, agent_cfg in agents_yaml.items():
            assert "allow_delegation" in agent_cfg, (
                f"Agent '{agent_key}' is missing allow_delegation"
            )

    def test_no_agent_allows_delegation(self, agents_yaml):
        for agent_key, agent_cfg in agents_yaml.items():
            assert agent_cfg.get("allow_delegation") is False, (
                f"Agent '{agent_key}' has allow_delegation != false. "
                "Delegation is forbidden per manifest policy."
            )

    def test_agent_count_within_manifest_spawn_limit(self, agents_yaml, manifest):
        max_spawned = manifest["constraints"]["max_spawned_agents_per_run"]
        actual_count = len(agents_yaml)
        assert actual_count <= max_spawned, (
            f"Runtime defines {actual_count} agents but manifest "
            f"max_spawned_agents_per_run is {max_spawned}"
        )


# ---------------------------------------------------------------------------
# Manifest archetype ↔ runtime agent key alignment
# ---------------------------------------------------------------------------

class TestManifestRuntimeAlignment:

    def test_all_manifest_archetypes_have_runtime_config(self, manifest, agents_yaml):
        """Every archetype in the manifest must have a corresponding agents.yaml key."""
        manifest_archetypes = set(manifest["archetypes"].keys())
        runtime_agents = set(agents_yaml.keys())
        missing = manifest_archetypes - runtime_agents
        assert not missing, (
            f"Manifest archetypes not configured in agents.yaml: {missing}\n"
            "Either add the runtime config or remove the archetype from the manifest."
        )

    def test_no_runtime_agents_missing_from_manifest(self, manifest, agents_yaml):
        """Every runtime agent must be declared as an archetype in the manifest."""
        manifest_archetypes = set(manifest["archetypes"].keys())
        runtime_agents = set(agents_yaml.keys())
        undeclared = runtime_agents - manifest_archetypes
        assert not undeclared, (
            f"Runtime agents not declared in manifest archetypes: {undeclared}\n"
            "Add them to the manifest or remove them from agents.yaml."
        )

    def test_max_iter_within_reasonable_bound(self, agents_yaml):
        """max_iter=3 is the current standard; warn if any agent exceeds 10."""
        for agent_key, agent_cfg in agents_yaml.items():
            max_iter = agent_cfg.get("max_iter", 0)
            assert max_iter <= 10, (
                f"Agent '{agent_key}' max_iter={max_iter} is unusually high. "
                "Review the bound before increasing beyond 10."
            )

    def test_max_execution_time_within_reasonable_bound(self, agents_yaml):
        """max_execution_time=180 is the current standard; warn if any exceeds 600."""
        for agent_key, agent_cfg in agents_yaml.items():
            max_time = agent_cfg.get("max_execution_time", 0)
            assert max_time <= 600, (
                f"Agent '{agent_key}' max_execution_time={max_time}s is unusually high. "
                "Review before allowing more than 10 minutes per agent."
            )


# ---------------------------------------------------------------------------
# Task output_file configuration alignment
# ---------------------------------------------------------------------------

class TestTaskOutputFiles:

    EXPECTED_OUTPUT_FILES = {
        "map_assets_task": "artifacts/research/asset_map.md",
        "audit_security_task": "artifacts/security_reviews/security_audit_report.md",
        "plan_execution_task": "artifacts/reports/execution_plan.md",
        "direct_synthesis_task": "artifacts/reports/release_packet.md",
        "antigravity_integration_task": "artifacts/antigravity/antigravity_execution_plan.md",
    }

    def test_durable_tasks_have_output_file(self, tasks_yaml):
        for task_key, expected_path in self.EXPECTED_OUTPUT_FILES.items():
            assert task_key in tasks_yaml, f"Task '{task_key}' not found in tasks.yaml"
            actual = tasks_yaml[task_key].get("output_file")
            assert actual == expected_path, (
                f"Task '{task_key}': expected output_file='{expected_path}', "
                f"got '{actual}'"
            )

    def test_all_terminal_artifacts_in_canonical_list(self):
        """
        The two terminal artifact paths must always be in ALL_CANONICAL_ARTIFACT_PATHS.
        This test fails if artifact_validation.py is edited to drop a terminal path.
        """
        required_terminal = {
            "artifacts/security_reviews/security_audit_report.md",
            "artifacts/antigravity/antigravity_execution_plan.md",
        }
        canonical_set = set(ALL_CANONICAL_ARTIFACT_PATHS)
        missing = required_terminal - canonical_set
        assert not missing, (
            f"Terminal artifacts missing from ALL_CANONICAL_ARTIFACT_PATHS: {missing}"
        )

    def test_all_intermediate_artifacts_in_canonical_list(self):
        intermediate = {
            "artifacts/research/asset_map.md",
            "artifacts/reports/execution_plan.md",
            "artifacts/reports/release_packet.md",
        }
        canonical_set = set(ALL_CANONICAL_ARTIFACT_PATHS)
        missing = intermediate - canonical_set
        assert not missing, (
            f"Intermediate artifacts missing from ALL_CANONICAL_ARTIFACT_PATHS: {missing}"
        )

    def test_canonical_list_has_no_duplicates(self):
        assert len(ALL_CANONICAL_ARTIFACT_PATHS) == len(set(ALL_CANONICAL_ARTIFACT_PATHS)), (
            "ALL_CANONICAL_ARTIFACT_PATHS contains duplicate entries"
        )
