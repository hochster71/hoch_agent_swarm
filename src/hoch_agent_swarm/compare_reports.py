"""
compare_reports.py — Compare two crew run_report.json files.

Automates the manual Step 7 comparison from the isolated trial procedure.
Produces a verdict (PROMOTE / INVESTIGATE / BLOCK) based on structured
diff of status, artifact validation, errors, and version fields.

SHA-256 hash diffs are noted but not used for the verdict — model output
varies run to run so artifact content changing is expected.

Usage:
    uv run compare_reports <baseline.json> <trial.json>
    uv run compare_reports --json <baseline.json> <trial.json>

Exit codes:
    0   PROMOTE — trial passed all gates
    1   BLOCK or INVESTIGATE — see output for details
"""

from __future__ import annotations

import json
import os
import sys

from dataclasses import asdict, dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Verdict constants
# ---------------------------------------------------------------------------

VERDICT_PROMOTE = "PROMOTE"
VERDICT_INVESTIGATE = "INVESTIGATE"
VERDICT_BLOCK = "BLOCK"

_VERDICT_EXIT = {
    VERDICT_PROMOTE: 0,
    VERDICT_INVESTIGATE: 1,
    VERDICT_BLOCK: 1,
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ArtifactDiff:
    """Per-artifact comparison between baseline and trial."""

    path: str
    baseline_validation: str   # VALID / INVALID / MISSING / NOT_VALIDATED
    trial_validation: str
    baseline_size_bytes: Optional[int]
    trial_size_bytes: Optional[int]
    sha256_changed: bool       # expected=True for LLM output; informational only
    regression: bool           # True if trial is worse than baseline

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ComparisonResult:
    """Full comparison result between a baseline and trial run report."""

    verdict: str                    # PROMOTE / INVESTIGATE / BLOCK
    baseline_path: str
    trial_path: str
    baseline_crewai_version: str
    trial_crewai_version: str
    baseline_mcp_version: str
    trial_mcp_version: str
    baseline_status: str
    trial_status: str
    baseline_errors: list[str]
    trial_errors: list[str]
    artifact_diffs: list[ArtifactDiff] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)  # human-readable rationale

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary_lines(self) -> list[str]:
        """Return human-readable terminal output lines."""
        lines: list[str] = []

        # Header
        lines.append(f"baseline : {self.baseline_path}")
        lines.append(f"trial    : {self.trial_path}")
        lines.append("")

        # Version table
        lines.append(f"  crewai  : {self.baseline_crewai_version}  →  {self.trial_crewai_version}")
        lines.append(f"  mcp     : {self.baseline_mcp_version}  →  {self.trial_mcp_version}")
        lines.append(f"  status  : {self.baseline_status}  →  {self.trial_status}")
        lines.append("")

        # Errors
        if self.trial_errors:
            lines.append(f"  trial errors ({len(self.trial_errors)}):")
            for e in self.trial_errors:
                lines.append(f"    • {e}")
            lines.append("")

        # Artifacts
        lines.append("  artifacts:")
        for d in self.artifact_diffs:
            name = os.path.basename(d.path)
            val_icon = "✅" if d.trial_validation == "VALID" else "❌"
            reg_tag = " ← REGRESSION" if d.regression else ""
            size_delta = ""
            if d.baseline_size_bytes is not None and d.trial_size_bytes is not None:
                delta = d.trial_size_bytes - d.baseline_size_bytes
                sign = "+" if delta >= 0 else ""
                size_delta = f"  ({sign}{delta}b)"
            sha_tag = " [hash changed — expected]" if d.sha256_changed else " [hash unchanged]"
            lines.append(
                f"    {val_icon} {name:<45} {d.trial_validation:<14}{size_delta}{sha_tag}{reg_tag}"
            )
        lines.append("")

        # Findings
        if self.findings:
            lines.append("  findings:")
            for f in self.findings:
                lines.append(f"    • {f}")
            lines.append("")

        # Verdict
        verdict_icon = {"PROMOTE": "✅", "INVESTIGATE": "⚠️ ", "BLOCK": "❌"}[self.verdict]
        lines.append(f"verdict: {verdict_icon} {self.verdict}")
        return lines


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------


def _load_report(path: str) -> dict:
    """Load a run_report.json from path. Raises FileNotFoundError or ValueError."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Run report not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid run report format: {path}")
    return data


def _artifact_map(report: dict) -> dict[str, dict]:
    """Index canonical_artifacts by their path field."""
    return {a["path"]: a for a in report.get("canonical_artifacts", [])}


def _diff_artifacts(baseline: dict, trial: dict) -> tuple[list[ArtifactDiff], list[str]]:
    """
    Produce per-artifact diffs and a list of regression finding strings.

    Regression = trial validation_status is worse than baseline:
      VALID → anything else is a regression
      INVALID → trial also INVALID is neutral (both broken)
      MISSING → trial also MISSING is neutral
    """
    b_map = _artifact_map(baseline)
    t_map = _artifact_map(trial)
    all_paths = sorted(set(b_map) | set(t_map))

    diffs: list[ArtifactDiff] = []
    findings: list[str] = []

    for path in all_paths:
        b = b_map.get(path, {})
        t = t_map.get(path, {})
        name = os.path.basename(path)

        b_val = b.get("validation_status", "MISSING")
        t_val = t.get("validation_status", "MISSING")

        b_sha = b.get("sha256")
        t_sha = t.get("sha256")
        sha_changed = (b_sha != t_sha) and (b_sha is not None or t_sha is not None)

        # Regression: baseline was VALID, trial is not
        regression = (b_val == "VALID") and (t_val != "VALID")
        if regression:
            findings.append(f"{name}: VALID → {t_val} (regression)")

        # New artifact missing in trial
        if path not in t_map:
            findings.append(f"{name}: present in baseline but MISSING in trial")

        diffs.append(ArtifactDiff(
            path=path,
            baseline_validation=b_val,
            trial_validation=t_val,
            baseline_size_bytes=b.get("size_bytes"),
            trial_size_bytes=t.get("size_bytes"),
            sha256_changed=sha_changed,
            regression=regression,
        ))

    return diffs, findings


def compare_run_reports(
    baseline_path: str,
    trial_path: str,
) -> ComparisonResult:
    """
    Compare a baseline run_report.json to a trial run_report.json.

    Args:
        baseline_path: Path to the sealed-main run report.
        trial_path:    Path to the trial-worktree run report.

    Returns:
        ComparisonResult with verdict and full diff.
    """
    baseline = _load_report(baseline_path)
    trial = _load_report(trial_path)

    b_status = baseline.get("status", "UNKNOWN")
    t_status = trial.get("status", "UNKNOWN")
    b_errors = baseline.get("errors", [])
    t_errors = trial.get("errors", [])
    b_crewai = baseline.get("crewai_version", "unknown")
    t_crewai = trial.get("crewai_version", "unknown")
    b_mcp = baseline.get("mcp_stub_version", "unknown")
    t_mcp = trial.get("mcp_stub_version", "unknown")

    artifact_diffs, art_findings = _diff_artifacts(baseline, trial)

    findings: list[str] = list(art_findings)

    # Collect additional findings
    if t_errors:
        findings.append(f"trial has {len(t_errors)} error(s): {t_errors}")

    if b_crewai == t_crewai:
        findings.append(f"crewai version unchanged: {t_crewai} (was this intentional?)")

    if b_mcp != t_mcp:
        findings.append(f"mcp_stub_version changed: {b_mcp} → {t_mcp}")

    # Verdict
    any_regression = any(d.regression for d in artifact_diffs)
    any_invalid = any(d.trial_validation not in ("VALID",) for d in artifact_diffs
                      if d.path in _artifact_map(trial))
    trial_failed = t_status != "PASS"

    if trial_failed or any_regression:
        verdict = VERDICT_BLOCK
    elif t_errors or any_invalid:
        verdict = VERDICT_INVESTIGATE
    else:
        verdict = VERDICT_PROMOTE

    return ComparisonResult(
        verdict=verdict,
        baseline_path=os.path.abspath(baseline_path),
        trial_path=os.path.abspath(trial_path),
        baseline_crewai_version=b_crewai,
        trial_crewai_version=t_crewai,
        baseline_mcp_version=b_mcp,
        trial_mcp_version=t_mcp,
        baseline_status=b_status,
        trial_status=t_status,
        baseline_errors=b_errors,
        trial_errors=t_errors,
        artifact_diffs=artifact_diffs,
        findings=findings,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """
    CLI entry point for `uv run compare_reports`.

    Usage:
        compare_reports <baseline.json> <trial.json>
        compare_reports --json <baseline.json> <trial.json>

    Returns 0 for PROMOTE, 1 for BLOCK or INVESTIGATE.
    """
    argv = argv if argv is not None else sys.argv[1:]
    as_json = "--json" in argv
    positional = [a for a in argv if not a.startswith("--")]

    if len(positional) != 2:
        print(
            "Usage: compare_reports [--json] <baseline_report.json> <trial_report.json>",
            file=sys.stderr,
        )
        return 2

    baseline_path, trial_path = positional

    try:
        result = compare_run_reports(baseline_path, trial_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if as_json:
        print(result.to_json())
    else:
        for line in result.summary_lines():
            print(line)

    return _VERDICT_EXIT[result.verdict]


if __name__ == "__main__":
    sys.exit(main())
