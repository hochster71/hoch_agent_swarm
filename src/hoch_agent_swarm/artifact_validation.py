"""
artifact_validation.py — Post-run artifact quality enforcement.

Called automatically after every crew kickoff in main.py.
Raises ArtifactValidationError on any violation so bad model output
cannot silently pass through to git staging.

Usage:
    from hoch_agent_swarm.artifact_validation import validate_all_artifacts
    validate_all_artifacts()          # raises on first failure
    validate_all_artifacts(strict=False)  # returns list of errors instead
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SECURITY_AUDIT_PATH = "artifacts/security_reviews/security_audit_report.md"
ANTIGRAVITY_PLAN_PATH = "artifacts/antigravity/antigravity_execution_plan.md"

# ---------------------------------------------------------------------------
# Forbidden patterns (model garbage indicators)
# ---------------------------------------------------------------------------

GARBAGE_PATTERNS: list[tuple[str, str]] = [
    (r"random\.uniform", "Python call: random.uniform(...)"),
    (r"\blambda\b\s+\w+\s*:", "Python lambda expression"),
    (r"```python", "Fenced Python code block"),
    (r"```json", "Fenced JSON code block"),
    (r"\bdef\s+\w+\s*\(", "Python function definition"),
    (r"\bclass\s+\w+\s*[\(:]", "Python class definition"),
    (r"\bimport\s+(?:json|random|os|sys)\b", "Python import statement"),
    (r'"dependencies"\s*:\s*\[', 'Raw JSON fragment: "dependencies": ['),
    (r"execution_time.*random", "Pseudocode: random execution_time assignment"),
    (r"Feel free to ask", "LLM conversational filler"),
    (r"Here's (?:a|the|an) (?:simplified|organized|detailed)", "LLM prose wrapper"),
]

# ---------------------------------------------------------------------------
# Required headings per artifact type
# ---------------------------------------------------------------------------

SECURITY_AUDIT_REQUIRED_HEADINGS: list[str] = [
    "# Security Audit Report",
    "## Scope",
    "## Findings",
    "## Verdict",
]

ANTIGRAVITY_PLAN_REQUIRED_HEADINGS: list[str] = [
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

# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class ArtifactValidationError(Exception):
    """Raised when one or more artifacts fail validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        bullet_list = "\n".join(f"  • {e}" for e in errors)
        super().__init__(
            f"\n\n{'='*60}\n"
            f"ARTIFACT VALIDATION FAILED ({len(errors)} error(s)):\n"
            f"{bullet_list}\n"
            f"{'='*60}\n"
            "Crew run output is invalid. Do not stage or commit.\n"
        )


# ---------------------------------------------------------------------------
# Core validators
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    path: str
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def _read_file(path: str) -> Optional[str]:
    """Return file content or None if the file is missing or empty."""
    if not os.path.isfile(path):
        return None
    content = open(path, "r", encoding="utf-8").read()
    return content if content.strip() else None


def _check_garbage(content: str, path: str) -> list[str]:
    errors = []
    for pattern, description in GARBAGE_PATTERNS:
        if re.search(pattern, content):
            errors.append(f"[{path}] Forbidden pattern detected: {description}")
    return errors


def _check_headings(content: str, path: str, required: list[str]) -> list[str]:
    errors = []
    for heading in required:
        if heading not in content:
            errors.append(f"[{path}] Missing required heading: '{heading}'")
    return errors


def _check_minimum_length(content: str, path: str, min_chars: int = 300) -> list[str]:
    """Reject trivially short outputs that indicate a failed generation."""
    stripped = content.strip()
    if len(stripped) < min_chars:
        return [
            f"[{path}] Content too short: {len(stripped)} chars "
            f"(minimum {min_chars}). Likely incomplete model output."
        ]
    return []


# ---------------------------------------------------------------------------
# Per-artifact validators
# ---------------------------------------------------------------------------


def validate_security_audit(path: str = SECURITY_AUDIT_PATH) -> ValidationResult:
    result = ValidationResult(path=path)

    content = _read_file(path)
    if content is None:
        result.errors.append(
            f"[{path}] File missing or empty. "
            "Security audit was not produced by the crew run."
        )
        return result

    result.errors.extend(_check_minimum_length(content, path, min_chars=200))
    result.errors.extend(_check_headings(content, path, SECURITY_AUDIT_REQUIRED_HEADINGS))
    result.errors.extend(_check_garbage(content, path))

    return result


def validate_antigravity_plan(path: str = ANTIGRAVITY_PLAN_PATH) -> ValidationResult:
    result = ValidationResult(path=path)

    content = _read_file(path)
    if content is None:
        result.errors.append(
            f"[{path}] File missing or empty. "
            "Antigravity execution plan was not produced by the crew run."
        )
        return result

    result.errors.extend(_check_minimum_length(content, path, min_chars=500))
    result.errors.extend(_check_headings(content, path, ANTIGRAVITY_PLAN_REQUIRED_HEADINGS))
    result.errors.extend(_check_garbage(content, path))

    return result


# ---------------------------------------------------------------------------
# Aggregate validator
# ---------------------------------------------------------------------------


def validate_all_artifacts(strict: bool = True) -> list[str]:
    """
    Validate all expected crew output artifacts.

    Args:
        strict: If True (default), raise ArtifactValidationError on any failure.
                If False, return the list of error strings instead.

    Returns:
        Empty list if all artifacts pass (strict=False mode).

    Raises:
        ArtifactValidationError: If strict=True and any artifact fails.
    """
    all_errors: list[str] = []

    for validate_fn in (validate_security_audit, validate_antigravity_plan):
        result = validate_fn()
        all_errors.extend(result.errors)

    if all_errors and strict:
        raise ArtifactValidationError(all_errors)

    return all_errors


# ---------------------------------------------------------------------------
# CLI entry point for manual invocation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    errors = validate_all_artifacts(strict=False)
    if errors:
        print(f"\nVALIDATION FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)
    else:
        print("\nAll artifacts passed validation.")
        sys.exit(0)
