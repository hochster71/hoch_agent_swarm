"""
release_candidate.py — Local release candidate packager for hoch_agent_swarm.

Collects git metadata, dependency versions, quality gate evidence, run report
evidence, and canonical artifact hashes into a single deterministic
release_candidate.json.

A release candidate is only produced when:
  1. The git working tree is clean (no uncommitted changes).
  2. The latest quality_gate_report.json records a PASS verdict.

On success the file is written to:
    artifacts/release_candidates/<timestamp>/release_candidate.json

Usage:
    uv run package_release_candidate              # human-readable output
    uv run package_release_candidate --json       # machine-readable JSON

Exit codes:
    0  RC packaged successfully
    1  Blocked by one or more gate conditions, or packaging error

Design principles:
  - No cloud dependency. No LLM calls. Pure filesystem + git subprocess.
  - All fields are deterministic given the same git commit + evidence files.
  - blocked_by is always present; empty list means the RC is valid.
  - The packager never writes when blocked (fail-fast, no partial output).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CREW_RUNS_DIR = "artifacts/crew_runs"
_RC_DIR = "artifacts/release_candidates"

_CANONICAL_ARTIFACTS: dict[str, str] = {
    "antigravity_execution_plan": "artifacts/antigravity/antigravity_execution_plan.md",
    "execution_plan":             "artifacts/reports/execution_plan.md",
    "release_packet":             "artifacts/reports/release_packet.md",
    "asset_map":                  "artifacts/research/asset_map.md",
    "security_audit_report":      "artifacts/security_reviews/security_audit_report.md",
    "revised_master_prompt_library_json": "artifacts/promptbrain/revised_master_prompt_library.json",
    "revised_master_prompt_library_md":   "artifacts/promptbrain/revised_master_prompt_library.md",
    "llm_brain_schema_json":              "artifacts/promptbrain/llm_brain_schema.json",
    "prompt_coverage_scorecard_json":     "artifacts/promptbrain/prompt_coverage_scorecard.json",
    "gap_analysis_json":                  "artifacts/promptbrain/gap_analysis.json",
    "brain_evidence_db":                  "data/brain_evidence.db",
    "prompt_quality_scores_json":         "artifacts/promptqa/prompt_quality_scores.json",
    "prompt_quality_scores_md":           "artifacts/promptqa/prompt_quality_scores.md",
    "prompt_weakness_register_json":      "artifacts/promptqa/prompt_weakness_register.json",
    "prompt_weakness_register_md":        "artifacts/promptqa/prompt_weakness_register.md",
    "prompt_assertions_json":             "artifacts/promptqa/prompt_assertions.json",
    "prompt_regression_results_json":      "artifacts/promptqa/prompt_regression_results.json",
    "prompt_rewrite_candidates_json":      "artifacts/promptqa/prompt_rewrite_candidates.json",
    "routing_eval_results_json":          "artifacts/promptqa/routing_eval_results.json",
    "prompt_approval_queue_json":         "artifacts/promptqa/prompt_approval_queue.json",
    "prompt_lineage_json":                "artifacts/promptqa/prompt_lineage.json",
    "docker_gap_analysis":                "artifacts/docker1/docker_gap_analysis.md",
    "live_screenshot_manifest":           "artifacts/live_screenshots/manifest.json",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ArtifactEntry:
    """Metadata for a single canonical artifact."""

    path: str
    sha256: Optional[str]
    size_bytes: Optional[int]
    present: bool

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "present": self.present,
        }


@dataclass
class RCResult:
    """
    Result of a release candidate packaging attempt.

    Attributes:
        rc_path:     Absolute path to the written release_candidate.json,
                     or None if packaging was blocked or failed.
        blocked_by:  List of blocking condition descriptions.
                     Empty when the RC was packaged successfully.
        data:        The full RC payload dict (always populated on success;
                     may be partial on block/failure).
        error:       Unexpected exception message, or None.
    """

    rc_path: Optional[str]
    blocked_by: list[str]
    data: dict
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return len(self.blocked_by) == 0 and self.rc_path is not None

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        if self.passed:
            lines.append(f"  ✅ release_candidate: PASS")
            lines.append(f"     written: {self.rc_path}")
        else:
            lines.append("  ❌ release_candidate: BLOCKED")
            for reason in self.blocked_by:
                lines.append(f"     • {reason}")
            if self.error:
                lines.append(f"     error: {self.error}")
        return lines

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.data, indent=indent)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git_run(*args: str) -> str:
    """
    Run a git subcommand and return stripped stdout.
    Raises subprocess.CalledProcessError on non-zero exit.
    """
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def check_git_clean() -> Optional[str]:
    """
    Return None if the working tree is clean, or an error message otherwise.

    'Clean' means `git status --porcelain` returns no output.
    """
    try:
        porcelain = _git_run("status", "--porcelain")
        if porcelain:
            return (
                "Git working tree is not clean — commit or stash changes before "
                f"packaging a release candidate. Dirty files:\n{porcelain}"
            )
        return None
    except subprocess.CalledProcessError as e:
        return f"git status failed: {e.stderr.strip()}"


def get_git_metadata() -> dict:
    """
    Return a dict of git metadata for the current HEAD.

    Fields:
        commit          — full SHA
        commit_short    — 7-char abbreviation
        commit_message  — first line of the commit message
        branch          — current branch name (or 'HEAD' if detached)
        tag             — nearest tag (or None)
    """
    try:
        commit = _git_run("rev-parse", "HEAD")
        commit_short = commit[:7]
        commit_message = _git_run("log", "-1", "--format=%s")
        try:
            branch = _git_run("rev-parse", "--abbrev-ref", "HEAD")
        except subprocess.CalledProcessError:
            branch = "HEAD"
        try:
            tag = _git_run("describe", "--tags", "--exact-match", "HEAD")
        except subprocess.CalledProcessError:
            tag = None
        return {
            "commit": commit,
            "commit_short": commit_short,
            "commit_message": commit_message,
            "branch": branch,
            "tag": tag,
        }
    except subprocess.CalledProcessError as e:
        return {"error": f"git metadata unavailable: {e.stderr.strip()}"}


# ---------------------------------------------------------------------------
# Dependency version helpers
# ---------------------------------------------------------------------------


def _crewai_version() -> str:
    try:
        import crewai
        return crewai.__version__
    except Exception:
        return "unknown"


def _mcp_version() -> str:
    try:
        import mcp
        return mcp.__version__
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Evidence file finders
# ---------------------------------------------------------------------------


def find_latest_gate_report(crew_runs_dir: str = _CREW_RUNS_DIR) -> Optional[str]:
    """
    Return the absolute path of the most recently written quality_gate_report.json,
    or None if no gate report is found under crew_runs_dir.

    Relies on directory name sort (ISO timestamp format YYYYMMDDTHHMMSS).
    """
    base = Path(crew_runs_dir)
    if not base.exists():
        return None
    candidates = sorted(
        base.glob("*/quality_gate_report.json"),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    if candidates:
        return str(candidates[0].resolve())
    return None


def find_latest_run_report(crew_runs_dir: str = _CREW_RUNS_DIR) -> Optional[str]:
    """
    Return the absolute path of the most recently written run_report.json,
    or None if no run report is found.
    """
    base = Path(crew_runs_dir)
    if not base.exists():
        return None
    candidates = sorted(
        base.glob("*/run_report.json"),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    if candidates:
        return str(candidates[0].resolve())
    return None


# ---------------------------------------------------------------------------
# Artifact hashing
# ---------------------------------------------------------------------------


def _sha256_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _file_size(path: str) -> Optional[int]:
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def collect_artifact_entries(
    canonical_paths: dict[str, str] | None = None,
) -> dict[str, ArtifactEntry]:
    """
    Return ArtifactEntry for each canonical artifact path.

    Args:
        canonical_paths: Mapping of logical name → relative path.
                         Defaults to _CANONICAL_ARTIFACTS.
    """
    if canonical_paths is None:
        canonical_paths = _CANONICAL_ARTIFACTS
    entries: dict[str, ArtifactEntry] = {}
    for name, rel_path in canonical_paths.items():
        present = os.path.isfile(rel_path)
        entries[name] = ArtifactEntry(
            path=rel_path,
            sha256=_sha256_file(rel_path) if present else None,
            size_bytes=_file_size(rel_path) if present else None,
            present=present,
        )
    return entries


# ---------------------------------------------------------------------------
# Gate report reader
# ---------------------------------------------------------------------------


def read_gate_report(path: str) -> dict:
    """
    Read and return the parsed JSON from a quality_gate_report.json.
    Raises ValueError on malformed JSON or missing required fields.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "verdict" not in data:
        raise ValueError(f"quality_gate_report.json at {path!r} is missing 'verdict' field")
    return data


# ---------------------------------------------------------------------------
# Main packager
# ---------------------------------------------------------------------------


def build_release_candidate(
    crew_runs_dir: str = _CREW_RUNS_DIR,
    rc_dir: str = _RC_DIR,
    canonical_paths: dict[str, str] | None = None,
) -> RCResult:
    """
    Build a release candidate evidence package.

    Gate conditions (all must pass):
      1. Git working tree is clean.
      2. A quality_gate_report.json exists.
      3. That report's verdict is PASS.

    On success, writes:
        <rc_dir>/<timestamp>/release_candidate.json

    Returns an RCResult with the outcome.
    """
    blocked_by: list[str] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    rc_id = str(uuid.uuid4())
    ts_iso = datetime.now(timezone.utc).isoformat()

    # --- Gate 1: git clean ---
    dirty = check_git_clean()
    if dirty:
        blocked_by.append(dirty)

    # --- Gate 2 & 3: quality gate report ---
    gate_report_path = find_latest_gate_report(crew_runs_dir)
    gate_verdict: Optional[str] = None
    gate_data: dict = {}

    if gate_report_path is None:
        blocked_by.append(
            "No quality_gate_report.json found under "
            f"'{crew_runs_dir}'. Run 'uv run quality_gate --live' first."
        )
    else:
        try:
            gate_data = read_gate_report(gate_report_path)
            gate_verdict = gate_data.get("verdict")
            if gate_verdict != "PASS":
                blocked_by.append(
                    f"Latest quality_gate_report.json verdict is {gate_verdict!r} "
                    f"(expected 'PASS'). Path: {gate_report_path}"
                )
        except (OSError, ValueError, json.JSONDecodeError) as e:
            blocked_by.append(f"Could not read quality_gate_report.json: {e}")

    # --- Collect evidence (always, even if blocked, so data is populated) ---
    git_meta = get_git_metadata()
    artifact_entries = collect_artifact_entries(canonical_paths)
    run_report_path = find_latest_run_report(crew_runs_dir)

    # Check all canonical artifacts are present (warning, not a hard block)
    missing_artifacts = [
        name for name, entry in artifact_entries.items() if not entry.present
    ]
    if missing_artifacts:
        blocked_by.append(
            f"Canonical artifact(s) missing from filesystem: {missing_artifacts}. "
            "Run the crew first to generate all outputs."
        )

    # --- Build payload ---
    data: dict = {
        "rc_id": rc_id,
        "timestamp_utc": ts_iso,
        "verdict": "PASS" if not blocked_by else "BLOCKED",
        "blocked_by": blocked_by,
        "git": git_meta,
        "crewai_version": _crewai_version(),
        "mcp_version": _mcp_version(),
        "python_version": platform.python_version(),
        "gate_verdict": gate_verdict,
        "gate_report_path": gate_report_path,
        "run_report_path": run_report_path,
        "artifacts": {
            name: entry.to_dict()
            for name, entry in artifact_entries.items()
        },
    }

    # --- If blocked, return without writing ---
    if blocked_by:
        return RCResult(rc_path=None, blocked_by=blocked_by, data=data)

    # --- Write ---
    try:
        out_dir = os.path.join(rc_dir, timestamp)
        os.makedirs(out_dir, exist_ok=True)
        rc_path = os.path.join(out_dir, "release_candidate.json")
        with open(rc_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2))
        return RCResult(rc_path=os.path.abspath(rc_path), blocked_by=[], data=data)
    except OSError as e:
        return RCResult(
            rc_path=None,
            blocked_by=[f"Failed to write release candidate: {e}"],
            data=data,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point for `uv run package_release_candidate`.

    Flags:
        --json    Machine-readable JSON output (the RC payload) to stdout

    Returns 0 on success, 1 when blocked or on error.
    """
    argv = argv if argv is not None else sys.argv[1:]
    as_json = "--json" in argv

    result = build_release_candidate()

    if as_json:
        print(result.to_json())
    else:
        for line in result.summary_lines():
            print(line)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
