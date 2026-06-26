"""
tests/test_artifact_validation.py

Tests the artifact_validation module using:
- Known-good markdown fixtures (always runs, no live crew needed)
- Known-bad content fixtures (always runs)
- Real artifact files when they exist (auto-activated after a crew run)

These tests do NOT skip permanently — every test either:
  a) runs against an in-memory fixture, or
  b) runs against a real artifact and fails explicitly if the file is
     missing or invalid (not silently skipped).

Run with:
    uv run pytest tests/test_artifact_validation.py -v
"""

import os
import pytest

from hoch_agent_swarm.artifact_validation import (
    ArtifactValidationError,
    SECURITY_AUDIT_PATH,
    ANTIGRAVITY_PLAN_PATH,
    SECURITY_AUDIT_REQUIRED_HEADINGS,
    ANTIGRAVITY_PLAN_REQUIRED_HEADINGS,
    ValidationResult,
    validate_security_audit,
    validate_antigravity_plan,
    validate_all_artifacts,
    _check_garbage,
    _check_headings,
    _check_minimum_length,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_SECURITY_AUDIT = """\
# Security Audit Report

## Scope

This audit covers the assembled agent configurations for the Hoch Agent Swarm
crew running locally with Ollama llama3.1:8b.

## Agent Configuration Review

All seven agents have allow_delegation set to false and max_iter set to 3.
No agent is configured to spawn additional subagents dynamically.

## Tool Access Verification

Each agent operates within the tool access tier defined in the manifest:
- asset_mapper: read_only
- security_operator: admin_gated

## Secret Scrubbing Status

No environment variable values or API keys appear in any task output.
The Ollama API base URL is configuration only and does not expose credentials.

## Replay Protection Status

Each crew run is uniquely identified by timestamp. Run IDs are stored in
artifacts/crew_runs/ which is gitignored to prevent accidental exposure.

## Findings

No violations detected in this audit run. All agents respect their declared
capability boundaries and delegation restrictions.

## Verdict

PASS. The assembled crew configuration meets all security requirements
defined in the Hoch Agent Swarm manifest version 1.0.0.
"""

GOOD_ANTIGRAVITY_PLAN = """\
# Hoch Agent Swarm Antigravity Execution Plan

## Mission

The Hoch Agent Swarm integrates Google Antigravity as its agentic development
cockpit with CrewAI as the bounded local execution runtime.

## Inputs Reviewed

- topic: AI LLMs
- antigravity_role: Agentic development cockpit.
- crewai_role: Local bounded multi-agent runtime.
- integration_mode: Antigravity plans and edits; CrewAI executes.

## Crew Output Chain

Seven tasks execute sequentially with explicit context wiring.

## Security Audit Summary

The security audit confirmed all delegation bounds and tool access limits.

## Antigravity Integration Steps

Antigravity reads the project structure and plans implementation steps.
CrewAI executes the bounded local crew deterministically.

## Local-Only Constraints

All runs use Ollama at localhost with no external network calls permitted.

## Validation Checklist

- Both artifact files exist and are non-empty.
- No garbage patterns detected in either artifact.
- All required headings present in both artifacts.

## Next Actions

Review output and promote to Hoch Agent Swarm governance ledger.
"""

GARBAGE_CONTENT = """\
Here's a simplified version of the code with comments:

```python
import json
import random

executable_tasks = '''
[
    {"agent_name": "asset_identification_agent",
     "execution_time": random.uniform(1000,2000)}
]
'''
manifest = {"cef": evidence_file["audit_report"]}
print(json.dumps(manifest, indent=4))
```

Feel free to ask for any further refinement!
"""

MINIMAL_CONTENT = "too short"

MISSING_HEADINGS_CONTENT = """\
# Security Audit Report

This report is missing the Scope, Findings, and Verdict sections.
The content exists but the required structure is absent.
This should fail heading validation even though it has some content
and does not contain any garbage patterns from the model.
"""


# ---------------------------------------------------------------------------
# Unit tests: _check_garbage
# ---------------------------------------------------------------------------

class TestCheckGarbage:

    def test_detects_random_uniform(self):
        errors = _check_garbage("x = random.uniform(1, 2)", "test.md")
        assert any("random.uniform" in e for e in errors)

    def test_detects_fenced_python_block(self):
        errors = _check_garbage("```python\nprint('hello')\n```", "test.md")
        assert any("python" in e.lower() for e in errors)

    def test_detects_lambda(self):
        errors = _check_garbage("f = lambda x: x + 1", "test.md")
        assert any("lambda" in e for e in errors)

    def test_detects_python_import(self):
        errors = _check_garbage("import random", "test.md")
        assert any("import" in e for e in errors)

    def test_detects_json_fragment(self):
        errors = _check_garbage('"dependencies": [', "test.md")
        assert any("dependencies" in e for e in errors)

    def test_detects_llm_filler(self):
        errors = _check_garbage("Feel free to ask for any further refinement!", "test.md")
        assert any("filler" in e.lower() or "Feel free" in e for e in errors)

    def test_clean_markdown_no_errors(self):
        errors = _check_garbage("## Mission\n\nThe crew runs sequentially.", "test.md")
        assert errors == []


# ---------------------------------------------------------------------------
# Unit tests: _check_headings
# ---------------------------------------------------------------------------

class TestCheckHeadings:

    def test_all_headings_present(self):
        content = "\n".join(SECURITY_AUDIT_REQUIRED_HEADINGS)
        errors = _check_headings(content, "test.md", SECURITY_AUDIT_REQUIRED_HEADINGS)
        assert errors == []

    def test_missing_heading_detected(self):
        content = "# Security Audit Report\n## Scope\n"
        errors = _check_headings(content, "test.md", SECURITY_AUDIT_REQUIRED_HEADINGS)
        missing = [e for e in errors if "## Findings" in e]
        assert len(missing) >= 1

    def test_all_antigravity_headings_present(self):
        errors = _check_headings(
            GOOD_ANTIGRAVITY_PLAN, "test.md", ANTIGRAVITY_PLAN_REQUIRED_HEADINGS
        )
        assert errors == []


# ---------------------------------------------------------------------------
# Unit tests: _check_minimum_length
# ---------------------------------------------------------------------------

class TestCheckMinimumLength:

    def test_short_content_fails(self):
        errors = _check_minimum_length("hi", "test.md", min_chars=200)
        assert len(errors) == 1
        assert "too short" in errors[0].lower()

    def test_adequate_content_passes(self):
        errors = _check_minimum_length("x" * 300, "test.md", min_chars=200)
        assert errors == []


# ---------------------------------------------------------------------------
# Fixture-based validator tests (no live run required)
# ---------------------------------------------------------------------------

class TestValidateSecurityAuditFixture:
    """Tests validate_security_audit() against a temp file fixture."""

    def test_good_audit_passes(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(GOOD_SECURITY_AUDIT)
        result = validate_security_audit(path=str(audit_file))
        assert result.passed, f"Expected pass, got errors: {result.errors}"

    def test_garbage_audit_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(GARBAGE_CONTENT)
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed
        assert any("random.uniform" in e or "python" in e.lower() for e in result.errors)

    def test_missing_headings_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(MISSING_HEADINGS_CONTENT)
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed

    def test_empty_file_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text("   ")
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed

    def test_missing_file_fails(self, tmp_path):
        result = validate_security_audit(path=str(tmp_path / "nonexistent.md"))
        assert not result.passed
        assert any("missing" in e.lower() for e in result.errors)


class TestValidateAntigravityPlanFixture:
    """Tests validate_antigravity_plan() against a temp file fixture."""

    def test_good_plan_passes(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(GOOD_ANTIGRAVITY_PLAN)
        result = validate_antigravity_plan(path=str(plan_file))
        assert result.passed, f"Expected pass, got errors: {result.errors}"

    def test_garbage_plan_fails(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(GARBAGE_CONTENT)
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed

    def test_missing_headings_fails(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        # Has length but missing most required headings
        plan_file.write_text(
            "# Hoch Agent Swarm Antigravity Execution Plan\n\n"
            + "Some content but none of the required sections below.\n" * 20
        )
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed
        missing = [e for e in result.errors if "## Mission" in e]
        assert len(missing) >= 1

    def test_empty_file_fails(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text("")
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed

    def test_missing_file_fails(self, tmp_path):
        result = validate_antigravity_plan(path=str(tmp_path / "nonexistent.md"))
        assert not result.passed


class TestValidateAllArtifactsFixture:
    """Tests the aggregate validator with combined fixture files."""

    def test_both_good_passes(self, tmp_path, monkeypatch):
        audit_file = tmp_path / "security_audit_report.md"
        plan_file = tmp_path / "antigravity_execution_plan.md"
        audit_file.write_text(GOOD_SECURITY_AUDIT)
        plan_file.write_text(GOOD_ANTIGRAVITY_PLAN)

        monkeypatch.chdir(tmp_path)
        os.makedirs("artifacts/security_reviews", exist_ok=True)
        os.makedirs("artifacts/antigravity", exist_ok=True)
        (tmp_path / "artifacts/security_reviews/security_audit_report.md").write_text(
            GOOD_SECURITY_AUDIT
        )
        (tmp_path / "artifacts/antigravity/antigravity_execution_plan.md").write_text(
            GOOD_ANTIGRAVITY_PLAN
        )

        errors = validate_all_artifacts(strict=False)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_garbage_raises_in_strict_mode(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        os.makedirs("artifacts/security_reviews", exist_ok=True)
        os.makedirs("artifacts/antigravity", exist_ok=True)
        (tmp_path / "artifacts/security_reviews/security_audit_report.md").write_text(
            GARBAGE_CONTENT
        )
        (tmp_path / "artifacts/antigravity/antigravity_execution_plan.md").write_text(
            GARBAGE_CONTENT
        )

        with pytest.raises(ArtifactValidationError) as exc_info:
            validate_all_artifacts(strict=True)
        assert "ARTIFACT VALIDATION FAILED" in str(exc_info.value)

    def test_non_strict_returns_errors_not_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No artifact files created — both will fail
        errors = validate_all_artifacts(strict=False)
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# Real artifact tests (fail explicitly if files are missing, do NOT skip)
# ---------------------------------------------------------------------------

class TestRealArtifacts:
    """
    Validates the canonical artifact files in the repository.

    These tests FAIL (not skip) if the files are missing or invalid.
    Run `uv run run_crew` before this test class if files don't exist.
    """

    def test_security_audit_exists_and_is_valid(self):
        if not os.path.isfile(SECURITY_AUDIT_PATH):
            pytest.fail(
                f"MISSING: {SECURITY_AUDIT_PATH}\n"
                "Run `uv run run_crew` to generate this artifact before running tests."
            )
        result = validate_security_audit()
        assert result.passed, (
            f"Security audit artifact failed validation:\n"
            + "\n".join(f"  • {e}" for e in result.errors)
        )

    def test_antigravity_plan_exists_and_is_valid(self):
        if not os.path.isfile(ANTIGRAVITY_PLAN_PATH):
            pytest.fail(
                f"MISSING: {ANTIGRAVITY_PLAN_PATH}\n"
                "Run `uv run run_crew` to generate this artifact before running tests."
            )
        result = validate_antigravity_plan()
        assert result.passed, (
            f"Antigravity plan artifact failed validation:\n"
            + "\n".join(f"  • {e}" for e in result.errors)
        )
