"""
run_report.py — Structured, JSON-serializable crew run metadata.

A RunReport is written to artifacts/crew_runs/<timestamp>/run_report.json
after every crew invocation (success or failure).  It provides a
machine-checkable audit record that supports before/after comparison for
any CrewAI version change.

No secrets, .env values, full prompts, or full artifact contents are recorded.

Usage (internal — called by main.py):
    from hoch_agent_swarm.run_report import RunReport
    report = RunReport.start(workflow_name="hoch_agent_swarm", inputs_summary={...})
    ...crew execution...
    report.record_artifacts(canonical_paths, archived_metadata)
    report.finish(status="PASS")
    report.write(run_dir)
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import uuid

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: str) -> Optional[str]:
    """Return the hex SHA-256 digest of a file, or None if the file is absent."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _file_size(path: str) -> Optional[int]:
    """Return the size in bytes of a file, or None if the file is absent."""
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _crewai_version() -> str:
    try:
        import crewai
        return crewai.__version__
    except Exception:
        return "unknown"


def _mcp_stub_version() -> str:
    try:
        import mcp
        return getattr(mcp, "__version__", "no version")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Sub-record dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ArtifactRecord:
    """Metadata for one canonical artifact path."""
    path: str
    exists: bool
    size_bytes: Optional[int]
    sha256: Optional[str]
    validation_status: str  # "VALID", "INVALID", "NOT_VALIDATED", "MISSING"

    @classmethod
    def from_path(cls, path: str, validation_status: str = "NOT_VALIDATED") -> "ArtifactRecord":
        exists = os.path.isfile(path)
        return cls(
            path=path,
            exists=exists,
            size_bytes=_file_size(path) if exists else None,
            sha256=_sha256(path) if exists else None,
            validation_status=validation_status if exists else "MISSING",
        )


@dataclass
class ArchivedArtifactRecord:
    """Metadata for one artifact that was archived before being overwritten."""
    source_path: str
    archived_path: str
    size_bytes: Optional[int]
    sha256: Optional[str]

    @classmethod
    def from_paths(cls, source_path: str, archived_path: str) -> "ArchivedArtifactRecord":
        return cls(
            source_path=source_path,
            archived_path=archived_path,
            size_bytes=_file_size(archived_path),
            sha256=_sha256(archived_path),
        )


# ---------------------------------------------------------------------------
# RunReport
# ---------------------------------------------------------------------------


@dataclass
class RunReport:
    """
    Complete metadata record for a single crew execution.

    Invariants:
      - run_id is a UUID4 string, unique per invocation.
      - started_at and completed_at are ISO 8601 UTC strings.
      - status is "PASS" or "FAIL".
      - errors is an empty list on PASS; populated list on FAIL.
      - No secret values, .env contents, or full artifact bodies are stored.
    """

    run_id: str
    started_at: str
    completed_at: Optional[str]
    status: str
    crewai_version: str
    mcp_stub_version: str
    python_version: str
    workflow_name: str
    inputs_summary: dict
    canonical_artifacts: list = field(default_factory=list)
    archived_previous_artifacts: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def start(
        cls,
        workflow_name: str,
        inputs_summary: Optional[dict] = None,
    ) -> "RunReport":
        """
        Create a new RunReport at the moment a crew run begins.
        `inputs_summary` should contain only safe, non-secret scalar values.
        """
        return cls(
            run_id=str(uuid.uuid4()),
            started_at=_utc_now(),
            completed_at=None,
            status=STATUS_FAIL,          # default pessimistic; set to PASS on success
            crewai_version=_crewai_version(),
            mcp_stub_version=_mcp_stub_version(),
            python_version=sys.version.split()[0],
            workflow_name=workflow_name,
            inputs_summary=inputs_summary or {},
            canonical_artifacts=[],
            archived_previous_artifacts=[],
            errors=[],
        )

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def record_canonical_artifacts(
        self,
        paths: list[str],
        validation_results: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Record metadata for each canonical artifact path.

        Args:
            paths: list of canonical artifact file paths.
            validation_results: optional map of path → validation_status string.
        """
        vr = validation_results or {}
        self.canonical_artifacts = [
            asdict(ArtifactRecord.from_path(p, vr.get(p, "NOT_VALIDATED")))
            for p in paths
        ]

    def record_archived_artifacts(
        self,
        archived_pairs: list[tuple[str, str]],
    ) -> None:
        """
        Record metadata for artifacts that were archived before overwrite.

        Args:
            archived_pairs: list of (source_path, archived_path) tuples.
        """
        self.archived_previous_artifacts = [
            asdict(ArchivedArtifactRecord.from_paths(src, dst))
            for src, dst in archived_pairs
        ]

    def add_error(self, message: str) -> None:
        """Append an error message. Switches status to FAIL if not already."""
        self.errors.append(message)
        self.status = STATUS_FAIL

    def finish(self, status: str) -> None:
        """Mark the run as complete with the given status and record completion time."""
        self.status = status
        self.completed_at = _utc_now()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return the report as a plain dict (all values JSON-serializable)."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Return the report as a pretty-printed JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def write(self, run_dir: str, filename: str = "run_report.json") -> str:
        """
        Write the report to <run_dir>/<filename>.

        Creates run_dir if it does not exist.
        Returns the absolute path of the written file.
        """
        os.makedirs(run_dir, exist_ok=True)
        dest = os.path.join(run_dir, filename)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return os.path.abspath(dest)
