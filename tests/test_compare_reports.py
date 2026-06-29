"""
tests/test_compare_reports.py — Unit tests for compare_reports.py

All tests use synthetic in-memory or tmp_path fixtures.
No live crew runs, no live filesystem side-effects beyond tmp_path.
"""
from __future__ import annotations

import json
import os

import pytest

from hoch_agent_swarm.compare_reports import (
    VERDICT_BLOCK,
    VERDICT_INVESTIGATE,
    VERDICT_PROMOTE,
    ArtifactDiff,
    ComparisonResult,
    _artifact_map,
    _diff_artifacts,
    _load_report,
    compare_run_reports,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_ARTIFACT_PATHS = [
    "artifacts/research/asset_map.md",
    "artifacts/security_reviews/security_audit_report.md",
    "artifacts/reports/execution_plan.md",
    "artifacts/reports/release_packet.md",
    "artifacts/antigravity/antigravity_execution_plan.md",
]


def _make_report(
    status: str = "PASS",
    crewai_version: str = "1.14.7",
    mcp_stub_version: str = "1.26.0",
    errors: list | None = None,
    artifact_validation: str = "VALID",
    artifact_sha: str = "abc123",
    artifact_size: int = 2000,
) -> dict:
    """Produce a synthetic run_report.json dict."""
    return {
        "run_id": "test-run-id",
        "started_at": "2026-06-26T00:00:00+00:00",
        "completed_at": "2026-06-26T00:05:00+00:00",
        "status": status,
        "crewai_version": crewai_version,
        "mcp_stub_version": mcp_stub_version,
        "python_version": "3.13.0",
        "workflow_name": "hoch_agent_swarm",
        "inputs_summary": {},
        "canonical_artifacts": [
            {
                "path": p,
                "exists": True,
                "size_bytes": artifact_size,
                "sha256": artifact_sha,
                "validation_status": artifact_validation,
            }
            for p in _ARTIFACT_PATHS
        ],
        "archived_previous_artifacts": [],
        "errors": errors or [],
    }


def _write_report(tmp_path, name: str, data: dict) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return str(path)


# ---------------------------------------------------------------------------
# _load_report
# ---------------------------------------------------------------------------


class TestLoadReport:
    def test_loads_valid_json(self, tmp_path):
        data = _make_report()
        path = _write_report(tmp_path, "report.json", data)
        result = _load_report(path)
        assert result["status"] == "PASS"

    def test_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            _load_report(str(tmp_path / "nonexistent.json"))

    def test_raises_value_error_on_non_dict(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("[1, 2, 3]")
        with pytest.raises(ValueError, match="Invalid run report format"):
            _load_report(str(path))


# ---------------------------------------------------------------------------
# _artifact_map
# ---------------------------------------------------------------------------


class TestArtifactMap:
    def test_indexes_by_path(self):
        report = _make_report()
        m = _artifact_map(report)
        assert set(m.keys()) == set(_ARTIFACT_PATHS)
        assert m[_ARTIFACT_PATHS[0]]["validation_status"] == "VALID"

    def test_empty_when_no_artifacts(self):
        assert _artifact_map({}) == {}
        assert _artifact_map({"canonical_artifacts": []}) == {}


# ---------------------------------------------------------------------------
# _diff_artifacts
# ---------------------------------------------------------------------------


class TestDiffArtifacts:
    def test_no_regression_when_both_valid(self):
        b = _make_report(artifact_validation="VALID", artifact_sha="aaa")
        t = _make_report(artifact_validation="VALID", artifact_sha="bbb")
        diffs, findings = _diff_artifacts(b, t)
        assert all(not d.regression for d in diffs)
        assert not any("regression" in f for f in findings)

    def test_sha_changed_flagged_informational(self):
        b = _make_report(artifact_sha="aaa")
        t = _make_report(artifact_sha="bbb")
        diffs, _ = _diff_artifacts(b, t)
        assert all(d.sha256_changed for d in diffs)
        assert all(not d.regression for d in diffs)

    def test_regression_when_valid_becomes_invalid(self):
        b = _make_report(artifact_validation="VALID")
        t = _make_report(artifact_validation="INVALID")
        diffs, findings = _diff_artifacts(b, t)
        assert all(d.regression for d in diffs)
        assert any("regression" in f for f in findings)

    def test_no_regression_both_invalid(self):
        """INVALID → INVALID is not a regression (both broken, trial didn't make it worse)."""
        b = _make_report(artifact_validation="INVALID")
        t = _make_report(artifact_validation="INVALID")
        diffs, _ = _diff_artifacts(b, t)
        assert all(not d.regression for d in diffs)

    def test_missing_in_trial_flagged(self):
        b = _make_report()
        t = {"canonical_artifacts": [], "errors": []}
        diffs, findings = _diff_artifacts(b, t)
        assert any("MISSING" in f for f in findings)

    def test_size_delta_computed(self):
        b = _make_report(artifact_size=2000)
        t = _make_report(artifact_size=2500)
        diffs, _ = _diff_artifacts(b, t)
        for d in diffs:
            assert d.baseline_size_bytes == 2000
            assert d.trial_size_bytes == 2500


# ---------------------------------------------------------------------------
# compare_run_reports — verdict logic
# ---------------------------------------------------------------------------


class TestCompareRunReports:
    def _write_pair(self, tmp_path, baseline: dict, trial: dict):
        b_path = _write_report(tmp_path, "baseline.json", baseline)
        t_path = _write_report(tmp_path, "trial.json", trial)
        return b_path, t_path

    def test_promote_when_trial_passes_cleanly(self, tmp_path):
        b = _make_report(crewai_version="1.14.7", artifact_sha="aaa")
        t = _make_report(crewai_version="1.15.0", artifact_sha="bbb")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.verdict == VERDICT_PROMOTE

    def test_block_when_trial_status_fail(self, tmp_path):
        b = _make_report()
        t = _make_report(status="FAIL")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.verdict == VERDICT_BLOCK

    def test_block_when_artifact_regression(self, tmp_path):
        b = _make_report(artifact_validation="VALID")
        t = _make_report(artifact_validation="INVALID")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.verdict == VERDICT_BLOCK

    def test_investigate_when_trial_has_errors(self, tmp_path):
        b = _make_report()
        t = _make_report(errors=["non-fatal warning"])
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.verdict == VERDICT_INVESTIGATE

    def test_versions_captured_correctly(self, tmp_path):
        b = _make_report(crewai_version="1.14.7", mcp_stub_version="1.26.0")
        t = _make_report(crewai_version="1.15.0", mcp_stub_version="1.26.0")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.baseline_crewai_version == "1.14.7"
        assert result.trial_crewai_version == "1.15.0"
        assert result.baseline_mcp_version == "1.26.0"
        assert result.trial_mcp_version == "1.26.0"

    def test_mcp_version_change_noted_in_findings(self, tmp_path):
        b = _make_report(mcp_stub_version="1.25.0")
        t = _make_report(mcp_stub_version="1.26.0")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert any("mcp_stub_version" in f for f in result.findings)

    def test_same_crewai_version_noted_in_findings(self, tmp_path):
        """Same version in both reports — likely unintentional trial setup error."""
        b = _make_report(crewai_version="1.14.7")
        t = _make_report(crewai_version="1.14.7")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert any("unchanged" in f for f in result.findings)

    def test_sha_changes_are_not_regressions(self, tmp_path):
        """Artifact content changing (different SHA) is expected for LLM output."""
        b = _make_report(artifact_sha="aaa", artifact_validation="VALID")
        t = _make_report(artifact_sha="zzz", artifact_validation="VALID")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.verdict == VERDICT_PROMOTE
        assert all(d.sha256_changed for d in result.artifact_diffs)
        assert all(not d.regression for d in result.artifact_diffs)

    def test_raises_file_not_found(self, tmp_path):
        b_path = _write_report(tmp_path, "b.json", _make_report())
        with pytest.raises(FileNotFoundError):
            compare_run_reports(b_path, str(tmp_path / "no_such.json"))

    def test_artifact_count_matches(self, tmp_path):
        b = _make_report()
        t = _make_report()
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert len(result.artifact_diffs) == len(_ARTIFACT_PATHS)

    def test_both_fail_still_blocks(self, tmp_path):
        """If baseline also failed, trial failure is still BLOCK."""
        b = _make_report(status="FAIL")
        t = _make_report(status="FAIL")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        result = compare_run_reports(b_path, t_path)
        assert result.verdict == VERDICT_BLOCK


# ---------------------------------------------------------------------------
# ComparisonResult — serialization
# ---------------------------------------------------------------------------


class TestComparisonResultSerialization:
    def _make_result(self) -> ComparisonResult:
        return ComparisonResult(
            verdict=VERDICT_PROMOTE,
            baseline_path="/a/baseline.json",
            trial_path="/b/trial.json",
            baseline_crewai_version="1.14.7",
            trial_crewai_version="1.15.0",
            baseline_mcp_version="1.26.0",
            trial_mcp_version="1.26.0",
            baseline_status="PASS",
            trial_status="PASS",
            baseline_errors=[],
            trial_errors=[],
            artifact_diffs=[
                ArtifactDiff(
                    path="artifacts/security_reviews/security_audit_report.md",
                    baseline_validation="VALID",
                    trial_validation="VALID",
                    baseline_size_bytes=2000,
                    trial_size_bytes=2500,
                    sha256_changed=True,
                    regression=False,
                )
            ],
            findings=["crewai version unchanged: 1.14.7"],
        )

    def test_to_dict_structure(self):
        r = self._make_result()
        d = r.to_dict()
        assert "verdict" in d
        assert "artifact_diffs" in d
        assert isinstance(d["artifact_diffs"], list)

    def test_to_json_is_valid_json(self):
        r = self._make_result()
        raw = r.to_json()
        parsed = json.loads(raw)
        assert parsed["verdict"] == VERDICT_PROMOTE

    def test_summary_lines_contains_verdict(self):
        r = self._make_result()
        combined = "\n".join(r.summary_lines())
        assert "PROMOTE" in combined
        assert "✅" in combined

    def test_summary_lines_contains_artifact_names(self):
        r = self._make_result()
        combined = "\n".join(r.summary_lines())
        assert "security_audit_report.md" in combined

    def test_summary_lines_block_verdict(self):
        r = self._make_result()
        r.verdict = VERDICT_BLOCK
        combined = "\n".join(r.summary_lines())
        assert "BLOCK" in combined
        assert "❌" in combined

    def test_summary_lines_investigate_verdict(self):
        r = self._make_result()
        r.verdict = VERDICT_INVESTIGATE
        combined = "\n".join(r.summary_lines())
        assert "INVESTIGATE" in combined


# ---------------------------------------------------------------------------
# main() — CLI
# ---------------------------------------------------------------------------


class TestMain:
    def _write_pair(self, tmp_path, baseline: dict, trial: dict):
        b_path = _write_report(tmp_path, "b.json", baseline)
        t_path = _write_report(tmp_path, "t.json", trial)
        return b_path, t_path

    def test_exit_0_on_promote(self, tmp_path, capsys):
        b = _make_report(crewai_version="1.14.7", artifact_sha="a")
        t = _make_report(crewai_version="1.15.0", artifact_sha="b")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        code = main([b_path, t_path])
        assert code == 0

    def test_exit_1_on_block(self, tmp_path, capsys):
        b = _make_report()
        t = _make_report(status="FAIL")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        code = main([b_path, t_path])
        assert code == 1

    def test_exit_1_on_investigate(self, tmp_path, capsys):
        b = _make_report()
        t = _make_report(errors=["warning"])
        b_path, t_path = self._write_pair(tmp_path, b, t)
        code = main([b_path, t_path])
        assert code == 1

    def test_json_flag_outputs_valid_json(self, tmp_path, capsys):
        b = _make_report(crewai_version="1.14.7", artifact_sha="a")
        t = _make_report(crewai_version="1.15.0", artifact_sha="b")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        code = main(["--json", b_path, t_path])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "verdict" in parsed
        assert code == 0

    def test_missing_args_returns_exit_2(self, capsys):
        code = main(["only_one_arg.json"])
        assert code == 2

    def test_no_args_returns_exit_2(self, capsys):
        code = main([])
        assert code == 2

    def test_missing_file_returns_exit_2(self, tmp_path, capsys):
        b_path = _write_report(tmp_path, "b.json", _make_report())
        code = main([b_path, str(tmp_path / "no_such.json")])
        assert code == 2

    def test_human_output_contains_promote(self, tmp_path, capsys):
        b = _make_report(crewai_version="1.14.7", artifact_sha="a")
        t = _make_report(crewai_version="1.15.0", artifact_sha="b")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        main([b_path, t_path])
        captured = capsys.readouterr()
        assert "PROMOTE" in captured.out

    def test_human_output_block_shows_block(self, tmp_path, capsys):
        b = _make_report()
        t = _make_report(status="FAIL")
        b_path, t_path = self._write_pair(tmp_path, b, t)
        main([b_path, t_path])
        captured = capsys.readouterr()
        assert "BLOCK" in captured.out
