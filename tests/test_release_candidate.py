"""
tests/test_release_candidate.py — Unit tests for release_candidate.py

All git subprocesses and filesystem reads are monkeypatched.
No live git, no live crew, no live filesystem writes except via tmp_path.
"""
from __future__ import annotations

import json
import os

import pytest

from hoch_agent_swarm.release_candidate import (
    ArtifactEntry,
    RCResult,
    build_release_candidate,
    check_git_clean,
    collect_artifact_entries,
    find_latest_gate_report,
    find_latest_run_report,
    get_git_metadata,
    main,
    read_gate_report,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_gate_report(tmp_path, verdict: str = "PASS", subdir: str = "20260626T010101") -> str:
    """Write a minimal quality_gate_report.json and return its path."""
    run_dir = tmp_path / "crew_runs" / subdir
    run_dir.mkdir(parents=True)
    report = {
        "run_id": "test-uuid",
        "timestamp_utc": "2026-06-26T01:01:01Z",
        "verdict": verdict,
        "passed": verdict == "PASS",
        "live_run_included": True,
        "run_report_path": str(run_dir / "run_report.json"),
        "steps": [],
    }
    path = run_dir / "quality_gate_report.json"
    path.write_text(json.dumps(report))
    return str(path)


def _make_run_report(tmp_path, subdir: str = "20260626T010101") -> str:
    """Write a minimal run_report.json and return its path."""
    run_dir = tmp_path / "crew_runs" / subdir
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {"run_id": "test-run-uuid", "verdict": "PASS"}
    path = run_dir / "run_report.json"
    path.write_text(json.dumps(report))
    return str(path)


def _make_canonical_artifacts(tmp_path) -> dict[str, str]:
    """Create minimal canonical artifact files and return their paths."""
    paths = {}
    for name in ("plan", "report", "summary"):
        f = tmp_path / f"{name}.md"
        f.write_text(f"# {name}\n\nContent for {name}.\n")
        paths[name] = str(f)
    return paths


def _mock_git_clean(monkeypatch, clean: bool = True):
    monkeypatch.setattr(
        "hoch_agent_swarm.release_candidate.check_git_clean",
        lambda: None if clean else "working tree is dirty",
    )


def _mock_git_meta(monkeypatch, commit: str = "abc1234abcd5678"):
    monkeypatch.setattr(
        "hoch_agent_swarm.release_candidate.get_git_metadata",
        lambda: {
            "commit": commit,
            "commit_short": commit[:7],
            "commit_message": "feat: test commit",
            "branch": "master",
            "tag": None,
        },
    )


# ---------------------------------------------------------------------------
# ArtifactEntry
# ---------------------------------------------------------------------------


class TestArtifactEntry:
    def test_to_dict_fields(self):
        e = ArtifactEntry(
            path="a/b.md",
            sha256="abc123",
            size_bytes=42,
            present=True,
        )
        d = e.to_dict()
        assert d["path"] == "a/b.md"
        assert d["sha256"] == "abc123"
        assert d["size_bytes"] == 42
        assert d["present"] is True

    def test_absent_entry(self):
        e = ArtifactEntry(path="missing.md", sha256=None, size_bytes=None, present=False)
        d = e.to_dict()
        assert d["present"] is False
        assert d["sha256"] is None


# ---------------------------------------------------------------------------
# RCResult
# ---------------------------------------------------------------------------


class TestRCResult:
    def test_passed_when_no_blocked_and_path_set(self):
        r = RCResult(rc_path="/some/path.json", blocked_by=[], data={})
        assert r.passed is True

    def test_not_passed_when_blocked(self):
        r = RCResult(rc_path=None, blocked_by=["git dirty"], data={})
        assert r.passed is False

    def test_not_passed_when_no_path(self):
        r = RCResult(rc_path=None, blocked_by=[], data={})
        assert r.passed is False

    def test_summary_lines_pass(self):
        r = RCResult(rc_path="/some/release_candidate.json", blocked_by=[], data={})
        combined = "\n".join(r.summary_lines())
        assert "PASS" in combined
        assert "/some/release_candidate.json" in combined

    def test_summary_lines_blocked(self):
        r = RCResult(rc_path=None, blocked_by=["git dirty", "no gate report"], data={})
        combined = "\n".join(r.summary_lines())
        assert "BLOCKED" in combined
        assert "git dirty" in combined
        assert "no gate report" in combined

    def test_to_json_serializable(self):
        r = RCResult(
            rc_path=None,
            blocked_by=["reason"],
            data={"verdict": "BLOCKED", "blocked_by": ["reason"]},
        )
        parsed = json.loads(r.to_json())
        assert parsed["verdict"] == "BLOCKED"


# ---------------------------------------------------------------------------
# check_git_clean
# ---------------------------------------------------------------------------


class TestCheckGitClean:
    def test_clean_when_no_porcelain_output(self, monkeypatch):
        import subprocess as sp
        monkeypatch.setattr(
            "hoch_agent_swarm.release_candidate.subprocess.run",
            lambda *a, **kw: sp.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        )
        result = check_git_clean()
        assert result is None

    def test_dirty_when_porcelain_output(self, monkeypatch):
        import subprocess as sp
        monkeypatch.setattr(
            "hoch_agent_swarm.release_candidate.subprocess.run",
            lambda *a, **kw: sp.CompletedProcess(
                args=[], returncode=0, stdout=" M src/foo.py\n", stderr=""
            ),
        )
        result = check_git_clean()
        assert result is not None
        assert "not clean" in result

    def test_error_on_subprocess_failure(self, monkeypatch):
        import subprocess as sp
        def _fail(*a, **kw):
            raise sp.CalledProcessError(128, "git", stderr="not a git repo")
        monkeypatch.setattr("hoch_agent_swarm.release_candidate.subprocess.run", _fail)
        result = check_git_clean()
        assert result is not None
        assert "git status failed" in result


# ---------------------------------------------------------------------------
# get_git_metadata
# ---------------------------------------------------------------------------


class TestGetGitMetadata:
    def test_returns_expected_fields(self, monkeypatch):
        import subprocess as sp
        call_count = {"n": 0}
        outputs = [
            "abc1234abcd5678",           # rev-parse HEAD
            "feat: test commit",         # log -1 --format=%s
            "master",                    # rev-parse --abbrev-ref HEAD
        ]
        def _fake_run(*a, **kw):
            n = call_count["n"]
            call_count["n"] += 1
            if n < len(outputs):
                return sp.CompletedProcess(args=[], returncode=0, stdout=outputs[n], stderr="")
            # describe --tags fails (no tag)
            raise sp.CalledProcessError(128, "git", stderr="no tag")
        monkeypatch.setattr("hoch_agent_swarm.release_candidate.subprocess.run", _fake_run)
        meta = get_git_metadata()
        assert meta["commit"] == "abc1234abcd5678"
        assert meta["commit_short"] == "abc1234"
        assert meta["branch"] == "master"
        assert meta["commit_message"] == "feat: test commit"
        assert meta["tag"] is None

    def test_returns_error_key_on_failure(self, monkeypatch):
        import subprocess as sp
        monkeypatch.setattr(
            "hoch_agent_swarm.release_candidate.subprocess.run",
            lambda *a, **kw: (_ for _ in ()).throw(
                sp.CalledProcessError(128, "git", stderr="fatal: not a repo")
            ),
        )
        meta = get_git_metadata()
        assert "error" in meta


# ---------------------------------------------------------------------------
# find_latest_gate_report / find_latest_run_report
# ---------------------------------------------------------------------------


class TestFindLatestGateReport:
    def test_returns_none_when_dir_missing(self, tmp_path):
        result = find_latest_gate_report(str(tmp_path / "nonexistent"))
        assert result is None

    def test_returns_none_when_no_reports(self, tmp_path):
        (tmp_path / "crew_runs").mkdir()
        result = find_latest_gate_report(str(tmp_path / "crew_runs"))
        assert result is None

    def test_returns_latest_by_timestamp(self, tmp_path):
        runs = tmp_path / "crew_runs"
        _make_gate_report(tmp_path, subdir="20260626T010000")
        _make_gate_report(tmp_path, subdir="20260626T020000")
        _make_gate_report(tmp_path, subdir="20260626T030000")
        result = find_latest_gate_report(str(runs))
        assert result is not None
        assert "20260626T030000" in result

    def test_returns_absolute_path(self, tmp_path):
        _make_gate_report(tmp_path, subdir="20260626T010000")
        result = find_latest_gate_report(str(tmp_path / "crew_runs"))
        assert result is not None
        assert os.path.isabs(result)


class TestFindLatestRunReport:
    def test_returns_none_when_dir_missing(self, tmp_path):
        result = find_latest_run_report(str(tmp_path / "nonexistent"))
        assert result is None

    def test_returns_latest_by_timestamp(self, tmp_path):
        runs = tmp_path / "crew_runs"
        _make_run_report(tmp_path, subdir="20260626T010000")
        _make_run_report(tmp_path, subdir="20260626T040000")
        result = find_latest_run_report(str(runs))
        assert result is not None
        assert "20260626T040000" in result


# ---------------------------------------------------------------------------
# collect_artifact_entries
# ---------------------------------------------------------------------------


class TestCollectArtifactEntries:
    def test_present_entries_have_sha(self, tmp_path):
        paths = _make_canonical_artifacts(tmp_path)
        entries = collect_artifact_entries(canonical_paths=paths)
        for name, entry in entries.items():
            assert entry.present is True
            assert entry.sha256 is not None
            assert len(entry.sha256) == 64

    def test_absent_entries_have_no_sha(self, tmp_path):
        paths = {"missing": str(tmp_path / "does_not_exist.md")}
        entries = collect_artifact_entries(canonical_paths=paths)
        assert entries["missing"].present is False
        assert entries["missing"].sha256 is None
        assert entries["missing"].size_bytes is None

    def test_size_bytes_correct(self, tmp_path):
        content = "# Test\n\nSome content.\n"
        f = tmp_path / "artifact.md"
        f.write_text(content)
        entries = collect_artifact_entries(canonical_paths={"a": str(f)})
        assert entries["a"].size_bytes == len(content.encode())

    def test_sha_changes_with_content(self, tmp_path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("# A\n")
        f2.write_text("# B\n")
        e1 = collect_artifact_entries({"x": str(f1)})
        e2 = collect_artifact_entries({"x": str(f2)})
        assert e1["x"].sha256 != e2["x"].sha256


# ---------------------------------------------------------------------------
# read_gate_report
# ---------------------------------------------------------------------------


class TestReadGateReport:
    def test_reads_valid_report(self, tmp_path):
        p = tmp_path / "quality_gate_report.json"
        p.write_text(json.dumps({"verdict": "PASS", "passed": True}))
        data = read_gate_report(str(p))
        assert data["verdict"] == "PASS"

    def test_raises_on_missing_verdict(self, tmp_path):
        p = tmp_path / "quality_gate_report.json"
        p.write_text(json.dumps({"passed": True}))
        with pytest.raises(ValueError, match="missing 'verdict'"):
            read_gate_report(str(p))

    def test_raises_on_invalid_json(self, tmp_path):
        p = tmp_path / "quality_gate_report.json"
        p.write_text("not json {{{")
        with pytest.raises(json.JSONDecodeError):
            read_gate_report(str(p))


# ---------------------------------------------------------------------------
# build_release_candidate — gate blocking
# ---------------------------------------------------------------------------


class TestBuildReleaseCandidateBlocking:
    def test_blocked_when_git_dirty(self, tmp_path, monkeypatch):
        _mock_git_meta(monkeypatch)
        monkeypatch.setattr(
            "hoch_agent_swarm.release_candidate.check_git_clean",
            lambda: "working tree is dirty",
        )
        _make_gate_report(tmp_path)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
        )
        assert not result.passed
        assert any("not clean" in b or "dirty" in b for b in result.blocked_by)
        assert result.rc_path is None

    def test_blocked_when_no_gate_report(self, tmp_path, monkeypatch):
        _mock_git_clean(monkeypatch, clean=True)
        _mock_git_meta(monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
        )
        assert not result.passed
        assert any("quality_gate_report.json" in b for b in result.blocked_by)

    def test_blocked_when_gate_verdict_fail(self, tmp_path, monkeypatch):
        _mock_git_clean(monkeypatch, clean=True)
        _mock_git_meta(monkeypatch)
        _make_gate_report(tmp_path, verdict="FAIL")
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
        )
        assert not result.passed
        assert any("FAIL" in b for b in result.blocked_by)

    def test_blocked_when_artifact_missing(self, tmp_path, monkeypatch):
        _mock_git_clean(monkeypatch, clean=True)
        _mock_git_meta(monkeypatch)
        _make_gate_report(tmp_path)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths={"missing_artifact": str(tmp_path / "does_not_exist.md")},
        )
        assert not result.passed
        assert any("missing" in b for b in result.blocked_by)

    def test_no_file_written_when_blocked(self, tmp_path, monkeypatch):
        _mock_git_clean(monkeypatch, clean=True)
        _mock_git_meta(monkeypatch)
        # No gate report = blocked
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
        )
        rc_dir = tmp_path / "rc"
        assert not result.passed
        # rc_dir should be empty (no file written)
        assert not any(rc_dir.rglob("release_candidate.json"))

    def test_multiple_block_reasons_collected(self, tmp_path, monkeypatch):
        """All blocking conditions are collected, not short-circuited."""
        monkeypatch.setattr(
            "hoch_agent_swarm.release_candidate.check_git_clean",
            lambda: "dirty",
        )
        _mock_git_meta(monkeypatch)
        # No gate report and missing artifact
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths={"missing": str(tmp_path / "nope.md")},
        )
        assert len(result.blocked_by) >= 3  # dirty + no gate report + missing artifact


# ---------------------------------------------------------------------------
# build_release_candidate — success path
# ---------------------------------------------------------------------------


class TestBuildReleaseCandidateSuccess:
    def _setup(self, tmp_path, monkeypatch):
        _mock_git_clean(monkeypatch, clean=True)
        _mock_git_meta(monkeypatch)
        _make_gate_report(tmp_path)
        _make_run_report(tmp_path)
        paths = _make_canonical_artifacts(tmp_path)
        return paths

    def test_passes_when_all_gates_clear(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        assert result.passed
        assert result.rc_path is not None
        assert result.blocked_by == []

    def test_writes_json_file(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        assert result.rc_path is not None
        assert os.path.isfile(result.rc_path)

    def test_json_is_valid(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        assert data["verdict"] == "PASS"

    def test_rc_contains_expected_fields(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        for key in (
            "rc_id", "timestamp_utc", "verdict", "blocked_by",
            "git", "crewai_version", "mcp_version", "python_version",
            "gate_verdict", "gate_report_path", "run_report_path", "artifacts",
        ):
            assert key in data, f"Missing key: {key}"

    def test_git_commit_in_rc(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        assert data["git"]["commit"] == "abc1234abcd5678"
        assert data["git"]["branch"] == "master"

    def test_artifact_hashes_in_rc(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        for name in paths:
            assert name in data["artifacts"]
            assert data["artifacts"][name]["sha256"] is not None
            assert data["artifacts"][name]["present"] is True

    def test_gate_verdict_pass_in_rc(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        assert data["gate_verdict"] == "PASS"

    def test_run_report_path_linked(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        assert data["run_report_path"] is not None
        assert "run_report.json" in data["run_report_path"]

    def test_rc_id_is_uuid(self, tmp_path, monkeypatch):
        import uuid as _uuid
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        _uuid.UUID(data["rc_id"])  # Should not raise

    def test_blocked_by_empty_on_success(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        with open(result.rc_path) as f:
            data = json.load(f)
        assert data["blocked_by"] == []

    def test_rc_written_in_timestamped_subdir(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        rc_dir = tmp_path / "rc"
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(rc_dir),
            canonical_paths=paths,
        )
        assert result.rc_path is not None
        # parent dir should be a timestamp subdir under rc_dir
        parent = os.path.dirname(result.rc_path)
        assert os.path.dirname(parent) == str(rc_dir.resolve())

    def test_rc_path_is_absolute(self, tmp_path, monkeypatch):
        paths = self._setup(tmp_path, monkeypatch)
        result = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        assert os.path.isabs(result.rc_path)

    def test_two_runs_produce_different_rc_ids(self, tmp_path, monkeypatch):
        import uuid as _uuid
        paths = self._setup(tmp_path, monkeypatch)
        r1 = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        r2 = build_release_candidate(
            crew_runs_dir=str(tmp_path / "crew_runs"),
            rc_dir=str(tmp_path / "rc"),
            canonical_paths=paths,
        )
        # Read rc_id from in-memory data — files may share a timestamp path
        id1 = r1.data["rc_id"]
        id2 = r2.data["rc_id"]
        # Both should be valid UUIDs
        _uuid.UUID(id1)
        _uuid.UUID(id2)
        # And distinct (generated per call)
        assert id1 != id2


# ---------------------------------------------------------------------------
# main() — CLI
# ---------------------------------------------------------------------------


def _stub_build(monkeypatch, passed: bool = True, tmp_path=None):
    """Stub build_release_candidate for main() tests."""
    rc_path = "/fake/rc/release_candidate.json" if passed else None
    data = {
        "verdict": "PASS" if passed else "BLOCKED",
        "blocked_by": [] if passed else ["git dirty"],
        "rc_id": "test-uuid",
    }
    result = RCResult(
        rc_path=rc_path,
        blocked_by=[] if passed else ["git dirty"],
        data=data,
    )
    monkeypatch.setattr(
        "hoch_agent_swarm.release_candidate.build_release_candidate",
        lambda **kw: result,
    )
    return result


class TestMain:
    def test_exit_0_on_pass(self, monkeypatch, capsys):
        _stub_build(monkeypatch, passed=True)
        code = main([])
        assert code == 0

    def test_exit_1_on_blocked(self, monkeypatch, capsys):
        _stub_build(monkeypatch, passed=False)
        code = main([])
        assert code == 1

    def test_json_flag_outputs_valid_json(self, monkeypatch, capsys):
        _stub_build(monkeypatch, passed=True)
        code = main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "verdict" in parsed
        assert code == 0

    def test_json_blocked_outputs_valid_json(self, monkeypatch, capsys):
        _stub_build(monkeypatch, passed=False)
        code = main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["verdict"] == "BLOCKED"
        assert code == 1

    def test_human_output_contains_pass(self, monkeypatch, capsys):
        _stub_build(monkeypatch, passed=True)
        main([])
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_human_output_contains_blocked(self, monkeypatch, capsys):
        _stub_build(monkeypatch, passed=False)
        main([])
        captured = capsys.readouterr()
        assert "BLOCKED" in captured.out
