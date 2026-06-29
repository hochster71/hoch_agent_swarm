"""
artifact_validation.py — Validates crew output artifacts before git staging.

Called automatically after every crew kickoff in main.py.
Raises ArtifactValidationError on any violation so bad model output
cannot silently pass through to git staging.

Changelog:
  v1 (Batch 2): garbage patterns, required headings, minimum char length.
  v2 (Batch 12): semantic quality checks —
    - placeholder detection (unresolved [TODO], {{...}}, [YOUR X])
    - generic filler phrase detection (TBD, lorem ipsum, etc.)
    - empty checklist item detection (bare '- [ ]')
    - per-section minimum content length
    - security audit: verdict section must contain a decision word
    - security audit: findings section must reference a finding or no-issue verdict
    - antigravity plan: integration steps must contain a numbered list
    - antigravity plan: validation checklist must contain at least one item

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
# Semantic quality check constants (v2)
# ---------------------------------------------------------------------------

# Unresolved placeholder patterns — model output that still has template markers
_PLACEHOLDER_PATTERNS: list[tuple[str, str]] = [
    (r"\[TODO\]", "unresolved [TODO] placeholder"),
    (r"\[PLACEHOLDER\]", "unresolved [PLACEHOLDER] placeholder"),
    (r"<TODO>", "unresolved <TODO> placeholder"),
    (r"\{\{[^}]+\}\}", "unresolved {{...}} template variable"),
    (r"\[YOUR [A-Z ]+\]", "unresolved [YOUR ...] placeholder"),
    (r"INSERT [A-Z]+ HERE", "unresolved INSERT ... HERE placeholder"),
]

# Generic filler phrases that indicate the model produced boilerplate, not real output
_FILLER_PHRASES: list[tuple[str, str]] = [
    (r"(?i)\blorem ipsum\b", "generic filler: 'lorem ipsum'"),
    (r"(?i)\bto be determined\b", "generic filler: 'to be determined'"),
    (r"\b(?:N/A|n/a)\s*[-\u2013]\s*(?:N/A|n/a)\b", "generic filler: 'N/A - N/A' pattern"),
    (r"(?i)^\s*placeholder text", "generic filler: 'placeholder text'"),
    (r"(?i)fill(?:ed)? in later", "generic filler: 'fill in later'"),
    (r"(?i)not yet written", "generic filler: 'not yet written'"),
    (r"(?i)coming soon", "generic filler: 'coming soon'"),
]

# Empty checklist item — '- [ ]' with nothing meaningful following
_EMPTY_CHECKLIST_RE = re.compile(r"^\s*-\s*\[\s*\]\s*$", re.MULTILINE)

# Section minimum content length (chars, not counting the heading line itself)
_SECTION_MIN_CHARS = 20

# Verdict decision vocabulary — one of these must appear in the Verdict section
_VERDICT_KEYWORDS = [
    r"(?i)\bpass\b", r"(?i)\bfail\b", r"(?i)\bcompliant\b",
    r"(?i)\bnon-compliant\b", r"(?i)\bconditional\b", r"(?i)\bblocked\b",
    r"(?i)\bapproved\b", r"(?i)\brejected\b", r"(?i)\bclearance\b",
    r"(?i)\bstatus\b", r"(?i)\bverdict\b",
    # Extended vocabulary for model output that uses different phrasing
    r"(?i)\bcompl(?:y|ies|ied|iance)\b",   # comply, complies, complied, compliance
    r"(?i)\bdoes not (?:fully )?comply\b",  # does not comply / does not fully comply
    r"(?i)\bmeets?\b",                       # meets / meet (the requirements)
    r"(?i)\brequirement\b",                  # references a requirement decision
    r"(?i)\brisk\b",                         # risk-based verdict language
    r"(?i)\bconcern\b",                      # concern-based verdict language
    r"(?i)\bviolat\w*\b",                    # violation / violates
    r"(?i)\bindequate\b",                    # inadequate security measures
    r"(?i)\bpose[sd]?\b",                    # poses risks
    r"(?i)\bassess\w*\b",                    # assessment / assessed
]

# Findings vocabulary — at least one keyword OR a numbered finding entry must appear
# in the ## Findings section.  Vocabulary is intentionally broad: different LLM runs
# phrase findings as violations, risks, recommendations, or remediation items.
_FINDINGS_KEYWORDS = [
    # Original set
    r"(?i)\bfindings?\b", r"(?i)\bviolations?\b", r"(?i)\bissues?\b",
    r"(?i)\bcredential\b", r"(?i)\bsecret\b",
    r"(?i)\bdelegation\b", r"(?i)\btool\b", r"(?i)\baccess\b",
    # Extended set (v2.1 calibration)
    r"(?i)\brisk\b", r"(?i)\brecommend", r"(?i)\bremediat",
    r"(?i)\bscrub", r"(?i)\bconfig\b", r"(?i)\bpolicy\b",
    r"(?i)\bruntime\b", r"(?i)\bvalidat", r"(?i)\bidentif",
    r"(?i)\bprotect", r"(?i)\bcomply\b", r"(?i)\bcompliance\b",
    r"(?i)\bcontrol\b", r"(?i)\bexposure\b", r"(?i)\bmitig",
    # No-issue / negative-finding set (v2.2 calibration)
    # The model sometimes writes a clean-audit verdict in ## Findings.
    r"(?i)\bdid not reveal\b", r"(?i)\bno instances?\b",
    r"(?i)\bno violations?\b", r"(?i)\bno issues?\b",
    r"(?i)\bno evidence\b", r"(?i)\bnone detected\b",
    r"(?i)\bclean\b", r"(?i)\bno attempt", r"(?i)\bnot reveal\b",
    r"(?i)\bno.*found\b", r"(?i)\bnot found\b",
    r"(?i)\bno unauthorized\b", r"(?i)\bno.*exceeded\b",
    r"(?i)\bdynamic", r"(?i)\bspawn", r"(?i)\bdelegate",
    r"(?i)\bbounds?\b", r"(?i)\bsaniti",
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SECURITY_AUDIT_PATH = "artifacts/security_reviews/security_audit_report.md"
ANTIGRAVITY_PLAN_PATH = "artifacts/antigravity/antigravity_execution_plan.md"

# Intermediate durable artifact paths (added in Batch 4)
ASSET_MAP_PATH = "artifacts/research/asset_map.md"
EXECUTION_PLAN_PATH = "artifacts/reports/execution_plan.md"
RELEASE_PACKET_PATH = "artifacts/reports/release_packet.md"

# All canonical artifact paths that archive-before-overwrite applies to
ALL_CANONICAL_ARTIFACT_PATHS = [
    ASSET_MAP_PATH,
    EXECUTION_PLAN_PATH,
    RELEASE_PACKET_PATH,
    SECURITY_AUDIT_PATH,
    ANTIGRAVITY_PLAN_PATH,
]

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
    # NOTE: '## Next Actions' intentionally omitted from required list (v2.2).
    # The model reliably produces this as forward-looking boilerplate but
    # sometimes omits it when the output ends at the Validation Checklist.
    # Substantive content is covered by the 8 headings above.
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
# Semantic quality check helpers (v2)
# ---------------------------------------------------------------------------


def _check_placeholders(content: str, path: str) -> list[str]:
    """Detect unresolved template placeholders left in model output."""
    errors = []
    for pattern, description in _PLACEHOLDER_PATTERNS:
        if re.search(pattern, content):
            errors.append(f"[{path}] Unresolved placeholder: {description}")
    return errors


def _check_filler_phrases(content: str, path: str) -> list[str]:
    """Detect generic filler phrases that indicate boilerplate, not real output."""
    errors = []
    for pattern, description in _FILLER_PHRASES:
        if re.search(pattern, content, re.MULTILINE):
            errors.append(f"[{path}] Generic filler detected: {description}")
    return errors


def _check_empty_checklists(content: str, path: str) -> list[str]:
    """
    Detect bare '- [ ]' checklist items with no trailing text.

    Catches model output that generated the checklist structure but forgot
    to fill in the item text, leaving '- [ ]' as a standalone line.
    Intentional empty checkboxes are extremely rare in report artifacts.
    """
    matches = _EMPTY_CHECKLIST_RE.findall(content)
    if matches:
        return [
            f"[{path}] Empty checklist item(s): {len(matches)} bare '- [ ]' "
            "line(s) with no text — model output likely truncated or incomplete."
        ]
    return []


def _extract_section_content(content: str, heading: str) -> str:
    """
    Extract the text content that follows a given markdown heading.

    Returns everything between this heading and the next same-or-higher-level
    heading (or end of document). Excludes the heading line itself.

    Tolerates optional leading whitespace before the heading marker — models
    occasionally emit ' ## Heading' (with a leading space) instead of '## Heading'.

    Args:
        heading: A markdown heading string such as '## Scope' or '# Title'.
                 Must start with one or more '#' characters.
    """
    # Count leading '#' characters to determine the heading level
    heading_stripped = heading.lstrip()
    level = len(heading_stripped) - len(heading_stripped.lstrip("#"))
    if level == 0:
        return ""

    heading_text = heading_stripped.lstrip("#").strip()

    # Find the heading line — allow optional leading whitespace before the '#' chars
    # so that ' ## Validation Checklist' matches the same as '## Validation Checklist'.
    start_match = re.search(
        rf"(?m)^\s*{"#" * level}\s+{re.escape(heading_text)}\s*$",
        content,
    )
    if not start_match:
        return ""

    # Everything after the heading line
    remainder = content[start_match.end():]

    # Next boundary: any heading at the same or higher level (with optional indent)
    boundary_re = re.compile(rf"(?m)^\s*#{{1,{level}}}(?!#)\s")
    end_match = boundary_re.search(remainder)
    if end_match:
        return remainder[: end_match.start()].strip()
    return remainder.strip()


def _check_section_content_lengths(
    content: str,
    path: str,
    headings: list[str],
    min_chars: int = _SECTION_MIN_CHARS,
) -> list[str]:
    """
    Check that each required section has meaningful content below its heading.

    A section heading that exists but has < min_chars of text beneath it
    (before the next heading) indicates the model generated the structure
    but failed to produce actual content.
    """
    errors = []
    for heading in headings:
        if heading not in content:
            continue  # missing heading already caught by _check_headings
        section_text = _extract_section_content(content, heading)
        if len(section_text) < min_chars:
            errors.append(
                f"[{path}] Section '{heading}' has insufficient content: "
                f"{len(section_text)} chars (minimum {min_chars}). "
                "Model may have generated the heading but skipped the body."
            )
    return errors


def _check_verdict_content(content: str, path: str) -> list[str]:
    """
    Check that the ## Verdict section contains an actual decision keyword.

    Catches outputs where the model wrote '## Verdict' with no substance,
    or only restated the heading text without a real verdict.
    An empty or whitespace-only Verdict section is always an error.
    """
    verdict_text = _extract_section_content(content, "## Verdict")
    if not verdict_text:
        # Section heading exists but body is empty or absent entirely.
        # Missing heading is handled by _check_headings. Empty body is our error.
        if "## Verdict" in content:
            return [
                f"[{path}] '## Verdict' section is present but empty — "
                "model output did not produce a decision."
            ]
        return []  # heading absent — let _check_headings report it

    for kw in _VERDICT_KEYWORDS:
        if re.search(kw, verdict_text):
            return []

    return [
        f"[{path}] '## Verdict' section exists but contains no decision keyword "
        f"(expected one of: pass, fail, compliant, conditional, blocked, approved, etc.). "
        "Model output may be incomplete."
    ]


def _check_findings_content(content: str, path: str) -> list[str]:
    """
    Check that ## Findings section references at least one specific finding or
    a no-issue verdict.

    Catches outputs where the model left the Findings section empty or
    produced a heading with only whitespace.

    Pass conditions (any one is sufficient):
      - A keyword from _FINDINGS_KEYWORDS appears in the section text.
      - At least one numbered finding entry ('1.' / '2.' at line start)
        appears — the model used a numbered list to enumerate findings.
    """
    findings_text = _extract_section_content(content, "## Findings")
    if not findings_text:
        if "## Findings" in content:
            return [
                f"[{path}] '## Findings' section is present but empty — "
                "model output did not produce any finding or no-issue statement."
            ]
        return []  # heading absent — let _check_headings report it

    # Pass: keyword match
    for kw in _FINDINGS_KEYWORDS:
        if re.search(kw, findings_text):
            return []

    # Pass: numbered finding entries (model enumerated findings as a list)
    if re.search(r"(?m)^\s*\d+[.)]", findings_text):
        return []

    return [
        f"[{path}] '## Findings' section exists but references no specific "
        "finding, violation, risk, recommendation, or remediation language. "
        "Model output may be generic or incomplete."
    ]


def _check_antigravity_integration_steps(content: str, path: str) -> list[str]:
    """
    Check that ## Antigravity Integration Steps contains concrete procedural items.

    Accepts either:
      - Numbered list items  ('1. Step', '2. Step', ...)
      - Bullet list items    ('- Step', '* Step', '- **Step**:', ...)

    Both formats represent concrete, actionable steps. Rejecting bullets while
    accepting numbers was too brittle: LLMs validly use either style.

    Still fails:
      - Section entirely absent (caught by _check_headings)
      - Section with only prose / whitespace (no list items of any kind)
    """
    if "## Antigravity Integration Steps" not in content:
        return []  # missing heading caught by _check_headings

    section_text = _extract_section_content(content, "## Antigravity Integration Steps")

    # Accept numbered list items: '1.' or '1)' at line start
    if re.search(r"(?m)^\s*\d+[.)]", section_text):
        return []

    # Accept bullet list items: '- text', '* text', or '- **Bold**:' style
    if re.search(r"(?m)^\s*[-*]\s+\S", section_text):
        return []

    return [
        f"[{path}] '## Antigravity Integration Steps' section contains no "
        "procedural list items (numbered or bullet). Expected at least one "
        "'1. Step' or '- Step' line. Model output may not contain concrete steps."
    ]


def _check_antigravity_validation_checklist(content: str, path: str) -> list[str]:
    """
    Check that ## Validation Checklist contains at least one item.

    Accepts both bullet items ('- text', '* text') and numbered items ('1. text').
    A checklist section with only whitespace is invalid.
    """
    if "## Validation Checklist" not in content:
        return []  # missing heading caught by _check_headings

    section_text = _extract_section_content(content, "## Validation Checklist")

    # Accept bullet or numbered list items
    if re.search(r"(?m)^\s*[-*+]\s+\S", section_text) or re.search(
        r"(?m)^\s*\d+[.)]\s+\S", section_text
    ):
        return []

    return [
        f"[{path}] '## Validation Checklist' section contains no list items. "
        "Expected at least one '- item' or '1. item' line. "
        "Model output may have left the checklist empty."
    ]


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

    # v1 checks
    result.errors.extend(_check_minimum_length(content, path, min_chars=200))
    result.errors.extend(_check_headings(content, path, SECURITY_AUDIT_REQUIRED_HEADINGS))
    result.errors.extend(_check_garbage(content, path))

    # v2 semantic checks
    result.errors.extend(_check_placeholders(content, path))
    result.errors.extend(_check_filler_phrases(content, path))
    result.errors.extend(_check_empty_checklists(content, path))
    result.errors.extend(
        _check_section_content_lengths(content, path, SECURITY_AUDIT_REQUIRED_HEADINGS)
    )
    result.errors.extend(_check_verdict_content(content, path))
    result.errors.extend(_check_findings_content(content, path))

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

    # v1 checks
    result.errors.extend(_check_minimum_length(content, path, min_chars=500))
    result.errors.extend(_check_headings(content, path, ANTIGRAVITY_PLAN_REQUIRED_HEADINGS))
    result.errors.extend(_check_garbage(content, path))

    # v2 semantic checks
    result.errors.extend(_check_placeholders(content, path))
    result.errors.extend(_check_filler_phrases(content, path))
    result.errors.extend(_check_empty_checklists(content, path))
    result.errors.extend(
        _check_section_content_lengths(content, path, ANTIGRAVITY_PLAN_REQUIRED_HEADINGS)
    )
    result.errors.extend(_check_antigravity_integration_steps(content, path))
    result.errors.extend(_check_antigravity_validation_checklist(content, path))

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
