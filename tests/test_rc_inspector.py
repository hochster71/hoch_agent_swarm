"""
tests/test_rc_inspector.py — Unit tests for rc_inspector.py

All git subprocesses are monkeypatched.
Filesystem fixtures use tmp_path only.
No live git, no live crew, no live network.
"""
from __future__ import annotations

import json
import os
import subprocess

import pytest

from hoch_agent_swarm.rc_inspector import (
    ArtifactInspection,
    CheckResult,
    InspectionResult,
    _check_gate_report,
    _check_git_commit,
    _check_run_report,
    _check_schema,
    _inspect_artifacts,
    find_latest_rc,
    inspect_release_candidate,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_REQUIRED_KEYS = (
    "rc_id", "timestamp_utc", "verdict", "blocked_by", "git",
    "crewai_version", "mcp_version", "python_version",
    "gate_verdict", "gate_report_path", "run_report_path", "artifacts",
)


def _make_artifact_file(tmp_path, name: str = "artifact.md", content: str = "# A\n") -> str:
    f = tmp_path / name
    f.write_text(content)
    return str(f)


def _sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _make_gate_report(tmp_path, verdict: str = "PASS") -> str:
    p = tmp_path / "quality_gate_report.json"
    p.write_text(json.dumps({
        "verdict": verdict,
        "run_id": "gate-run-uuid",
        "passed": verdict == "PASS",
    }))
    return str(p)


def _make_run_report(tmp_path) -> str:
    p = tmp_path / "run_report.json"
    p.write_text(json.dumps({"run_id": "run-uuid", "verdict": "PASS"}))
    return str(p)


def _make_rc(
    tmp_path,
    *,
    artifact_content: str = "# A\n\nSome content.\n",
    gate_verdict: str = "PASS",
    rc_id: str = "test-rc-id",
    commit: str = "abc1234abcd5678",
    extra_keys: dict | None = None,
    drop_keys: list[str] | None = None,
) -> tuple[str, dict]:
    """
    Build a complete release_candidate.json in tmp_path.

    Returns (path_str, rc_dict).
    """
    art_path = _make_artifact_file(tmp_path, content=artifact_content)
    gate_path = _make_gate_report(tmp_path, verdict=gate_verdict)
    run_path = _make_run_report(tmp_path)
    sha = _sha256(art_path)
    size = os.path.getsize(art_path)

    rc: dict = {
        "rc_id": rc_id,
        "timestamp_utc": "2026-06-26T01:00:00Z",
        "verdict": "PASS",
        "blocked_by": [],
        "git": {
            "commit": commit,
            "commit_short": commit[:7],
            "commit_message": "feat: test",
            "branch": "master",
            "tag": None,
        },
        "crewai_version": "1.15.0",
        "mcp_version": "1.26.0",
        "python_version": "3.13.0",
        "gate_verdict": gate_verdict,
        "gate_report_path": gate_path,
        "run_report_path": run_path,
        "artifacts": {
            "test_artifact": {
                "path": art_path,
                "sha256": sha,
                "size_bytes": size,
                "present": True,
            }
        },
    }

    if extra_keys:
        rc.update(extra_keys)
    if drop_keys:
        for k in drop_keys:
            rc.pop(k, None)

    rc_path = tmp_path / "release_candidate.json"
    rc_path.write_text(json.dumps(rc))
    return str(rc_path), rc


def _mock_git_commit_found(monkeypatch, commit: str = "abc1234abcd5678"):
    monkeypatch.setattr(
        "hoch_agent_swarm.rc_inspector.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="commit\n", stderr=""
        ),
    )


def _mock_git_commit_not_found(monkeypatch):
    def _fail(*a, **kw):
        raise subprocess.CalledProcessError(128, "git", stderr="not found")
    monkeypatch.setattr("hoch_agent_swarm.rc_inspector.subprocess.run", _fail)


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------


class TestCheckResult:
    def test_to_dict_basic(self):
        c = CheckResult(name="foo", passed=True, detail="ok")
        d = c.to_dict()
        assert d["name"] == "foo"
        assert d["passed"] is True
        assert d["detail"] == "ok"
        assert "notes" not in d  # omitted when empty

    def test_to_dict_with_notes(self):
        c = CheckResult(name="bar", passed=False, detail="bad", notes=["line1", "line2"])
        d = c.to_dict()
        assert d["notes"] == ["line1", "line2"]


# ---------------------------------------------------------------------------
# ArtifactInspection
# ---------------------------------------------------------------------------


class TestArtifactInspection:
    def test_ok_when_hash_matches(self):
        ai = ArtifactInspection(
            name="a", path="/p",
            stored_sha256="abc", current_sha256="abc",
            stored_size=10, current_size=10,
            present_now=True,
        )
        assert ai.ok is True
        assert ai.drifted is False
        assert ai.absent is False

    def test_drifted_when_hash_differs(self):
        ai = ArtifactInspection(
            name="a", path="/p",
            stored_sha256="aaa", current_sha256="bbb",
            stored_size=10, current_size=12,
            present_now=True,
        )
        assert ai.drifted is True
        assert ai.ok is False
        assert ai.absent is False

    def test_absent_when_not_present(self):
        ai = ArtifactInspection(
            name="a", path="/missing",
            stored_sha256="aaa", current_sha256=None,
            stored_size=10, current_size=None,
            present_now=False,
        )
        assert ai.absent is True
        assert ai.ok is False
        assert ai.drifted is False  # absent takes precedence

    def test_to_dict_fields(self):
        ai = ArtifactInspection(
            name="x", path="/x",
            stored_sha256="s", current_sha256="s",
            stored_size=5, current_size=5,
            present_now=True,
        )
        d = ai.to_dict()
        for key in ("name", "path", "stored_sha256", "current_sha256", "present_now",
                    "drifted", "absent", "ok"):
            assert key in d


# ---------------------------------------------------------------------------
# InspectionResult
# ---------------------------------------------------------------------------


class TestInspectionResult:
    def _make(self, passed: bool = True) -> InspectionResult:
        checks = [CheckResult(name="schema", passed=passed, detail="ok")]
        return InspectionResult(
            rc_path="/rc.json",
            rc_id="test-id",
            rc_verdict="PASS",
            inspection_verdict="PASS" if passed else "FAIL",
            timestamp_utc="2026-06-26T00:00:00Z",
            checks=checks,
        )

    def test_passed_true(self):
        r = self._make(passed=True)
        assert r.passed is True

    def test_passed_false(self):
        r = self._make(passed=False)
        assert r.passed is False

    def test_to_dict_required_fields(self):
        r = self._make()
        d = r.to_dict()
        for k in ("rc_path", "rc_id", "rc_verdict", "inspection_verdict",
                  "timestamp_utc", "passed", "checks", "artifacts",
                  "drifted_artifacts", "absent_artifacts"):
            assert k in d

    def test_to_json_valid(self):
        r = self._make()
        parsed = json.loads(r.to_json())
        assert parsed["inspection_verdict"] == "PASS"

    def test_summary_lines_pass(self):
        r = self._make(passed=True)
        combined = "\n".join(r.summary_lines())
        assert "PASS" in combined
        assert "✅" in combined

    def test_summary_lines_fail(self):
        r = self._make(passed=False)
        combined = "\n".join(r.summary_lines())
        assert "FAIL" in combined
        assert "❌" in combined

    def test_drifted_artifacts_listed(self):
        ai = ArtifactInspection(
            name="x", path="/x",
            stored_sha256="aaa", current_sha256="bbb",
            stored_size=10, current_size=10,
            present_now=True,
        )
        r = InspectionResult(
            rc_path="/rc.json", rc_id="id", rc_verdict="PASS",
            inspection_verdict="FAIL", timestamp_utc="ts",
            artifacts=[ai],
        )
        assert "x" in r.drifted_artifacts
        combined = "\n".join(r.summary_lines())
        assert "x" in combined

    def test_absent_artifacts_listed(self):
        ai = ArtifactInspection(
            name="gone", path="/gone",
            stored_sha256="aaa", current_sha256=None,
            stored_size=10, current_size=None,
            present_now=False,
        )
        r = InspectionResult(
            rc_path="/rc.json", rc_id="id", rc_verdict="PASS",
            inspection_verdict="FAIL", timestamp_utc="ts",
            artifacts=[ai],
        )
        assert "gone" in r.absent_artifacts


# ---------------------------------------------------------------------------
# _check_schema
# ---------------------------------------------------------------------------


class TestCheckSchema:
    def test_passes_on_valid_rc(self, tmp_path):
        _, rc = _make_rc(tmp_path)
        result = _check_schema(rc, str(tmp_path / "release_candidate.json"))
        assert result.passed is True
        assert "12" in result.detail

    def test_fails_on_missing_top_level_key(self, tmp_path):
        _, rc = _make_rc(tmp_path, drop_keys=["rc_id"])
        result = _check_schema(rc, "")
        assert result.passed is False
        assert "rc_id" in result.detail

    def test_fails_on_multiple_missing_keys(self, tmp_path):
        _, rc = _make_rc(tmp_path, drop_keys=["rc_id", "verdict"])
        result = _check_schema(rc, "")
        assert result.passed is False

    def test_fails_when_artifacts_not_dict(self, tmp_path):
        _, rc = _make_rc(tmp_path)
        rc["artifacts"] = "not_a_dict"
        result = _check_schema(rc, "")
        assert result.passed is False

    def test_fails_when_artifact_entry_missing_key(self, tmp_path):
        _, rc = _make_rc(tmp_path)
        rc["artifacts"]["test_artifact"].pop("sha256")
        result = _check_schema(rc, "")
        assert result.passed is False
        assert "sha256" in "\n".join(result.notes)

    def test_multiple_artifact_entries_all_validated(self, tmp_path):
        _, rc = _make_rc(tmp_path)
        rc["artifacts"]["second"] = {"path": "/p"}  # missing keys
        result = _check_schema(rc, "")
        assert result.passed is False


# ---------------------------------------------------------------------------
# _check_git_commit
# ---------------------------------------------------------------------------


class TestCheckGitCommit:
    def test_passes_when_commit_found(self, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc = {"git": {"commit": "abc1234abcd5678", "commit_message": "msg", "branch": "master"}}
        result = _check_git_commit(rc)
        assert result.passed is True
        assert "abc1234" in result.detail

    def test_fails_when_commit_missing_from_git(self, monkeypatch):
        _mock_git_commit_not_found(monkeypatch)
        rc = {"git": {"commit": "deadbeef1234567", "branch": "master"}}
        result = _check_git_commit(rc)
        assert result.passed is False
        assert "not found" in result.detail

    def test_fails_when_no_commit_field(self, monkeypatch):
        rc = {"git": {}}
        result = _check_git_commit(rc)
        assert result.passed is False
        assert "No 'commit'" in result.detail

    def test_fails_when_object_type_wrong(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.rc_inspector.subprocess.run",
            lambda *a, **kw: subprocess.CompletedProcess(
                args=[], returncode=0, stdout="tree\n", stderr=""
            ),
        )
        rc = {"git": {"commit": "abc1234abcd5678", "branch": "master"}}
        result = _check_git_commit(rc)
        assert result.passed is False
        assert "tree" in result.detail

    def test_includes_commit_message_in_notes(self, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc = {"git": {"commit": "abc1234abcd5678", "commit_message": "fix: something", "branch": "master"}}
        result = _check_git_commit(rc)
        assert any("fix: something" in n for n in result.notes)


# ---------------------------------------------------------------------------
# _check_gate_report
# ---------------------------------------------------------------------------


class TestCheckGateReport:
    def test_passes_when_file_exists_with_verdict(self, tmp_path):
        path = _make_gate_report(tmp_path)
        rc = {"gate_report_path": path}
        result = _check_gate_report(rc)
        assert result.passed is True
        assert "PASS" in result.detail

    def test_fails_when_path_missing_from_rc(self):
        rc = {}
        result = _check_gate_report(rc)
        assert result.passed is False
        assert "gate_report_path" in result.detail

    def test_fails_when_file_not_found(self, tmp_path):
        rc = {"gate_report_path": str(tmp_path / "nonexistent.json")}
        result = _check_gate_report(rc)
        assert result.passed is False
        assert "not found" in result.detail

    def test_fails_on_invalid_json(self, tmp_path):
        p = tmp_path / "quality_gate_report.json"
        p.write_text("not json{{{")
        rc = {"gate_report_path": str(p)}
        result = _check_gate_report(rc)
        assert result.passed is False
        assert "Could not read" in result.detail

    def test_run_id_in_notes(self, tmp_path):
        path = _make_gate_report(tmp_path)
        rc = {"gate_report_path": path}
        result = _check_gate_report(rc)
        assert any("gate-run-uuid" in n for n in result.notes)


# ---------------------------------------------------------------------------
# _check_run_report
# ---------------------------------------------------------------------------


class TestCheckRunReport:
    def test_passes_when_file_exists(self, tmp_path):
        path = _make_run_report(tmp_path)
        rc = {"run_report_path": path}
        result = _check_run_report(rc)
        assert result.passed is True
        assert "run-uuid" in result.detail

    def test_fails_when_path_missing_from_rc(self):
        rc = {}
        result = _check_run_report(rc)
        assert result.passed is False

    def test_fails_when_file_not_found(self, tmp_path):
        rc = {"run_report_path": str(tmp_path / "missing.json")}
        result = _check_run_report(rc)
        assert result.passed is False
        assert "not found" in result.detail

    def test_fails_on_invalid_json(self, tmp_path):
        p = tmp_path / "run_report.json"
        p.write_text("{{broken")
        rc = {"run_report_path": str(p)}
        result = _check_run_report(rc)
        assert result.passed is False


# ---------------------------------------------------------------------------
# _inspect_artifacts
# ---------------------------------------------------------------------------


class TestInspectArtifacts:
    def test_passes_when_hash_matches(self, tmp_path):
        art = _make_artifact_file(tmp_path)
        sha = _sha256(art)
        rc = {"artifacts": {"a": {"path": art, "sha256": sha, "size_bytes": 10, "present": True}}}
        check, inspections = _inspect_artifacts(rc)
        assert check.passed is True
        assert inspections[0].ok is True

    def test_fails_on_drift(self, tmp_path):
        art = _make_artifact_file(tmp_path, content="original\n")
        sha = _sha256(art)
        # Modify file after recording sha
        with open(art, "w") as f:
            f.write("modified content\n")
        rc = {"artifacts": {"a": {"path": art, "sha256": sha, "size_bytes": 9, "present": True}}}
        check, inspections = _inspect_artifacts(rc)
        assert check.passed is False
        assert inspections[0].drifted is True
        assert any("DRIFT" in n for n in check.notes)

    def test_fails_on_absent_file(self, tmp_path):
        rc = {"artifacts": {"a": {"path": str(tmp_path / "gone.md"), "sha256": "abc", "size_bytes": 10, "present": True}}}
        check, inspections = _inspect_artifacts(rc)
        assert check.passed is False
        assert inspections[0].absent is True
        assert any("ABSENT" in n for n in check.notes)

    def test_multiple_artifacts_all_ok(self, tmp_path):
        arts = {}
        for name in ("x", "y", "z"):
            p = _make_artifact_file(tmp_path, name=f"{name}.md")
            arts[name] = {"path": p, "sha256": _sha256(p), "size_bytes": os.path.getsize(p), "present": True}
        rc = {"artifacts": arts}
        check, inspections = _inspect_artifacts(rc)
        assert check.passed is True
        assert len(inspections) == 3

    def test_mixed_drift_and_absent(self, tmp_path):
        art1 = _make_artifact_file(tmp_path, name="a.md", content="original\n")
        sha1 = _sha256(art1)
        with open(art1, "w") as f:
            f.write("changed\n")  # drift
        rc = {
            "artifacts": {
                "drifted": {"path": art1, "sha256": sha1, "size_bytes": 9, "present": True},
                "absent":  {"path": str(tmp_path / "gone.md"), "sha256": "x", "size_bytes": 5, "present": True},
            }
        }
        check, inspections = _inspect_artifacts(rc)
        assert check.passed is False
        assert "1 drifted" in check.detail
        assert "1 absent" in check.detail

    def test_ok_notes_include_hash_prefix(self, tmp_path):
        art = _make_artifact_file(tmp_path)
        sha = _sha256(art)
        rc = {"artifacts": {"a": {"path": art, "sha256": sha, "size_bytes": os.path.getsize(art), "present": True}}}
        check, _ = _inspect_artifacts(rc)
        assert any("OK" in n for n in check.notes)

    def test_empty_artifacts_dict(self):
        rc = {"artifacts": {}}
        check, inspections = _inspect_artifacts(rc)
        assert check.passed is True
        assert inspections == []


# ---------------------------------------------------------------------------
# inspect_release_candidate — integration
# ---------------------------------------------------------------------------


class TestInspectReleaseCandidate:
    def test_full_pass(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, _ = _make_rc(tmp_path)
        result = inspect_release_candidate(rc_path)
        assert result.passed is True
        assert result.inspection_verdict == "PASS"
        assert len(result.checks) == 5

    def test_check_names(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, _ = _make_rc(tmp_path)
        result = inspect_release_candidate(rc_path)
        names = [c.name for c in result.checks]
        assert names == ["schema", "git_commit", "gate_report", "run_report", "artifact_hashes"]

    def test_all_checks_run_even_on_failure(self, tmp_path, monkeypatch):
        """All checks run even when an early check fails (no short-circuit)."""
        _mock_git_commit_not_found(monkeypatch)
        rc_path, _ = _make_rc(tmp_path)
        result = inspect_release_candidate(rc_path)
        # git_commit fails but all 5 checks still run
        assert len(result.checks) == 5

    def test_fails_on_missing_rc_file(self):
        result = inspect_release_candidate("/nonexistent/release_candidate.json")
        assert result.passed is False
        assert result.inspection_verdict == "FAIL"
        assert any("not found" in c.detail for c in result.checks)

    def test_fails_on_invalid_json(self, tmp_path):
        bad = tmp_path / "release_candidate.json"
        bad.write_text("{{not valid json")
        result = inspect_release_candidate(str(bad))
        assert result.passed is False

    def test_fails_on_drifted_artifact(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, rc = _make_rc(tmp_path)
        # Corrupt the artifact after packaging
        art_path = list(rc["artifacts"].values())[0]["path"]
        with open(art_path, "w") as f:
            f.write("completely different content\n")
        result = inspect_release_candidate(rc_path)
        assert result.passed is False
        assert "test_artifact" in result.drifted_artifacts

    def test_fails_on_absent_artifact(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, rc = _make_rc(tmp_path)
        art_path = list(rc["artifacts"].values())[0]["path"]
        os.remove(art_path)
        result = inspect_release_candidate(rc_path)
        assert result.passed is False
        assert "test_artifact" in result.absent_artifacts

    def test_fails_on_missing_gate_report(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, rc = _make_rc(tmp_path)
        os.remove(rc["gate_report_path"])
        result = inspect_release_candidate(rc_path)
        assert result.passed is False
        gate_check = next(c for c in result.checks if c.name == "gate_report")
        assert not gate_check.passed

    def test_fails_on_missing_run_report(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, rc = _make_rc(tmp_path)
        os.remove(rc["run_report_path"])
        result = inspect_release_candidate(rc_path)
        assert result.passed is False
        run_check = next(c for c in result.checks if c.name == "run_report")
        assert not run_check.passed

    def test_fails_on_schema_violation(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, _ = _make_rc(tmp_path, drop_keys=["rc_id"])
        result = inspect_release_candidate(rc_path)
        assert result.passed is False
        schema_check = next(c for c in result.checks if c.name == "schema")
        assert not schema_check.passed

    def test_rc_path_is_absolute_in_result(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, _ = _make_rc(tmp_path)
        result = inspect_release_candidate(rc_path)
        assert os.path.isabs(result.rc_path)

    def test_to_dict_roundtrip(self, tmp_path, monkeypatch):
        _mock_git_commit_found(monkeypatch)
        rc_path, _ = _make_rc(tmp_path)
        result = inspect_release_candidate(rc_path)
        d = result.to_dict()
        assert d["inspection_verdict"] == "PASS"
        assert isinstance(d["checks"], list)
        assert isinstance(d["artifacts"], list)


# ---------------------------------------------------------------------------
# find_latest_rc
# ---------------------------------------------------------------------------


class TestFindLatestRc:
    def test_returns_none_when_dir_missing(self, tmp_path):
        result = find_latest_rc(str(tmp_path / "nonexistent"))
        assert result is None

    def test_returns_none_when_no_rcs(self, tmp_path):
        (tmp_path / "rc").mkdir()
        result = find_latest_rc(str(tmp_path / "rc"))
        assert result is None

    def test_returns_latest_by_timestamp(self, tmp_path):
        for ts in ("20260626T010000", "20260626T020000", "20260626T030000"):
            d = tmp_path / "rc" / ts
            d.mkdir(parents=True)
            (d / "release_candidate.json").write_text("{}")
        result = find_latest_rc(str(tmp_path / "rc"))
        assert result is not None
        assert "20260626T030000" in result

    def test_returns_absolute_path(self, tmp_path):
        d = tmp_path / "rc" / "20260626T010000"
        d.mkdir(parents=True)
        (d / "release_candidate.json").write_text("{}")
        result = find_latest_rc(str(tmp_path / "rc"))
        assert result is not None
        assert os.path.isabs(result)


# ---------------------------------------------------------------------------
# main() — CLI
# ---------------------------------------------------------------------------


def _stub_inspect(monkeypatch, passed: bool = True, rc_path: str = "/fake/rc.json"):
    result = InspectionResult(
        rc_path=rc_path,
        rc_id="test-id",
        rc_verdict="PASS",
        inspection_verdict="PASS" if passed else "FAIL",
        timestamp_utc="2026-06-26T00:00:00Z",
        checks=[CheckResult(name="schema", passed=passed, detail="ok")],
    )
    monkeypatch.setattr(
        "hoch_agent_swarm.rc_inspector.inspect_release_candidate",
        lambda path: result,
    )
    return result


def _stub_find_latest(monkeypatch, path: str | None = "/fake/rc.json"):
    monkeypatch.setattr(
        "hoch_agent_swarm.rc_inspector.find_latest_rc",
        lambda rc_dir=None: path,
    )


class TestMain:
    def test_exit_0_on_pass(self, monkeypatch, capsys):
        _stub_inspect(monkeypatch, passed=True)
        code = main(["/fake/release_candidate.json"])
        assert code == 0

    def test_exit_1_on_fail(self, monkeypatch, capsys):
        _stub_inspect(monkeypatch, passed=False)
        code = main(["/fake/release_candidate.json"])
        assert code == 1

    def test_latest_flag_uses_find_latest(self, monkeypatch, capsys):
        _stub_find_latest(monkeypatch, path="/fake/latest/rc.json")
        _stub_inspect(monkeypatch, passed=True, rc_path="/fake/latest/rc.json")
        code = main(["--latest"])
        assert code == 0

    def test_latest_flag_returns_1_when_no_rc_found(self, monkeypatch, capsys):
        _stub_find_latest(monkeypatch, path=None)
        code = main(["--latest"])
        assert code == 1

    def test_json_flag_outputs_valid_json(self, monkeypatch, capsys):
        _stub_inspect(monkeypatch, passed=True)
        code = main(["/fake/release_candidate.json", "--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "inspection_verdict" in parsed
        assert code == 0

    def test_json_flag_fail_outputs_valid_json(self, monkeypatch, capsys):
        _stub_inspect(monkeypatch, passed=False)
        code = main(["/fake/release_candidate.json", "--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["inspection_verdict"] == "FAIL"
        assert code == 1

    def test_human_output_pass(self, monkeypatch, capsys):
        _stub_inspect(monkeypatch, passed=True)
        main(["/fake/release_candidate.json"])
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_human_output_fail(self, monkeypatch, capsys):
        _stub_inspect(monkeypatch, passed=False)
        main(["/fake/release_candidate.json"])
        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_no_args_returns_1(self, monkeypatch, capsys):
        code = main([])
        assert code == 1
