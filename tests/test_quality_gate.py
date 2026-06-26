"""
tests/test_quality_gate.py — Unit tests for quality_gate.py

All subprocess calls are monkeypatched. No live crew run, no live Ollama,
no live pytest invocation inside these tests.
"""
from __future__ import annotations

import json
import subprocess

import pytest

from hoch_agent_swarm.quality_gate import (
    GateResult,
    StepResult,
    _STEP_IMPORT,
    _STEP_LIVE_CREW,
    _STEP_PREFLIGHT,
    _STEP_PYTEST,
    _run_import_check,
    _run_live_crew_step,
    _run_preflight_step,
    _run_pytest_step,
    main,
    run_quality_gate,
)
from hoch_agent_swarm.trial_preflight import CheckResult, PreflightResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(returncode: int, stdout: str = "", stderr: str = ""):
    """Return a mock subprocess.CompletedProcess."""
    p = subprocess.CompletedProcess(args=[], returncode=returncode)
    p.stdout = stdout
    p.stderr = stderr
    return p


def _make_preflight_result(passed: bool, check_name: str = "env_file_present") -> PreflightResult:
    detail = "ok" if passed else "MISSING"
    return PreflightResult(
        passed=passed,
        checks=[
            CheckResult(name=check_name, passed=passed, blocking=True, detail=detail),
        ],
        baseline_report="/path/run_report.json" if passed else None,
    )


def _make_gate_result(
    steps_passed: list[bool] | None = None,
    live: bool = False,
) -> GateResult:
    if steps_passed is None:
        steps_passed = [True, True, True]
    names = [_STEP_IMPORT, _STEP_PREFLIGHT, _STEP_PYTEST]
    if live:
        names.append(_STEP_LIVE_CREW)
        steps_passed = list(steps_passed) + [True]
    steps = [
        StepResult(name=n, passed=p, detail="ok" if p else "FAIL")
        for n, p in zip(names, steps_passed)
    ]
    return GateResult(passed=all(s.passed for s in steps), live_run_included=live, steps=steps)


# ---------------------------------------------------------------------------
# StepResult
# ---------------------------------------------------------------------------


class TestStepResult:
    def test_to_dict_fields(self):
        s = StepResult(name="foo", passed=True, detail="ok", output="")
        d = s.to_dict()
        assert d["name"] == "foo"
        assert d["passed"] is True
        assert "detail" in d
        assert "output" in d

    def test_passed_and_failed(self):
        ok = StepResult(name="a", passed=True, detail="ok")
        fail = StepResult(name="b", passed=False, detail="nope", output="err")
        assert ok.passed is True
        assert fail.passed is False
        assert fail.output == "err"


# ---------------------------------------------------------------------------
# GateResult
# ---------------------------------------------------------------------------


class TestGateResult:
    def test_to_dict_structure(self):
        r = _make_gate_result()
        d = r.to_dict()
        assert "passed" in d
        assert "live_run_included" in d
        assert "steps" in d
        assert isinstance(d["steps"], list)

    def test_to_json_valid(self):
        r = _make_gate_result()
        parsed = json.loads(r.to_json())
        assert parsed["passed"] is True

    def test_summary_lines_pass(self):
        r = _make_gate_result()
        combined = "\n".join(r.summary_lines())
        assert "PASS" in combined
        assert "✅" in combined

    def test_summary_lines_fail(self):
        r = _make_gate_result(steps_passed=[True, False, True])
        r.passed = False
        combined = "\n".join(r.summary_lines())
        assert "FAIL" in combined
        assert "❌" in combined

    def test_summary_lines_live_tag(self):
        r = _make_gate_result(live=True)
        combined = "\n".join(r.summary_lines())
        assert "live crew included" in combined

    def test_summary_lines_no_live_tag(self):
        r = _make_gate_result(live=False)
        combined = "\n".join(r.summary_lines())
        assert "live crew skipped" in combined

    def test_failed_step_output_shown(self):
        r = GateResult(
            passed=False,
            live_run_included=False,
            steps=[
                StepResult(name="pytest", passed=False, detail="2 failed", output="FAILED test_x\nFAILED test_y"),
            ],
        )
        combined = "\n".join(r.summary_lines())
        assert "FAILED test_x" in combined


# ---------------------------------------------------------------------------
# _run_import_check
# ---------------------------------------------------------------------------


class TestRunImportCheck:
    def test_pass_on_zero_returncode(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="ok\n"),
        )
        result = _run_import_check()
        assert result.passed is True
        assert result.name == _STEP_IMPORT
        assert "imports cleanly" in result.detail

    def test_fail_on_nonzero_returncode(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(1, stderr="ImportError: no module"),
        )
        result = _run_import_check()
        assert result.passed is False
        assert "import failed" in result.detail
        assert "ImportError" in result.output

    def test_output_empty_on_success(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="ok"),
        )
        result = _run_import_check()
        assert result.output == ""  # no noise on success


# ---------------------------------------------------------------------------
# _run_preflight_step
# ---------------------------------------------------------------------------


class TestRunPreflightStep:
    def test_pass_when_preflight_passes(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=True),
        )
        result = _run_preflight_step()
        assert result.passed is True
        assert result.name == _STEP_PREFLIGHT
        assert "preflight checks passed" in result.detail

    def test_fail_when_preflight_blocked(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=False, check_name="env_file_present"),
        )
        result = _run_preflight_step()
        assert result.passed is False
        assert "BLOCKED" in result.detail
        assert "env_file_present" in result.detail

    def test_check_count_in_detail(self, monkeypatch):
        pf = _make_preflight_result(passed=True)
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: pf,
        )
        result = _run_preflight_step()
        assert str(len(pf.checks)) in result.detail

    def test_output_empty_on_success(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=True),
        )
        result = _run_preflight_step()
        assert result.output == ""

    def test_output_contains_check_details_on_failure(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=False, check_name="ollama_model_available"),
        )
        result = _run_preflight_step()
        assert "ollama_model_available" in result.output


# ---------------------------------------------------------------------------
# _run_pytest_step
# ---------------------------------------------------------------------------


class TestRunPytestStep:
    def test_pass_on_zero_returncode(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="219 passed in 1.02s\n"),
        )
        result = _run_pytest_step()
        assert result.passed is True
        assert result.name == _STEP_PYTEST
        assert "219 passed" in result.detail

    def test_fail_on_nonzero_returncode(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(1, stdout="2 failed, 217 passed\n"),
        )
        result = _run_pytest_step()
        assert result.passed is False

    def test_summary_line_extracted(self, monkeypatch):
        """The last non-empty line is used as the detail."""
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="stuff\n\n219 passed in 1.02s\n"),
        )
        result = _run_pytest_step()
        assert result.detail == "219 passed in 1.02s"

    def test_output_empty_on_success(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="219 passed\n"),
        )
        result = _run_pytest_step()
        assert result.output == ""

    def test_output_populated_on_failure(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(1, stdout="FAILED test_foo\n1 failed\n"),
        )
        result = _run_pytest_step()
        assert "FAILED" in result.output


# ---------------------------------------------------------------------------
# _run_live_crew_step
# ---------------------------------------------------------------------------


class TestRunLiveCrewStep:
    def test_pass_on_zero_returncode(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(
                0,
                stdout="[report] Run report written: artifacts/crew_runs/X/run_report.json\n",
            ),
        )
        result = _run_live_crew_step()
        assert result.passed is True
        assert result.name == _STEP_LIVE_CREW
        assert "PASS" in result.detail

    def test_report_path_in_detail(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(
                0,
                stdout="[report] Run report written: artifacts/crew_runs/X/run_report.json\n",
            ),
        )
        result = _run_live_crew_step()
        assert "run_report.json" in result.detail

    def test_fail_on_nonzero_returncode(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(1, stderr="crew failed\n"),
        )
        result = _run_live_crew_step()
        assert result.passed is False
        assert "FAIL" in result.detail

    def test_output_empty_on_success(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="done\n"),
        )
        result = _run_live_crew_step()
        assert result.output == ""

    def test_output_populated_on_failure(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(1, stderr="OpenAI API key required\n"),
        )
        result = _run_live_crew_step()
        assert "OpenAI" in result.output


# ---------------------------------------------------------------------------
# run_quality_gate — integration
# ---------------------------------------------------------------------------


def _mock_all_pass(monkeypatch):
    """Mock all steps to pass. Returns the mocked PreflightResult."""
    pf = _make_preflight_result(passed=True)

    monkeypatch.setattr(
        "hoch_agent_swarm.quality_gate.subprocess.run",
        lambda *a, **kw: _make_completed_process(0, stdout="219 passed in 1.02s\n"),
    )
    monkeypatch.setattr(
        "hoch_agent_swarm.quality_gate.run_preflight",
        lambda **kw: pf,
    )
    return pf


class TestRunQualityGate:
    def test_pass_when_all_steps_pass(self, monkeypatch):
        _mock_all_pass(monkeypatch)
        result = run_quality_gate(include_live=False)
        assert result.passed is True
        assert result.live_run_included is False

    def test_step_count_without_live(self, monkeypatch):
        _mock_all_pass(monkeypatch)
        result = run_quality_gate(include_live=False)
        assert len(result.steps) == 3

    def test_step_count_with_live(self, monkeypatch):
        _mock_all_pass(monkeypatch)
        result = run_quality_gate(include_live=True)
        assert len(result.steps) == 4
        assert result.live_run_included is True

    def test_fail_when_import_fails(self, monkeypatch):
        call_count = {"n": 0}

        def _fake_run(*a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _make_completed_process(1, stderr="ImportError")
            return _make_completed_process(0, stdout="219 passed\n")

        monkeypatch.setattr("hoch_agent_swarm.quality_gate.subprocess.run", _fake_run)
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=True),
        )
        result = run_quality_gate(include_live=False)
        assert result.passed is False
        import_step = next(s for s in result.steps if s.name == _STEP_IMPORT)
        assert import_step.passed is False

    def test_fail_when_preflight_blocked(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.subprocess.run",
            lambda *a, **kw: _make_completed_process(0, stdout="219 passed\n"),
        )
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=False),
        )
        result = run_quality_gate(include_live=False)
        assert result.passed is False
        pf_step = next(s for s in result.steps if s.name == _STEP_PREFLIGHT)
        assert pf_step.passed is False

    def test_fail_when_pytest_fails(self, monkeypatch):
        call_count = {"n": 0}

        def _fake_run(*a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # import check pass
                return _make_completed_process(0, stdout="ok\n")
            # pytest fail
            return _make_completed_process(1, stdout="2 failed\n")

        monkeypatch.setattr("hoch_agent_swarm.quality_gate.subprocess.run", _fake_run)
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=True),
        )
        result = run_quality_gate(include_live=False)
        assert result.passed is False
        pytest_step = next(s for s in result.steps if s.name == _STEP_PYTEST)
        assert pytest_step.passed is False

    def test_all_steps_run_even_when_earlier_fails(self, monkeypatch):
        """No short-circuit — all steps execute regardless of failures."""
        call_count = {"n": 0}

        def _fake_run(*a, **kw):
            call_count["n"] += 1
            # import check fails, pytest called anyway
            if call_count["n"] == 1:
                return _make_completed_process(1, stderr="ImportError")
            return _make_completed_process(0, stdout="219 passed\n")

        monkeypatch.setattr("hoch_agent_swarm.quality_gate.subprocess.run", _fake_run)
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_preflight",
            lambda **kw: _make_preflight_result(passed=True),
        )
        result = run_quality_gate(include_live=False)
        assert len(result.steps) == 3  # all 3 ran
        assert call_count["n"] == 2    # import + pytest both called

    def test_step_names_in_order(self, monkeypatch):
        _mock_all_pass(monkeypatch)
        result = run_quality_gate(include_live=False)
        names = [s.name for s in result.steps]
        assert names == [_STEP_IMPORT, _STEP_PREFLIGHT, _STEP_PYTEST]

    def test_step_names_with_live(self, monkeypatch):
        _mock_all_pass(monkeypatch)
        result = run_quality_gate(include_live=True)
        names = [s.name for s in result.steps]
        assert names == [_STEP_IMPORT, _STEP_PREFLIGHT, _STEP_PYTEST, _STEP_LIVE_CREW]


# ---------------------------------------------------------------------------
# main() — CLI
# ---------------------------------------------------------------------------


def _mock_gate_result(monkeypatch, passed: bool = True, live: bool = False):
    result = _make_gate_result(live=live)
    result.passed = passed
    monkeypatch.setattr(
        "hoch_agent_swarm.quality_gate.run_quality_gate",
        lambda include_live=False: result,
    )
    return result


class TestMain:
    def test_exit_0_on_pass(self, monkeypatch, capsys):
        _mock_gate_result(monkeypatch, passed=True)
        code = main([])
        assert code == 0

    def test_exit_1_on_fail(self, monkeypatch, capsys):
        _mock_gate_result(monkeypatch, passed=False)
        code = main([])
        assert code == 1

    def test_json_flag_outputs_valid_json(self, monkeypatch, capsys):
        _mock_gate_result(monkeypatch, passed=True)
        code = main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "passed" in parsed
        assert "steps" in parsed
        assert code == 0

    def test_json_fail_outputs_valid_json(self, monkeypatch, capsys):
        _mock_gate_result(monkeypatch, passed=False)
        code = main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["passed"] is False
        assert code == 1

    def test_live_flag_passed_to_run_quality_gate(self, monkeypatch, capsys):
        calls = []
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_quality_gate",
            lambda include_live=False: (calls.append(include_live), _make_gate_result(live=include_live))[1],
        )
        main(["--live"])
        assert calls == [True]

    def test_no_live_flag_by_default(self, monkeypatch, capsys):
        calls = []
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_quality_gate",
            lambda include_live=False: (calls.append(include_live), _make_gate_result())[1],
        )
        main([])
        assert calls == [False]

    def test_human_output_contains_pass(self, monkeypatch, capsys):
        _mock_gate_result(monkeypatch, passed=True)
        main([])
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_human_output_contains_fail(self, monkeypatch, capsys):
        _mock_gate_result(monkeypatch, passed=False)
        main([])
        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_json_and_live_together(self, monkeypatch, capsys):
        calls = []
        monkeypatch.setattr(
            "hoch_agent_swarm.quality_gate.run_quality_gate",
            lambda include_live=False: (calls.append(include_live), _make_gate_result(live=include_live))[1],
        )
        code = main(["--live", "--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["live_run_included"] is True
        assert calls == [True]
        assert code == 0
