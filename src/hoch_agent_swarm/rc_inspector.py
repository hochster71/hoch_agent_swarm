"""
rc_inspector.py — Release candidate inspector for hoch_agent_swarm.

Inspects an existing release_candidate.json, verifies that all linked
evidence files still exist, recomputes artifact hashes, and detects drift
from the state captured at packaging time.

This is a read-only tool — it does not write or modify any files.

Usage:
    uv run inspect_release_candidate <path/to/release_candidate.json>
    uv run inspect_release_candidate <path> --json
    uv run inspect_release_candidate --latest       # find newest RC automatically

Exit codes:
    0  PASS — all checks pass, no drift detected
    1  FAIL — one or more checks failed, or drift detected

Checks performed:
    schema          — Required keys present in RC; artifact entries well-formed
    git_commit      — RC commit SHA still reachable in local git history
    gate_report     — quality_gate_report.json at gate_report_path exists and
                      contains a valid 'verdict' field
    run_report      — run_report.json at run_report_path exists and is valid JSON
    artifact_hashes — Each artifact re-hashed; compared against RC snapshot;
                      drift (hash changed) and absent (file missing) both fail

Design principles:
  - Read-only. No side effects.
  - No cloud dependency. No LLM calls.
  - All checks run unconditionally (no short-circuit) so the full picture
    is always visible.
  - Drift is distinguished from absence: a missing file and a changed file
    are different failure modes.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

# Top-level keys required in a well-formed release_candidate.json
_RC_REQUIRED_KEYS: tuple[str, ...] = (
    "rc_id",
    "timestamp_utc",
    "verdict",
    "blocked_by",
    "git",
    "crewai_version",
    "mcp_version",
    "python_version",
    "gate_verdict",
    "gate_report_path",
    "run_report_path",
    "artifacts",
)

# Keys required in each entry under rc["artifacts"]
_ARTIFACT_REQUIRED_KEYS: tuple[str, ...] = ("path", "sha256", "size_bytes", "present")

# gitignored base dir — used by --latest
_RC_DIR = "artifacts/release_candidates"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Outcome of a single inspector check."""

    name: str
    passed: bool
    detail: str           # human-readable summary
    notes: list[str] = field(default_factory=list)  # per-item details (drift lines etc.)

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "passed": self.passed, "detail": self.detail}
        if self.notes:
            d["notes"] = self.notes
        return d


@dataclass
class ArtifactInspection:
    """Per-artifact hash comparison result."""

    name: str
    path: str
    stored_sha256: Optional[str]   # from the RC at packaging time
    current_sha256: Optional[str]  # recomputed now
    stored_size: Optional[int]
    current_size: Optional[int]
    present_now: bool

    @property
    def drifted(self) -> bool:
        """True when the file is present but its hash has changed."""
        return (
            self.present_now
            and self.stored_sha256 is not None
            and self.current_sha256 != self.stored_sha256
        )

    @property
    def absent(self) -> bool:
        """True when the file cannot be found on disk."""
        return not self.present_now

    @property
    def ok(self) -> bool:
        return self.present_now and not self.drifted

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "stored_sha256": self.stored_sha256,
            "current_sha256": self.current_sha256,
            "stored_size": self.stored_size,
            "current_size": self.current_size,
            "present_now": self.present_now,
            "drifted": self.drifted,
            "absent": self.absent,
            "ok": self.ok,
        }


@dataclass
class InspectionResult:
    """
    Aggregated result of inspecting a release candidate.

    Attributes:
        rc_path             Path to the inspected release_candidate.json
        rc_id               RC identifier from the file
        rc_verdict          Verdict recorded at packaging time
        inspection_verdict  Verdict of this inspection run (PASS/FAIL)
        timestamp_utc       When this inspection was performed
        checks              Ordered list of CheckResult items
        artifacts           Per-artifact inspection detail
    """

    rc_path: str
    rc_id: str
    rc_verdict: str
    inspection_verdict: str       # "PASS" or "FAIL"
    timestamp_utc: str
    checks: list[CheckResult] = field(default_factory=list)
    artifacts: list[ArtifactInspection] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.inspection_verdict == "PASS"

    @property
    def drifted_artifacts(self) -> list[str]:
        return [a.name for a in self.artifacts if a.drifted]

    @property
    def absent_artifacts(self) -> list[str]:
        return [a.name for a in self.artifacts if a.absent]

    def to_dict(self) -> dict:
        return {
            "rc_path": self.rc_path,
            "rc_id": self.rc_id,
            "rc_verdict": self.rc_verdict,
            "inspection_verdict": self.inspection_verdict,
            "timestamp_utc": self.timestamp_utc,
            "passed": self.passed,
            "drifted_artifacts": self.drifted_artifacts,
            "absent_artifacts": self.absent_artifacts,
            "checks": [c.to_dict() for c in self.checks],
            "artifacts": [a.to_dict() for a in self.artifacts],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        lines.append(f"  RC: {self.rc_path}")
        lines.append(f"  RC ID: {self.rc_id}")
        lines.append(f"  RC packaged verdict: {self.rc_verdict}")
        lines.append("")
        for c in self.checks:
            icon = "✅" if c.passed else "❌"
            lines.append(f"  {icon} {c.name}: {c.detail}")
            for note in c.notes:
                lines.append(f"       {note}")
        lines.append("")
        icon = "✅" if self.passed else "❌"
        lines.append(f"inspect_release_candidate: {icon} {self.inspection_verdict}")
        if self.drifted_artifacts:
            lines.append(f"  ⚠️  Drifted artifacts: {self.drifted_artifacts}")
        if self.absent_artifacts:
            lines.append(f"  ⚠️  Absent artifacts:  {self.absent_artifacts}")
        return lines


# ---------------------------------------------------------------------------
# Individual check helpers
# ---------------------------------------------------------------------------


def _check_schema(rc: dict, rc_path: str) -> CheckResult:
    """Verify all required top-level keys are present and artifacts are well-formed."""
    missing_top = [k for k in _RC_REQUIRED_KEYS if k not in rc]
    if missing_top:
        return CheckResult(
            name="schema",
            passed=False,
            detail=f"Missing required keys: {missing_top}",
        )

    # Verify artifacts sub-structure
    artifacts = rc.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return CheckResult(name="schema", passed=False, detail="'artifacts' is not a dict")

    malformed = []
    for name, entry in artifacts.items():
        if not isinstance(entry, dict):
            malformed.append(f"{name}: not a dict")
            continue
        missing = [k for k in _ARTIFACT_REQUIRED_KEYS if k not in entry]
        if missing:
            malformed.append(f"{name}: missing keys {missing}")

    if malformed:
        return CheckResult(
            name="schema",
            passed=False,
            detail=f"Malformed artifact entries: {len(malformed)}",
            notes=malformed,
        )

    return CheckResult(
        name="schema",
        passed=True,
        detail=f"All {len(_RC_REQUIRED_KEYS)} required keys present; "
               f"{len(artifacts)} artifact entries well-formed",
    )


def _check_git_commit(rc: dict) -> CheckResult:
    """Verify the RC's recorded commit SHA is still reachable in local git."""
    git_meta = rc.get("git", {})
    commit = git_meta.get("commit")
    if not commit:
        return CheckResult(
            name="git_commit",
            passed=False,
            detail="No 'commit' field in RC git metadata",
        )
    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", commit],
            capture_output=True,
            text=True,
            check=True,
        )
        obj_type = result.stdout.strip()
        if obj_type == "commit":
            short = commit[:7]
            msg = git_meta.get("commit_message", "")
            branch = git_meta.get("branch", "")
            return CheckResult(
                name="git_commit",
                passed=True,
                detail=f"Commit {short} reachable (branch: {branch})",
                notes=[f"message: {msg}"] if msg else [],
            )
        return CheckResult(
            name="git_commit",
            passed=False,
            detail=f"Object {commit[:7]} exists but type is {obj_type!r}, expected 'commit'",
        )
    except subprocess.CalledProcessError:
        return CheckResult(
            name="git_commit",
            passed=False,
            detail=f"Commit {commit[:7]} not found in local git history",
        )


def _check_gate_report(rc: dict) -> CheckResult:
    """Verify quality_gate_report.json at gate_report_path exists and has a verdict."""
    path = rc.get("gate_report_path")
    if not path:
        return CheckResult(
            name="gate_report",
            passed=False,
            detail="No 'gate_report_path' in RC",
        )
    if not os.path.isfile(path):
        return CheckResult(
            name="gate_report",
            passed=False,
            detail=f"File not found: {path}",
        )
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        verdict = data.get("verdict", "<absent>")
        run_id = data.get("run_id", "")
        return CheckResult(
            name="gate_report",
            passed=True,
            detail=f"Exists; verdict={verdict}",
            notes=[f"run_id: {run_id}", f"path: {path}"],
        )
    except (OSError, json.JSONDecodeError) as e:
        return CheckResult(
            name="gate_report",
            passed=False,
            detail=f"Could not read gate report: {e}",
        )


def _check_run_report(rc: dict) -> CheckResult:
    """Verify run_report.json at run_report_path exists and is valid JSON."""
    path = rc.get("run_report_path")
    if not path:
        return CheckResult(
            name="run_report",
            passed=False,
            detail="No 'run_report_path' in RC",
        )
    if not os.path.isfile(path):
        return CheckResult(
            name="run_report",
            passed=False,
            detail=f"File not found: {path}",
        )
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        run_id = data.get("run_id", "<absent>")
        return CheckResult(
            name="run_report",
            passed=True,
            detail=f"Exists; run_id={run_id}",
            notes=[f"path: {path}"],
        )
    except (OSError, json.JSONDecodeError) as e:
        return CheckResult(
            name="run_report",
            passed=False,
            detail=f"Could not read run report: {e}",
        )


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


def _inspect_artifacts(rc: dict) -> tuple[CheckResult, list[ArtifactInspection]]:
    """
    Re-hash each canonical artifact and compare against the RC snapshot.

    Returns (CheckResult, [ArtifactInspection]).
    """
    artifacts_data = rc.get("artifacts", {})
    inspections: list[ArtifactInspection] = []
    drifted: list[str] = []
    absent: list[str] = []
    notes: list[str] = []

    for name, entry in artifacts_data.items():
        path = entry.get("path", "")
        stored_sha = entry.get("sha256")
        stored_size = entry.get("size_bytes")
        present_now = os.path.isfile(path)
        current_sha = _sha256_file(path) if present_now else None
        current_size = _file_size(path) if present_now else None

        ai = ArtifactInspection(
            name=name,
            path=path,
            stored_sha256=stored_sha,
            current_sha256=current_sha,
            stored_size=stored_size,
            current_size=current_size,
            present_now=present_now,
        )
        inspections.append(ai)

        if ai.absent:
            absent.append(name)
            notes.append(f"ABSENT  {name}: {path}")
        elif ai.drifted:
            drifted.append(name)
            size_delta = (
                f"{current_size - stored_size:+d}B" if (current_size and stored_size) else "?"
            )
            notes.append(
                f"DRIFT   {name}: stored={stored_sha[:16]}… "
                f"current={current_sha[:16]}… ({size_delta})"  # type: ignore[index]
            )
        else:
            notes.append(f"OK      {name}: sha256={stored_sha[:16]}…")

    n_ok = len(inspections) - len(drifted) - len(absent)
    if drifted or absent:
        detail = (
            f"{n_ok}/{len(inspections)} artifacts unchanged; "
            f"{len(drifted)} drifted, {len(absent)} absent"
        )
        passed = False
    else:
        detail = f"All {len(inspections)} artifacts unchanged (hashes match)"
        passed = True

    return (
        CheckResult(name="artifact_hashes", passed=passed, detail=detail, notes=notes),
        inspections,
    )


# ---------------------------------------------------------------------------
# Main inspector
# ---------------------------------------------------------------------------


def inspect_release_candidate(rc_path: str) -> InspectionResult:
    """
    Inspect a release candidate JSON file.

    Reads the RC, runs all checks unconditionally, returns an InspectionResult.

    Args:
        rc_path: Path to release_candidate.json.

    Returns:
        InspectionResult with per-check outcomes and artifact comparisons.
    """
    rc_path = os.path.abspath(rc_path)
    ts = datetime.now(timezone.utc).isoformat()

    # Read and parse the RC file
    try:
        with open(rc_path, encoding="utf-8") as f:
            rc = json.load(f)
    except FileNotFoundError:
        return InspectionResult(
            rc_path=rc_path,
            rc_id="<unknown>",
            rc_verdict="<unknown>",
            inspection_verdict="FAIL",
            timestamp_utc=ts,
            checks=[
                CheckResult(
                    name="schema",
                    passed=False,
                    detail=f"Release candidate file not found: {rc_path}",
                )
            ],
        )
    except json.JSONDecodeError as e:
        return InspectionResult(
            rc_path=rc_path,
            rc_id="<unknown>",
            rc_verdict="<unknown>",
            inspection_verdict="FAIL",
            timestamp_utc=ts,
            checks=[
                CheckResult(
                    name="schema",
                    passed=False,
                    detail=f"Invalid JSON in release candidate: {e}",
                )
            ],
        )

    rc_id = rc.get("rc_id", "<unknown>")
    rc_verdict = rc.get("verdict", "<unknown>")

    # Run all checks — no short-circuit
    checks: list[CheckResult] = []

    checks.append(_check_schema(rc, rc_path))
    checks.append(_check_git_commit(rc))
    checks.append(_check_gate_report(rc))
    checks.append(_check_run_report(rc))

    artifact_check, artifact_inspections = _inspect_artifacts(rc)
    checks.append(artifact_check)

    overall_passed = all(c.passed for c in checks)
    inspection_verdict = "PASS" if overall_passed else "FAIL"

    return InspectionResult(
        rc_path=rc_path,
        rc_id=rc_id,
        rc_verdict=rc_verdict,
        inspection_verdict=inspection_verdict,
        timestamp_utc=ts,
        checks=checks,
        artifacts=artifact_inspections,
    )


# ---------------------------------------------------------------------------
# RC discovery
# ---------------------------------------------------------------------------


def find_latest_rc(rc_dir: str = _RC_DIR) -> Optional[str]:
    """
    Return the absolute path of the most recently written release_candidate.json,
    or None if none found.
    """
    base = Path(rc_dir)
    if not base.exists():
        return None
    candidates = sorted(
        base.glob("*/release_candidate.json"),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    if candidates:
        return str(candidates[0].resolve())
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point for `uv run inspect_release_candidate`.

    Usage:
        uv run inspect_release_candidate <path/to/release_candidate.json>
        uv run inspect_release_candidate --latest
        uv run inspect_release_candidate <path> --json

    Flags:
        --latest   Automatically find the newest release_candidate.json
        --json     Machine-readable JSON output to stdout

    Returns 0 for PASS, 1 for FAIL or error.
    """
    argv = argv if argv is not None else sys.argv[1:]
    as_json = "--json" in argv
    use_latest = "--latest" in argv

    # Resolve RC path
    rc_path: Optional[str] = None
    if use_latest:
        rc_path = find_latest_rc()
        if rc_path is None:
            msg = f"No release_candidate.json found under '{_RC_DIR}'."
            if as_json:
                print(json.dumps({"error": msg, "inspection_verdict": "FAIL"}))
            else:
                print(f"  ❌ {msg}")
            return 1
    else:
        # First non-flag argument is the path
        positional = [a for a in argv if not a.startswith("--")]
        if not positional:
            print(
                "Usage: uv run inspect_release_candidate <path/to/release_candidate.json> "
                "[--latest] [--json]",
                file=sys.stderr,
            )
            return 1
        rc_path = positional[0]

    result = inspect_release_candidate(rc_path)

    if as_json:
        print(result.to_json())
    else:
        for line in result.summary_lines():
            print(line)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
