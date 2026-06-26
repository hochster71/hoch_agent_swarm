"""
tests/test_run_report.py — Unit tests for the RunReport module.

Coverage:
- RunReport construction and start()
- finish() sets status and completed_at
- add_error() accumulates errors and forces FAIL
- record_canonical_artifacts() — existence, size, sha256, validation_status
- record_archived_artifacts() — source/dest/size/sha256
- to_dict() / to_json() serialization
- write() produces a valid file with correct JSON
- No .env content or obvious secret strings appear in report JSON
- inputs_summary filtering in main._inputs_summary()
- _archive_existing_artifacts() return signature (pairs + report integration)
- run() writes a PASS report on success; FAIL report on crew exception

All tests use monkeypatching and temp dirs — no live LLM calls.
"""

import hashlib
import json
import os
import tempfile

import pytest

from hoch_agent_swarm.run_report import (
    RunReport,
    ArtifactRecord,
    ArchivedArtifactRecord,
    STATUS_PASS,
    STATUS_FAIL,
    _sha256,
    _file_size,
)
from hoch_agent_swarm.main import _inputs_summary, _archive_existing_artifacts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_temp_file(dir_path: str, name: str, content: str = "hello") -> str:
    path = os.path.join(dir_path, name)
    with open(path, "w") as f:
        f.write(content)
    return path


def _expected_sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


# ---------------------------------------------------------------------------
# _sha256 and _file_size helpers
# ---------------------------------------------------------------------------

class TestFileHelpers:

    def test_sha256_of_known_content(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        result = _sha256(str(f))
        assert result == hashlib.sha256(b"hello world").hexdigest()

    def test_sha256_missing_file_returns_none(self):
        assert _sha256("/nonexistent/path/to/file.txt") is None

    def test_file_size_known_content(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"abcde")
        assert _file_size(str(f)) == 5

    def test_file_size_missing_returns_none(self):
        assert _file_size("/nonexistent/path/to/file.txt") is None


# ---------------------------------------------------------------------------
# ArtifactRecord
# ---------------------------------------------------------------------------

class TestArtifactRecord:

    def test_existing_file(self, tmp_path):
        f = tmp_path / "artifact.md"
        f.write_text("# Report\n\nSome content.")
        rec = ArtifactRecord.from_path(str(f), validation_status="VALID")
        assert rec.exists is True
        assert rec.size_bytes == f.stat().st_size
        assert rec.sha256 == hashlib.sha256(b"# Report\n\nSome content.").hexdigest()
        assert rec.validation_status == "VALID"

    def test_missing_file(self, tmp_path):
        rec = ArtifactRecord.from_path(str(tmp_path / "nope.md"))
        assert rec.exists is False
        assert rec.size_bytes is None
        assert rec.sha256 is None
        assert rec.validation_status == "MISSING"

    def test_invalid_status_preserved(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text("garbage: lambda x: x")
        rec = ArtifactRecord.from_path(str(f), validation_status="INVALID")
        assert rec.validation_status == "INVALID"
        assert rec.exists is True


# ---------------------------------------------------------------------------
# ArchivedArtifactRecord
# ---------------------------------------------------------------------------

class TestArchivedArtifactRecord:

    def test_from_paths_hashes_dest(self, tmp_path):
        src = tmp_path / "orig.md"
        dst = tmp_path / "archive" / "orig.md"
        dst.parent.mkdir()
        src.write_text("original content")
        dst.write_text("original content")  # archive is a copy
        rec = ArchivedArtifactRecord.from_paths(str(src), str(dst))
        assert rec.source_path == str(src)
        assert rec.archived_path == str(dst)
        assert rec.sha256 == hashlib.sha256(b"original content").hexdigest()
        assert rec.size_bytes == len(b"original content")

    def test_missing_dest_returns_none_fields(self, tmp_path):
        rec = ArchivedArtifactRecord.from_paths("/src.md", "/missing/dest.md")
        assert rec.sha256 is None
        assert rec.size_bytes is None


# ---------------------------------------------------------------------------
# RunReport lifecycle
# ---------------------------------------------------------------------------

class TestRunReportLifecycle:

    def test_start_creates_report_with_pessimistic_status(self):
        r = RunReport.start(workflow_name="test_wf", inputs_summary={"topic": "AI"})
        assert r.status == STATUS_FAIL  # pessimistic default
        assert r.workflow_name == "test_wf"
        assert r.inputs_summary == {"topic": "AI"}
        assert r.completed_at is None
        assert r.errors == []
        assert isinstance(r.run_id, str) and len(r.run_id) == 36  # UUID4

    def test_finish_pass_sets_status_and_timestamp(self):
        r = RunReport.start(workflow_name="wf")
        r.finish(STATUS_PASS)
        assert r.status == STATUS_PASS
        assert r.completed_at is not None

    def test_finish_fail_preserves_fail(self):
        r = RunReport.start(workflow_name="wf")
        r.finish(STATUS_FAIL)
        assert r.status == STATUS_FAIL

    def test_add_error_forces_fail(self):
        r = RunReport.start(workflow_name="wf")
        r.add_error("something went wrong")
        assert r.status == STATUS_FAIL
        assert "something went wrong" in r.errors

    def test_add_multiple_errors_accumulates(self):
        r = RunReport.start(workflow_name="wf")
        r.add_error("error A")
        r.add_error("error B")
        assert len(r.errors) == 2

    def test_crewai_version_is_string(self):
        r = RunReport.start(workflow_name="wf")
        assert isinstance(r.crewai_version, str)
        assert len(r.crewai_version) > 0

    def test_python_version_is_plausible(self):
        r = RunReport.start(workflow_name="wf")
        major = int(r.python_version.split(".")[0])
        assert major >= 3

    def test_run_id_unique_per_call(self):
        r1 = RunReport.start(workflow_name="wf")
        r2 = RunReport.start(workflow_name="wf")
        assert r1.run_id != r2.run_id


# ---------------------------------------------------------------------------
# RunReport.record_canonical_artifacts
# ---------------------------------------------------------------------------

class TestRecordCanonicalArtifacts:

    def test_existing_artifact_captured(self, tmp_path):
        f = tmp_path / "sec.md"
        f.write_text("# Security Audit Report\n\nContent.")
        r = RunReport.start(workflow_name="wf")
        r.record_canonical_artifacts([str(f)], {str(f): "VALID"})
        assert len(r.canonical_artifacts) == 1
        rec = r.canonical_artifacts[0]
        assert rec["exists"] is True
        assert rec["validation_status"] == "VALID"
        assert rec["sha256"] is not None
        assert rec["size_bytes"] > 0

    def test_missing_artifact_captured_as_missing(self, tmp_path):
        missing = str(tmp_path / "nope.md")
        r = RunReport.start(workflow_name="wf")
        r.record_canonical_artifacts([missing])
        assert r.canonical_artifacts[0]["exists"] is False
        assert r.canonical_artifacts[0]["validation_status"] == "MISSING"

    def test_no_validation_defaults_to_not_validated(self, tmp_path):
        f = tmp_path / "artifact.md"
        f.write_text("content")
        r = RunReport.start(workflow_name="wf")
        r.record_canonical_artifacts([str(f)])
        assert r.canonical_artifacts[0]["validation_status"] == "NOT_VALIDATED"

    def test_multiple_paths_recorded(self, tmp_path):
        paths = [str(tmp_path / f"f{i}.md") for i in range(3)]
        for p in paths:
            with open(p, "w") as fh:
                fh.write("content")
        r = RunReport.start(workflow_name="wf")
        r.record_canonical_artifacts(paths)
        assert len(r.canonical_artifacts) == 3


# ---------------------------------------------------------------------------
# RunReport.record_archived_artifacts
# ---------------------------------------------------------------------------

class TestRecordArchivedArtifacts:

    def test_archived_pairs_captured(self, tmp_path):
        src = tmp_path / "orig.md"
        dst = tmp_path / "copy.md"
        src.write_text("original")
        dst.write_text("original")
        r = RunReport.start(workflow_name="wf")
        r.record_archived_artifacts([(str(src), str(dst))])
        assert len(r.archived_previous_artifacts) == 1
        rec = r.archived_previous_artifacts[0]
        assert rec["sha256"] is not None
        assert rec["size_bytes"] == len(b"original")

    def test_empty_pairs_is_valid(self):
        r = RunReport.start(workflow_name="wf")
        r.record_archived_artifacts([])
        assert r.archived_previous_artifacts == []


# ---------------------------------------------------------------------------
# RunReport serialization
# ---------------------------------------------------------------------------

class TestRunReportSerialization:

    def test_to_dict_is_json_serializable(self):
        r = RunReport.start(workflow_name="wf", inputs_summary={"topic": "AI"})
        r.finish(STATUS_PASS)
        d = r.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    def test_to_json_is_valid_json(self):
        r = RunReport.start(workflow_name="wf")
        r.finish(STATUS_PASS)
        parsed = json.loads(r.to_json())
        assert parsed["status"] == STATUS_PASS

    def test_write_creates_file(self, tmp_path):
        r = RunReport.start(workflow_name="wf", inputs_summary={"topic": "AI"})
        r.finish(STATUS_PASS)
        path = r.write(str(tmp_path))
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data["status"] == STATUS_PASS
        assert data["workflow_name"] == "wf"

    def test_write_creates_directory_if_missing(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        r = RunReport.start(workflow_name="wf")
        r.finish(STATUS_PASS)
        path = r.write(str(deep))
        assert os.path.isfile(path)

    def test_fail_report_includes_errors(self, tmp_path):
        r = RunReport.start(workflow_name="wf")
        r.add_error("validation failed")
        r.finish(STATUS_FAIL)
        path = r.write(str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert data["status"] == STATUS_FAIL
        assert "validation failed" in data["errors"]


# ---------------------------------------------------------------------------
# Security: no secret content in report
# ---------------------------------------------------------------------------

class TestNoSecretsInReport:

    BANNED_PATTERNS = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SERPER_API_KEY",
        "sk-",
        "Bearer ",
        "password",
        "secret",
    ]

    def _make_report_json(self) -> str:
        r = RunReport.start(
            workflow_name="wf",
            inputs_summary={
                "topic": "AI LLMs",
                "current_year": "2026",
            },
        )
        r.finish(STATUS_PASS)
        return r.to_json()

    def test_no_api_key_patterns_in_report(self):
        js = self._make_report_json().lower()
        for pattern in self.BANNED_PATTERNS:
            assert pattern.lower() not in js, (
                f"Banned pattern '{pattern}' found in run report JSON"
            )

    def test_inputs_summary_does_not_contain_trigger_payload_key(self):
        # Simulate a trigger payload being passed but filtered by _inputs_summary
        inputs = {
            "topic": "test",
            "current_year": "2026",
            "crewai_trigger_payload": {"some": "data"},  # should be stripped
        }
        summary = _inputs_summary(inputs)
        assert "crewai_trigger_payload" not in summary

    def test_inputs_summary_strips_key_containing_secret(self):
        inputs = {
            "topic": "test",
            "api_secret_key": "supersecret123",
            "token": "bearer123",
        }
        summary = _inputs_summary(inputs)
        for dangerous_key in ("api_secret_key", "token"):
            assert dangerous_key not in summary

    def test_inputs_summary_retains_safe_string_values(self):
        inputs = {
            "topic": "AI LLMs",
            "current_year": "2026",
            "antigravity_role": "planner",
        }
        summary = _inputs_summary(inputs)
        assert summary["topic"] == "AI LLMs"
        assert summary["current_year"] == "2026"

    def test_inputs_summary_drops_non_scalar_values(self):
        inputs = {
            "topic": "AI",
            "nested": {"a": "b"},   # dict — not a safe scalar
            "a_list": [1, 2, 3],    # list — not a safe scalar
        }
        summary = _inputs_summary(inputs)
        assert "nested" not in summary
        assert "a_list" not in summary


# ---------------------------------------------------------------------------
# _archive_existing_artifacts return value (pairs)
# ---------------------------------------------------------------------------

class TestArchiveReturnsPairs:

    def test_returns_empty_list_when_nothing_to_archive(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No canonical artifacts exist in tmp_path
        monkeypatch.setattr(
            "hoch_agent_swarm.main._CANONICAL_ARTIFACTS",
            [str(tmp_path / "nonexistent.md")],
        )
        pairs = _archive_existing_artifacts("20260101T000000")
        assert pairs == []

    def test_returns_pair_when_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "artifact.md"
        src.write_text("# content")
        monkeypatch.setattr(
            "hoch_agent_swarm.main._CANONICAL_ARTIFACTS",
            [str(src)],
        )
        monkeypatch.setattr(
            "hoch_agent_swarm.main._ARCHIVE_DIR",
            str(tmp_path / "crew_runs"),
        )
        pairs = _archive_existing_artifacts("20260101T000000")
        assert len(pairs) == 1
        src_path, dst_path = pairs[0]
        assert src_path == str(src)
        assert os.path.isfile(dst_path)


# ---------------------------------------------------------------------------
# run() integration — PASS and FAIL reports via monkeypatch
# ---------------------------------------------------------------------------

class TestRunWritesReport:

    def test_pass_report_written_on_success(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("hoch_agent_swarm.main._CANONICAL_ARTIFACTS", [])
        monkeypatch.setattr("hoch_agent_swarm.main._ARCHIVE_DIR", str(tmp_path / "crew_runs"))

        # Stub crew kickoff
        monkeypatch.setattr(
            "hoch_agent_swarm.main.HochAgentSwarm",
            lambda: type("C", (), {"crew": lambda s: type("Crew", (), {"kickoff": lambda s, inputs: None})()})(),
        )
        # Stub validation to succeed
        monkeypatch.setattr(
            "hoch_agent_swarm.main._run_validation",
            lambda: {},
        )
        # Stub default inputs
        monkeypatch.setattr(
            "hoch_agent_swarm.main._default_inputs",
            lambda topic="AI LLMs": {"topic": topic, "current_year": "2026"},
        )

        from hoch_agent_swarm.main import run
        run()

        # Find written report
        run_dirs = list((tmp_path / "crew_runs").iterdir())
        assert len(run_dirs) == 1
        report_file = run_dirs[0] / "run_report.json"
        assert report_file.exists()
        data = json.loads(report_file.read_text())
        assert data["status"] == STATUS_PASS
        assert data["errors"] == []

    def test_fail_report_written_on_crew_exception(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("hoch_agent_swarm.main._CANONICAL_ARTIFACTS", [])
        monkeypatch.setattr("hoch_agent_swarm.main._ARCHIVE_DIR", str(tmp_path / "crew_runs"))

        def _bad_crew():
            class Crew:
                def kickoff(self, inputs):
                    raise RuntimeError("LLM timeout")
            class C:
                def crew(self):
                    return Crew()
            return C()

        monkeypatch.setattr("hoch_agent_swarm.main.HochAgentSwarm", _bad_crew)
        monkeypatch.setattr(
            "hoch_agent_swarm.main._default_inputs",
            lambda topic="AI LLMs": {"topic": topic, "current_year": "2026"},
        )

        from hoch_agent_swarm.main import run
        with pytest.raises(Exception, match="LLM timeout"):
            run()

        run_dirs = list((tmp_path / "crew_runs").iterdir())
        assert len(run_dirs) == 1
        report_file = run_dirs[0] / "run_report.json"
        assert report_file.exists()
        data = json.loads(report_file.read_text())
        assert data["status"] == STATUS_FAIL
        assert len(data["errors"]) > 0
