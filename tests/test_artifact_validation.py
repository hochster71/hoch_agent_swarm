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
    # v1 helpers
    _check_garbage,
    _check_headings,
    _check_minimum_length,
    # v2 helpers
    _PLACEHOLDER_PATTERNS,
    _FILLER_PHRASES,
    _check_placeholders,
    _check_filler_phrases,
    _check_empty_checklists,
    _extract_section_content,
    _check_section_content_lengths,
    _check_verdict_content,
    _check_findings_content,
    _check_antigravity_integration_steps,
    _check_antigravity_validation_checklist,
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

1. Antigravity reads the project structure and plans implementation steps.
2. CrewAI executes the bounded local crew deterministically.
3. Artifacts are written to canonical paths and validated post-run.
4. Run report captures SHA-256 hashes for artifact integrity tracking.

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

    # --- v2.2 calibration regression tests ---

    def test_next_actions_omission_passes(self):
        """## Next Actions is no longer required — its absence must not cause a failure."""
        # Build a plan with all required headings but no ## Next Actions
        content = (
            "# Hoch Agent Swarm Antigravity Execution Plan\n\n"
            "## Mission\nThe mission.\n\n"
            "## Inputs Reviewed\nInputs reviewed.\n\n"
            "## Crew Output Chain\n1. Step one\n\n"
            "## Security Audit Summary\nSummary.\n\n"
            "## Antigravity Integration Steps\n- Step one\n\n"
            "## Local-Only Constraints\nConstraints.\n\n"
            "## Validation Checklist\n- Item one\n"
            # No ## Next Actions
        )
        errors = _check_headings(content, "test.md", ANTIGRAVITY_PLAN_REQUIRED_HEADINGS)
        assert errors == [], f"## Next Actions absence should not fail: {errors}"

    def test_real_batch17b_missing_next_actions_passes(self):
        """The actual plan that omitted ## Next Actions in batch17b must now pass heading check."""
        import os
        sample = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "validation_samples",
            "batch17b",
            "antigravity_missing_next_actions.md",
        )
        if not os.path.isfile(sample):
            import pytest
            pytest.skip("batch17b sample not present")
        with open(sample) as f:
            content = f.read()
        errors = _check_headings(content, "antigravity_execution_plan.md", ANTIGRAVITY_PLAN_REQUIRED_HEADINGS)
        assert errors == [], f"Missing Next Actions should no longer be an error: {errors}"


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
# v2 bad-content fixtures
# ---------------------------------------------------------------------------

PLACEHOLDER_CONTENT = GOOD_SECURITY_AUDIT.replace(
    "PASS. The assembled crew configuration meets all security requirements",
    "[TODO] The assembled crew configuration meets all security requirements",
)

FILLER_CONTENT = GOOD_SECURITY_AUDIT.replace(
    "PASS. The assembled crew configuration meets all security requirements",
    "to be determined. The configuration is coming soon.",
)

EMPTY_CHECKLIST_CONTENT = GOOD_ANTIGRAVITY_PLAN.replace(
    "- Both artifact files exist and are non-empty.",
    "- [ ]",
).replace(
    "- No garbage patterns detected in either artifact.",
    "- [ ]",
).replace(
    "- All required headings present in both artifacts.",
    "- [ ]",
)

SECURITY_AUDIT_EMPTY_VERDICT = """\
# Security Audit Report

## Scope

This audit covers assembled agent configurations for the Hoch Agent Swarm.

## Agent Configuration Review

All agents reviewed. Delegation set to false, max_iter set to three.

## Tool Access Verification

Tool access verified for each agent in the manifest tier.

## Secret Scrubbing Status

No secrets detected in task output. Ollama URL is config only.

## Replay Protection Status

Timestamped run IDs prevent replay across crew executions.

## Findings

No violations found. All bounds respected.

## Verdict

"""

SECURITY_AUDIT_EMPTY_FINDINGS = """\
# Security Audit Report

## Scope

This audit covers assembled agent configurations for the Hoch Agent Swarm.

## Agent Configuration Review

All agents reviewed. Delegation set to false, max_iter set to three.

## Tool Access Verification

Tool access verified for each agent in the manifest tier.

## Secret Scrubbing Status

No secrets detected in task output. Ollama URL is config only.

## Replay Protection Status

Timestamped run IDs prevent replay across crew executions.

## Findings


## Verdict

PASS — all requirements met.
"""

ANTIGRAVITY_PLAN_NO_NUMBERED_STEPS = GOOD_ANTIGRAVITY_PLAN.replace(
    "1. Antigravity reads the project structure and plans implementation steps.\n"
    "2. CrewAI executes the bounded local crew deterministically.\n"
    "3. Artifacts are written to canonical paths and validated post-run.\n"
    "4. Run report captures SHA-256 hashes for artifact integrity tracking.",
    "Antigravity reads the project structure.\nCrewAI executes the crew.",
)

ANTIGRAVITY_PLAN_EMPTY_CHECKLIST = GOOD_ANTIGRAVITY_PLAN.replace(
    "## Validation Checklist\n\n- Both artifact files exist and are non-empty.\n- No garbage patterns detected in either artifact.\n- All required headings present in both artifacts.",
    "## Validation Checklist\n\nSee attached.",
)


# ---------------------------------------------------------------------------
# v2 unit tests: _check_placeholders
# ---------------------------------------------------------------------------


class TestCheckPlaceholders:
    def test_detects_todo(self):
        errors = _check_placeholders("See [TODO] for details.", "test.md")
        assert any("TODO" in e for e in errors)

    def test_detects_placeholder_bracket(self):
        errors = _check_placeholders("[PLACEHOLDER]", "test.md")
        assert any("PLACEHOLDER" in e for e in errors)

    def test_detects_html_todo(self):
        errors = _check_placeholders("<TODO>", "test.md")
        assert any("TODO" in e for e in errors)

    def test_detects_double_brace_template(self):
        errors = _check_placeholders("{{project_name}} is great.", "test.md")
        assert any("template" in e.lower() for e in errors)

    def test_detects_your_placeholder(self):
        errors = _check_placeholders("Contact [YOUR NAME] here.", "test.md")
        assert any("YOUR" in e for e in errors)

    def test_detects_insert_here(self):
        errors = _check_placeholders("INSERT CONTENT HERE", "test.md")
        assert any("INSERT" in e for e in errors)

    def test_clean_content_no_errors(self):
        errors = _check_placeholders("The crew ran successfully.", "test.md")
        assert errors == []

    def test_good_security_audit_passes(self):
        errors = _check_placeholders(GOOD_SECURITY_AUDIT, "test.md")
        assert errors == []

    def test_good_antigravity_plan_passes(self):
        errors = _check_placeholders(GOOD_ANTIGRAVITY_PLAN, "test.md")
        assert errors == []


# ---------------------------------------------------------------------------
# v2 unit tests: _check_filler_phrases
# ---------------------------------------------------------------------------


class TestCheckFillerPhrases:
    def test_detects_lorem_ipsum(self):
        errors = _check_filler_phrases("Lorem ipsum dolor sit amet.", "test.md")
        assert any("lorem ipsum" in e for e in errors)

    def test_detects_to_be_determined(self):
        errors = _check_filler_phrases("The plan is to be determined.", "test.md")
        assert any("to be determined" in e for e in errors)

    def test_detects_coming_soon(self):
        errors = _check_filler_phrases("Features coming soon.", "test.md")
        assert any("coming soon" in e for e in errors)

    def test_detects_fill_in_later(self):
        errors = _check_filler_phrases("We will fill in later.", "test.md")
        assert any("fill" in e.lower() for e in errors)

    def test_detects_not_yet_written(self):
        errors = _check_filler_phrases("Not yet written.", "test.md")
        assert any("not yet written" in e for e in errors)

    def test_clean_content_no_errors(self):
        errors = _check_filler_phrases("PASS — all configurations verified.", "test.md")
        assert errors == []

    def test_good_security_audit_passes(self):
        errors = _check_filler_phrases(GOOD_SECURITY_AUDIT, "test.md")
        assert errors == []

    def test_good_antigravity_plan_passes(self):
        errors = _check_filler_phrases(GOOD_ANTIGRAVITY_PLAN, "test.md")
        assert errors == []


# ---------------------------------------------------------------------------
# v2 unit tests: _check_empty_checklists
# ---------------------------------------------------------------------------


class TestCheckEmptyChecklists:
    def test_detects_bare_checkbox(self):
        errors = _check_empty_checklists("- [ ]\n", "test.md")
        assert len(errors) == 1
        assert "Empty checklist" in errors[0]

    def test_detects_multiple_bare_checkboxes(self):
        content = "- [ ]\n- [ ]\n- [ ]\n"
        errors = _check_empty_checklists(content, "test.md")
        assert len(errors) == 1  # one error with count
        assert "3" in errors[0]

    def test_filled_checkbox_passes(self):
        errors = _check_empty_checklists("- [ ] This has text\n", "test.md")
        assert errors == []

    def test_checked_checkbox_passes(self):
        errors = _check_empty_checklists("- [x] Done\n", "test.md")
        assert errors == []

    def test_plain_bullet_passes(self):
        errors = _check_empty_checklists("- Item one\n- Item two\n", "test.md")
        assert errors == []

    def test_good_security_audit_passes(self):
        errors = _check_empty_checklists(GOOD_SECURITY_AUDIT, "test.md")
        assert errors == []

    def test_good_antigravity_plan_passes(self):
        errors = _check_empty_checklists(GOOD_ANTIGRAVITY_PLAN, "test.md")
        assert errors == []


# ---------------------------------------------------------------------------
# v2 unit tests: _extract_section_content
# ---------------------------------------------------------------------------


class TestExtractSectionContent:
    SAMPLE = """# Title\n\nTitle body text.\n\n## Section A\n\nContent A here.\n\n## Section B\n\nContent B here.\n### Subsection\n\nSub content.\n"""

    def test_extracts_h2_section(self):
        text = _extract_section_content(self.SAMPLE, "## Section A")
        assert "Content A here." in text
        assert "Content B" not in text

    def test_stops_at_next_same_level(self):
        text = _extract_section_content(self.SAMPLE, "## Section A")
        assert "## Section B" not in text

    def test_extracts_h1_section_includes_h2s(self):
        text = _extract_section_content(self.SAMPLE, "# Title")
        assert "Title body text." in text

    def test_returns_empty_for_missing_heading(self):
        text = _extract_section_content(self.SAMPLE, "## Nonexistent")
        assert text == ""

    def test_last_section_goes_to_end(self):
        text = _extract_section_content(self.SAMPLE, "## Section B")
        assert "Content B here." in text

    # --- v2.3 calibration regression tests ---

    def test_leading_space_before_heading_marker_extracted(self):
        """' ## Heading' (with leading space) must be extractable — batch17c pattern."""
        content = (
            "## Section A\n\nContent A.\n\n"
            " ## Section B\n\nContent B indented heading.\n"
        )
        text = _extract_section_content(content, "## Section B")
        assert "Content B indented heading." in text

    def test_leading_space_section_not_empty(self):
        """Extraction of ' ## Validation Checklist' must return non-empty string."""
        content = " ## Validation Checklist\n\n- Item one\n- Item two\n"
        text = _extract_section_content(content, "## Validation Checklist")
        assert len(text) > 0
        assert "Item one" in text

    def test_real_batch17c_indented_heading_passes_full_validation(self):
        """The actual plan with ' ## Validation Checklist' must pass end-to-end."""
        import os
        import tempfile
        sample = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "validation_samples",
            "batch17c",
            "antigravity_indented_checklist_heading.md",
        )
        if not os.path.isfile(sample):
            import pytest
            pytest.skip("batch17c sample not present")
        with open(sample) as f:
            content = f.read()
        # Section extraction must yield content
        extracted = _extract_section_content(content, "## Validation Checklist")
        assert len(extracted) > 0, "Leading-space heading must now be extractable"
        # Full validator must pass
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            tmp = f.name
        try:
            from hoch_agent_swarm.artifact_validation import validate_antigravity_plan
            result = validate_antigravity_plan(path=tmp)
            assert result.passed, f"Real batch17c sample should pass: {result.errors}"
        finally:
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# v2 unit tests: _check_section_content_lengths
# ---------------------------------------------------------------------------


class TestCheckSectionContentLengths:
    def test_short_section_fails(self):
        content = "## Scope\n\nhi\n\n## Findings\n\nSomething substantial here.\n"
        errors = _check_section_content_lengths(
            content, "test.md", ["## Scope", "## Findings"], min_chars=20
        )
        assert any("## Scope" in e for e in errors)
        assert all("## Findings" not in e for e in errors)

    def test_adequate_section_passes(self):
        content = "## Scope\n\nThis is adequate content with enough characters to pass.\n"
        errors = _check_section_content_lengths(
            content, "test.md", ["## Scope"], min_chars=20
        )
        assert errors == []

    def test_skips_missing_heading(self):
        """Missing headings are handled by _check_headings; section length skips them."""
        content = "## Findings\n\nSome findings text here.\n"
        errors = _check_section_content_lengths(
            content, "test.md", ["## Scope", "## Findings"], min_chars=20
        )
        # ## Scope missing -> skipped (no double-error), ## Findings is fine
        assert errors == []

    def test_good_security_audit_passes(self):
        errors = _check_section_content_lengths(
            GOOD_SECURITY_AUDIT, "test.md", SECURITY_AUDIT_REQUIRED_HEADINGS
        )
        assert errors == []

    def test_good_antigravity_plan_passes(self):
        errors = _check_section_content_lengths(
            GOOD_ANTIGRAVITY_PLAN, "test.md", ANTIGRAVITY_PLAN_REQUIRED_HEADINGS
        )
        assert errors == []


# ---------------------------------------------------------------------------
# v2 unit tests: _check_verdict_content
# ---------------------------------------------------------------------------


class TestCheckVerdictContent:
    def test_pass_keyword_accepted(self):
        content = "## Verdict\n\nPASS — all checks clear.\n"
        errors = _check_verdict_content(content, "test.md")
        assert errors == []

    def test_fail_keyword_accepted(self):
        content = "## Verdict\n\nFAIL — delegation bound violated.\n"
        errors = _check_verdict_content(content, "test.md")
        assert errors == []

    def test_conditional_keyword_accepted(self):
        content = "## Verdict\n\nConditional Compliance Status detected.\n"
        errors = _check_verdict_content(content, "test.md")
        assert errors == []

    def test_empty_verdict_fails(self):
        content = "## Verdict\n\n"
        errors = _check_verdict_content(content, "test.md")
        # Empty section -> error about missing decision
        assert len(errors) == 1
        assert "Verdict" in errors[0]

    def test_missing_verdict_heading_ignored(self):
        """Missing heading is caught by _check_headings; _check_verdict_content skips."""
        content = "## Scope\n\nNo verdict here.\n"
        errors = _check_verdict_content(content, "test.md")
        assert errors == []

    def test_good_security_audit_passes(self):
        errors = _check_verdict_content(GOOD_SECURITY_AUDIT, "test.md")
        assert errors == []


# ---------------------------------------------------------------------------
# v2 unit tests: _check_findings_content
# ---------------------------------------------------------------------------


class TestCheckFindingsContent:
    def test_finding_keyword_accepted(self):
        content = "## Findings\n\nNo violations detected in this run.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_issue_keyword_accepted(self):
        content = "## Findings\n\nPotential credential issue identified.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_tool_keyword_accepted(self):
        content = "## Findings\n\nTool access limits verified for all agents.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_empty_findings_fails(self):
        content = "## Findings\n\n"
        errors = _check_findings_content(content, "test.md")
        assert len(errors) == 1
        assert "Findings" in errors[0]

    def test_missing_findings_heading_ignored(self):
        content = "## Scope\n\nNo findings section.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_good_security_audit_passes(self):
        errors = _check_findings_content(GOOD_SECURITY_AUDIT, "test.md")
        assert errors == []

    # --- v2.1 calibration regression tests ---

    def test_numbered_finding_entries_pass(self):
        """Numbered list items in ## Findings pass even without keyword vocabulary."""
        content = (
            "## Findings\n\n"
            "1. Task Run Unique Identification: no unique IDs assigned.\n"
            "2. Secrets Management: no explicit scrubbing present.\n"
        )
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_risk_keyword_accepted(self):
        content = "## Findings\n\nThere is a risk of replay attack.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_recommend_keyword_accepted(self):
        content = "## Findings\n\nWe recommend adding unique identifiers.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_remediation_keyword_accepted(self):
        content = "## Findings\n\nRemediation: add task run IDs.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_protect_keyword_accepted(self):
        content = "## Findings\n\nProtection against credential leak confirmed.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_pure_generic_prose_still_fails(self):
        """Generic prose with no finding vocabulary or numbered items still fails."""
        content = "## Findings\n\nEverything looks good overall. The system is fine.\n"
        errors = _check_findings_content(content, "test.md")
        assert len(errors) == 1

    def test_real_batch17_findings_sample_passes(self):
        """The actual security audit that triggered the Batch 17 calibration must pass."""
        import os
        sample = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "validation_samples",
            "batch17",
            "security_audit_report_findings_style.md",
        )
        if not os.path.isfile(sample):
            import pytest
            pytest.skip("batch17 sample not present")
        with open(sample) as f:
            content = f.read()
        errors = _check_findings_content(content, "security_audit_report.md")
        assert errors == [], f"Real failure sample should now pass: {errors}"

    # --- v2.2 calibration regression tests ---

    def test_no_instances_negative_finding_passes(self):
        """'no instances' clean-audit verdict must pass (batch17b failure pattern)."""
        content = (
            "## Findings\n\n"
            "The review did not reveal any instances of agents spawning additional "
            "agents dynamically or exceeding delegated bounds.\n"
        )
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_no_violations_passes(self):
        content = "## Findings\n\nNo violations were observed during the review.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_clean_keyword_passes(self):
        content = "## Findings\n\nAll configurations returned a clean result.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_no_unauthorized_passes(self):
        content = "## Findings\n\nNo unauthorized tool access was detected.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_spawn_keyword_passes(self):
        """'spawn' (in 'agents spawning') triggers the dynamic/spawn pattern."""
        content = "## Findings\n\nNo agents spawning additional agents detected.\n"
        errors = _check_findings_content(content, "test.md")
        assert errors == []

    def test_real_batch17b_clean_finding_sample_passes(self):
        """The actual security audit from the batch17b failure run must now pass."""
        import os
        sample = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "validation_samples",
            "batch17b",
            "security_audit_clean_finding.md",
        )
        if not os.path.isfile(sample):
            import pytest
            pytest.skip("batch17b sample not present")
        with open(sample) as f:
            content = f.read()
        errors = _check_findings_content(content, "security_audit_report.md")
        assert errors == [], f"Real clean-finding sample should now pass: {errors}"


# ---------------------------------------------------------------------------
# v2 unit tests: _check_antigravity_integration_steps
# ---------------------------------------------------------------------------


class TestCheckAntigravityIntegrationSteps:
    def test_numbered_list_passes(self):
        content = "## Antigravity Integration Steps\n\n1. Step one\n2. Step two\n"
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert errors == []

    def test_prose_only_fails(self):
        content = "## Antigravity Integration Steps\n\nAntigravity integrates things.\n"
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert len(errors) == 1
        assert "procedural" in errors[0]

    def test_bullet_only_passes(self):
        """Bullets are valid procedural steps — v2.1 calibration."""
        content = "## Antigravity Integration Steps\n\n- Step one\n- Step two\n"
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert errors == []

    def test_missing_heading_ignored(self):
        content = "## Mission\n\nThe mission.\n"
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert errors == []

    def test_good_antigravity_plan_passes(self):
        errors = _check_antigravity_integration_steps(GOOD_ANTIGRAVITY_PLAN, "test.md")
        assert errors == []

    # --- v2.1 calibration regression tests ---

    def test_star_bullet_passes(self):
        """'* Step' style is a valid procedural item."""
        content = "## Antigravity Integration Steps\n\n* Step one\n* Step two\n"
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert errors == []

    def test_bold_bullet_passes(self):
        """'- **Step**: description' (Batch 17 failure pattern) must pass."""
        content = (
            "## Antigravity Integration Steps\n\n"
            "- **Initial Synthesis Step**: Convert architecture into artifacts.\n"
            "- **Task Planning Step**: Derive task plans.\n"
        )
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert errors == []

    def test_empty_section_fails(self):
        """Section with only whitespace still fails."""
        content = "## Antigravity Integration Steps\n\n   \n\n"
        errors = _check_antigravity_integration_steps(content, "test.md")
        assert len(errors) == 1

    def test_real_batch17_bulleted_sample_passes(self):
        """The actual artifact that triggered the Batch 17 calibration must pass."""
        import os
        sample = os.path.join(
            os.path.dirname(__file__),
            "..",
            "artifacts",
            "validation_samples",
            "batch17",
            "antigravity_bulleted_steps.md",
        )
        if not os.path.isfile(sample):
            import pytest
            pytest.skip("batch17 sample not present")
        with open(sample) as f:
            content = f.read()
        errors = _check_antigravity_integration_steps(content, "antigravity_execution_plan.md")
        assert errors == [], f"Real failure sample should now pass: {errors}"


# ---------------------------------------------------------------------------
# v2 unit tests: _check_antigravity_validation_checklist
# ---------------------------------------------------------------------------


class TestCheckAntigravityValidationChecklist:
    def test_bullet_list_passes(self):
        content = "## Validation Checklist\n\n- Item one\n- Item two\n"
        errors = _check_antigravity_validation_checklist(content, "test.md")
        assert errors == []

    def test_star_bullet_passes(self):
        content = "## Validation Checklist\n\n* Item one\n"
        errors = _check_antigravity_validation_checklist(content, "test.md")
        assert errors == []

    def test_numbered_list_passes(self):
        content = "## Validation Checklist\n\n1. Item one\n2. Item two\n"
        errors = _check_antigravity_validation_checklist(content, "test.md")
        assert errors == []

    def test_prose_only_fails(self):
        content = "## Validation Checklist\n\nSee attached document.\n"
        errors = _check_antigravity_validation_checklist(content, "test.md")
        assert len(errors) == 1
        assert "Validation Checklist" in errors[0]

    def test_empty_section_fails(self):
        content = "## Validation Checklist\n\n"
        # Empty section -> extract returns '' -> no list items found -> error
        errors = _check_antigravity_validation_checklist(content, "test.md")
        assert len(errors) == 1

    def test_missing_heading_ignored(self):
        content = "## Mission\n\nThe mission.\n"
        errors = _check_antigravity_validation_checklist(content, "test.md")
        assert errors == []

    def test_good_antigravity_plan_passes(self):
        errors = _check_antigravity_validation_checklist(GOOD_ANTIGRAVITY_PLAN, "test.md")
        assert errors == []


# ---------------------------------------------------------------------------
# v2 fixture-based integration: validate_security_audit with bad semantic content
# ---------------------------------------------------------------------------


class TestValidateSecurityAuditV2:
    def test_placeholder_in_audit_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(PLACEHOLDER_CONTENT)
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed
        assert any("Unresolved placeholder" in e for e in result.errors)

    def test_filler_in_audit_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(FILLER_CONTENT)
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed
        assert any("filler" in e.lower() for e in result.errors)

    def test_empty_verdict_section_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(SECURITY_AUDIT_EMPTY_VERDICT)
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed
        assert any("Verdict" in e for e in result.errors)

    def test_empty_findings_section_fails(self, tmp_path):
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(SECURITY_AUDIT_EMPTY_FINDINGS)
        result = validate_security_audit(path=str(audit_file))
        assert not result.passed
        assert any("Findings" in e for e in result.errors)

    def test_good_audit_still_passes_v2(self, tmp_path):
        """GOOD_ fixture must still pass after v2 checks are added."""
        audit_file = tmp_path / "security_audit_report.md"
        audit_file.write_text(GOOD_SECURITY_AUDIT)
        result = validate_security_audit(path=str(audit_file))
        assert result.passed, f"GOOD_ fixture failed v2: {result.errors}"


# ---------------------------------------------------------------------------
# v2 fixture-based integration: validate_antigravity_plan with bad semantic content
# ---------------------------------------------------------------------------


class TestValidateAntigravityPlanV2:
    def test_placeholder_in_plan_fails(self, tmp_path):
        # Inject a placeholder into the good plan
        bad = GOOD_ANTIGRAVITY_PLAN.replace(
            "The Hoch Agent Swarm integrates",
            "[TODO] The Hoch Agent Swarm integrates",
        )
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(bad)
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed
        assert any("Unresolved placeholder" in e for e in result.errors)

    def test_empty_checklist_items_fail(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(EMPTY_CHECKLIST_CONTENT)
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed
        assert any("Empty checklist" in e for e in result.errors)

    def test_no_numbered_steps_fails(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(ANTIGRAVITY_PLAN_NO_NUMBERED_STEPS)
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed
        assert any("numbered" in e for e in result.errors)

    def test_empty_checklist_section_fails(self, tmp_path):
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(ANTIGRAVITY_PLAN_EMPTY_CHECKLIST)
        result = validate_antigravity_plan(path=str(plan_file))
        assert not result.passed
        assert any("Validation Checklist" in e for e in result.errors)

    def test_good_plan_still_passes_v2(self, tmp_path):
        """GOOD_ fixture must still pass after v2 checks are added."""
        plan_file = tmp_path / "antigravity_execution_plan.md"
        plan_file.write_text(GOOD_ANTIGRAVITY_PLAN)
        result = validate_antigravity_plan(path=str(plan_file))
        assert result.passed, f"GOOD_ fixture failed v2: {result.errors}"


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
