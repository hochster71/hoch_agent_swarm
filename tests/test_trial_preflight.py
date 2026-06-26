"""
tests/test_trial_preflight.py — Unit tests for trial_preflight.py

All tests are fully mocked: no live network calls, no live .env reads,
no live filesystem side-effects beyond tmp_path.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error

import pytest

from hoch_agent_swarm.trial_preflight import (
    CheckResult,
    PreflightResult,
    _CHECK_API_BASE,
    _CHECK_BASELINE,
    _CHECK_ENV_FILE,
    _CHECK_MODEL,
    _CHECK_MODEL_AVAILABLE,
    _CHECK_OLLAMA,
    _check_api_base_var,
    _check_baseline_report,
    _check_env_file,
    _check_model_var,
    _check_ollama_endpoint,
    _check_ollama_model_available,
    _load_dotenv_into_dict,
    _normalize_ollama_model_name,
    main,
    run_preflight,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_env(tmp_path, content="MODEL=ollama/llama3.1:8b\nAPI_BASE=http://localhost:11434\n"):
    env_file = tmp_path / ".env"
    env_file.write_text(content)
    return str(tmp_path)


def _write_report(tmp_path):
    """Create a fake run_report.json in the expected structure."""
    run_dir = tmp_path / "artifacts" / "crew_runs" / "20260101T000000"
    run_dir.mkdir(parents=True)
    report = run_dir / "run_report.json"
    report.write_text('{"status": "PASS"}')
    return str(tmp_path / "artifacts" / "crew_runs")


def _make_http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="http://localhost:11434",
        code=code,
        msg="",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )


# ---------------------------------------------------------------------------
# _load_dotenv_into_dict
# ---------------------------------------------------------------------------


class TestLoadDotenvIntoDict:
    def test_parses_key_value_pairs(self, tmp_path):
        cwd = _write_env(tmp_path, "MODEL=ollama/llama3.1:8b\nAPI_BASE=http://localhost:11434\n")
        result = _load_dotenv_into_dict(cwd)
        assert result["MODEL"] == "ollama/llama3.1:8b"
        assert result["API_BASE"] == "http://localhost:11434"

    def test_ignores_comment_lines(self, tmp_path):
        cwd = _write_env(tmp_path, "# comment\nMODEL=x\n")
        result = _load_dotenv_into_dict(cwd)
        assert "# comment" not in result
        assert result["MODEL"] == "x"

    def test_ignores_blank_lines(self, tmp_path):
        cwd = _write_env(tmp_path, "\nMODEL=x\n\n")
        result = _load_dotenv_into_dict(cwd)
        assert result == {"MODEL": "x"}

    def test_returns_empty_dict_if_file_absent(self, tmp_path):
        result = _load_dotenv_into_dict(str(tmp_path))
        assert result == {}

    def test_handles_value_with_equals(self, tmp_path):
        cwd = _write_env(tmp_path, "URL=http://a.com/v1?x=1\n")
        result = _load_dotenv_into_dict(cwd)
        assert result["URL"] == "http://a.com/v1?x=1"


# ---------------------------------------------------------------------------
# _check_env_file
# ---------------------------------------------------------------------------


class TestCheckEnvFile:
    def test_pass_when_present(self, tmp_path):
        cwd = _write_env(tmp_path)
        result = _check_env_file(cwd)
        assert result.passed is True
        assert result.blocking is True
        assert result.name == _CHECK_ENV_FILE

    def test_fail_when_absent(self, tmp_path):
        result = _check_env_file(str(tmp_path))
        assert result.passed is False
        assert result.blocking is True
        assert "MISSING" in result.detail
        assert "ln -sf" in result.detail  # guidance present


# ---------------------------------------------------------------------------
# _check_model_var
# ---------------------------------------------------------------------------


class TestCheckModelVar:
    def test_pass_when_set(self):
        result = _check_model_var({"MODEL": "ollama/llama3.1:8b"})
        assert result.passed is True
        assert "ollama/llama3.1:8b" in result.detail

    def test_fail_when_empty_string(self):
        result = _check_model_var({"MODEL": ""})
        assert result.passed is False
        assert result.blocking is True

    def test_fail_when_missing(self):
        result = _check_model_var({})
        assert result.passed is False
        assert result.name == _CHECK_MODEL

    def test_whitespace_only_is_fail(self):
        result = _check_model_var({"MODEL": "   "})
        assert result.passed is False


# ---------------------------------------------------------------------------
# _check_api_base_var
# ---------------------------------------------------------------------------


class TestCheckApiBaseVar:
    def test_pass_when_set(self):
        result = _check_api_base_var({"API_BASE": "http://localhost:11434"})
        assert result.passed is True

    def test_fail_when_missing(self):
        result = _check_api_base_var({})
        assert result.passed is False
        assert result.blocking is True
        assert result.name == _CHECK_API_BASE

    def test_fail_when_whitespace(self):
        result = _check_api_base_var({"API_BASE": "  "})
        assert result.passed is False


# ---------------------------------------------------------------------------
# _check_ollama_endpoint
# ---------------------------------------------------------------------------


class TestCheckOllamaEndpoint:
    def test_pass_on_200(self, monkeypatch):
        class _FakeResp:
            def getcode(self):
                return 200

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeResp(),
        )
        result = _check_ollama_endpoint("http://localhost:11434")
        assert result.passed is True
        assert "200" in result.detail

    def test_pass_on_404_http_error(self, monkeypatch):
        """Ollama sometimes returns 404 on GET / — still reachable."""
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(_make_http_error(404)),
        )
        result = _check_ollama_endpoint("http://localhost:11434")
        assert result.passed is True  # 404 < 500

    def test_fail_on_503(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(_make_http_error(503)),
        )
        result = _check_ollama_endpoint("http://localhost:11434")
        assert result.passed is False
        assert result.blocking is True
        assert "503" in result.detail

    def test_fail_on_connection_refused(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(OSError("Connection refused")),
        )
        result = _check_ollama_endpoint("http://localhost:11434")
        assert result.passed is False
        assert result.blocking is True
        assert "ollama serve" in result.detail

    def test_fail_on_timeout(self, monkeypatch):
        import socket
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(TimeoutError("timed out")),
        )
        result = _check_ollama_endpoint("http://localhost:11434")
        assert result.passed is False

    def test_trailing_slash_stripped(self, monkeypatch):
        """api_base with trailing slash should still produce a valid URL."""
        seen_urls = []

        class _FakeResp:
            def getcode(self):
                return 200

        def fake_urlopen(url, timeout):
            seen_urls.append(url)
            return _FakeResp()

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            fake_urlopen,
        )
        _check_ollama_endpoint("http://localhost:11434/")
        assert seen_urls[0] == "http://localhost:11434"


# ---------------------------------------------------------------------------
# _check_baseline_report
# ---------------------------------------------------------------------------


class TestCheckBaselineReport:
    def test_pass_when_report_exists(self, tmp_path):
        reports_dir = _write_report(tmp_path)
        check, latest = _check_baseline_report(reports_dir)
        assert check.passed is True
        assert check.blocking is False  # warn-only
        assert latest is not None
        assert "run_report.json" in latest

    def test_fail_warn_only_when_no_report(self, tmp_path):
        check, latest = _check_baseline_report(str(tmp_path / "no_such_dir"))
        assert check.passed is False
        assert check.blocking is False  # warn-only — not a blocker
        assert latest is None

    def test_latest_is_lexicographically_last(self, tmp_path):
        """Multiple reports — latest should be the last sorted path."""
        for ts in ["20260101T000000", "20260102T000000", "20260103T000000"]:
            d = tmp_path / "crew_runs" / ts
            d.mkdir(parents=True)
            (d / "run_report.json").write_text("{}")
        check, latest = _check_baseline_report(str(tmp_path / "crew_runs"))
        assert "20260103T000000" in latest



# ---------------------------------------------------------------------------
# _normalize_ollama_model_name
# ---------------------------------------------------------------------------


class TestNormalizeOllamaModelName:
    def test_strips_ollama_prefix(self):
        assert _normalize_ollama_model_name("ollama/llama3.1:8b") == "llama3.1:8b"

    def test_no_prefix_unchanged(self):
        assert _normalize_ollama_model_name("llama3.1:8b") == "llama3.1:8b"

    def test_other_provider_prefix_unchanged(self):
        assert _normalize_ollama_model_name("openai/gpt-4o") == "openai/gpt-4o"

    def test_strips_ollama_prefix_with_tag(self):
        assert _normalize_ollama_model_name("ollama/mistral:7b") == "mistral:7b"

    def test_empty_string_unchanged(self):
        assert _normalize_ollama_model_name("") == ""


# ---------------------------------------------------------------------------
# _check_ollama_model_available
# ---------------------------------------------------------------------------


def _make_urlopen_model_ok(model_name: str = "llama3.1:8b"):
    """Return a monkeypatch target that simulates /api/tags returning one model."""
    _resp = json.dumps({"models": [
        {"name": model_name, "model": model_name},
    ]}).encode()

    class _FakeReq:
        def read(self):
            return _resp

    return lambda url, timeout: _FakeReq()


class TestCheckOllamaModelAvailable:
    def test_pass_when_model_in_name_field(self, monkeypatch):
        _resp = json.dumps({"models": [
            {"name": "llama3.1:8b", "model": ""},
        ]}).encode()

        class _FakeReq:
            def read(self):
                return _resp

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        result = _check_ollama_model_available("http://localhost:11434", "ollama/llama3.1:8b")
        assert result.passed is True
        assert result.name == _CHECK_MODEL_AVAILABLE
        assert "llama3.1:8b" in result.detail

    def test_pass_when_model_in_model_field(self, monkeypatch):
        _resp = json.dumps({"models": [
            {"name": "", "model": "llama3.1:8b"},
        ]}).encode()

        class _FakeReq:
            def read(self):
                return _resp

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is True

    def test_pass_model_without_provider_prefix(self, monkeypatch):
        """MODEL=llama3.1:8b (no ollama/ prefix) should still match."""
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            _make_urlopen_model_ok("llama3.1:8b"),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is True

    def test_block_when_model_absent(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            _make_urlopen_model_ok("mistral:7b"),  # different model present
        )
        result = _check_ollama_model_available("http://localhost:11434", "ollama/llama3.1:8b")
        assert result.passed is False
        assert result.blocking is True
        assert "ollama pull llama3.1:8b" in result.detail

    def test_block_when_models_list_empty(self, monkeypatch):
        _resp = json.dumps({"models": []}).encode()

        class _FakeReq:
            def read(self):
                return _resp

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is False
        assert "NOT pulled" in result.detail

    def test_block_on_invalid_json(self, monkeypatch):
        class _FakeReq:
            def read(self):
                return b"not-json!!!"

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is False
        assert "invalid JSON" in result.detail

    def test_block_when_models_key_missing(self, monkeypatch):
        """Response JSON does not contain 'models' key."""
        _resp = json.dumps({"other_key": []}).encode()

        class _FakeReq:
            def read(self):
                return _resp

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        # models defaults to [] from .get("models", []) — model not found
        assert result.passed is False

    def test_block_when_models_not_a_list(self, monkeypatch):
        _resp = json.dumps({"models": "not-a-list"}).encode()

        class _FakeReq:
            def read(self):
                return _resp

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is False
        assert "missing 'models' list" in result.detail

    def test_block_on_http_error(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(
                urllib.error.HTTPError(url, 500, "error", None, None)  # type: ignore[arg-type]
            ),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is False
        assert "HTTP 500" in result.detail

    def test_block_on_os_error(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(OSError("connection refused")),
        )
        result = _check_ollama_model_available("http://localhost:11434", "llama3.1:8b")
        assert result.passed is False
        assert "cannot reach" in result.detail

    def test_check_name_constant(self, monkeypatch):
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            _make_urlopen_model_ok("llama3.1:8b"),
        )
        result = _check_ollama_model_available("http://localhost:11434", "ollama/llama3.1:8b")
        assert result.name == _CHECK_MODEL_AVAILABLE

    def test_json_output_includes_model_check(self, monkeypatch, capsys):
        """--json output contains the ollama_model_available check entry."""
        _TAGS_RESP = json.dumps({"models": [
            {"name": "llama3.1:8b", "model": "llama3.1:8b"},
        ]}).encode()

        class _FakeReq:
            def getcode(self):
                return 200
            def read(self):
                return _TAGS_RESP

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = os.path.join(tmpdir, ".env")
            with open(env_file, "w") as f:
                f.write("MODEL=ollama/llama3.1:8b\nAPI_BASE=http://localhost:11434\n")
            from hoch_agent_swarm.trial_preflight import run_preflight
            result = run_preflight(cwd=tmpdir, run_reports_dir=os.path.join(tmpdir, "no_runs"))
            parsed = json.loads(result.to_json())
            check_names = [c["name"] for c in parsed["checks"]]
            assert _CHECK_MODEL_AVAILABLE in check_names


# ---------------------------------------------------------------------------
# run_preflight — integration paths
# ---------------------------------------------------------------------------


class TestRunPreflight:
    def _mock_ollama_ok(self, monkeypatch):
        """Mock both HTTP calls: endpoint check (GET /) and model check (GET /api/tags)."""
        _TAGS_RESP = json.dumps({"models": [
            {"name": "llama3.1:8b", "model": "llama3.1:8b"},
        ]}).encode()

        class _FakeReq:
            def getcode(self):
                return 200
            def read(self):
                return _TAGS_RESP

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )

    def test_full_pass_path(self, tmp_path, monkeypatch):
        cwd = _write_env(tmp_path)
        reports_dir = _write_report(tmp_path)
        self._mock_ollama_ok(monkeypatch)
        result = run_preflight(cwd=cwd, run_reports_dir=reports_dir)
        assert result.passed is True
        assert all(c.passed or not c.blocking for c in result.checks)
        assert result.baseline_report is not None

    def test_blocked_when_env_absent(self, tmp_path):
        result = run_preflight(cwd=str(tmp_path), run_reports_dir=str(tmp_path))
        assert result.passed is False
        env_check = next(c for c in result.checks if c.name == _CHECK_ENV_FILE)
        assert env_check.passed is False

    def test_blocked_when_model_missing(self, tmp_path, monkeypatch):
        cwd = _write_env(tmp_path, "API_BASE=http://localhost:11434\n")  # MODEL absent
        self._mock_ollama_ok(monkeypatch)
        result = run_preflight(cwd=cwd, run_reports_dir=str(tmp_path))
        assert result.passed is False
        model_check = next(c for c in result.checks if c.name == _CHECK_MODEL)
        assert model_check.passed is False

    def test_blocked_when_api_base_missing(self, tmp_path, monkeypatch):
        cwd = _write_env(tmp_path, "MODEL=ollama/llama3.1:8b\n")  # API_BASE absent
        result = run_preflight(cwd=cwd, run_reports_dir=str(tmp_path))
        assert result.passed is False
        api_check = next(c for c in result.checks if c.name == _CHECK_API_BASE)
        assert api_check.passed is False

    def test_blocked_when_ollama_unreachable(self, tmp_path, monkeypatch):
        cwd = _write_env(tmp_path)
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: (_ for _ in ()).throw(OSError("refused")),
        )
        result = run_preflight(cwd=cwd, run_reports_dir=str(tmp_path))
        assert result.passed is False
        ollama_check = next(c for c in result.checks if c.name == _CHECK_OLLAMA)
        assert ollama_check.passed is False

    def test_passes_with_warn_when_no_baseline(self, tmp_path, monkeypatch):
        """No baseline report → warn-only → result.passed still True."""
        cwd = _write_env(tmp_path)
        self._mock_ollama_ok(monkeypatch)
        # No report dir set up
        result = run_preflight(cwd=cwd, run_reports_dir=str(tmp_path / "no_runs"))
        assert result.passed is True
        baseline_check = next(c for c in result.checks if c.name == _CHECK_BASELINE)
        assert baseline_check.passed is False
        assert baseline_check.blocking is False
        assert result.baseline_report is None

    def test_check_count_full_path(self, tmp_path, monkeypatch):
        """Full pass path produces exactly 6 checks."""
        cwd = _write_env(tmp_path)
        _write_report(tmp_path)
        self._mock_ollama_ok(monkeypatch)
        result = run_preflight(cwd=cwd, run_reports_dir=str(tmp_path / "artifacts" / "crew_runs"))
        assert len(result.checks) == 6

    def test_check_count_env_absent(self, tmp_path):
        """Env-absent path short-circuits: only check 1 + check 6 (warn)."""
        result = run_preflight(cwd=str(tmp_path), run_reports_dir=str(tmp_path))
        assert len(result.checks) == 2  # check 1 (fail) + check 6 (warn)

    def test_blocked_when_model_not_available(self, tmp_path, monkeypatch):
        """Model absent from /api/tags → BLOCKED."""
        _TAGS_RESP = json.dumps({"models": [
            {"name": "mistral:7b", "model": "mistral:7b"},
        ]}).encode()

        class _FakeReq:
            def getcode(self):
                return 200
            def read(self):
                return _TAGS_RESP

        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.urllib.request.urlopen",
            lambda url, timeout: _FakeReq(),
        )
        cwd = _write_env(tmp_path)  # MODEL=ollama/llama3.1:8b
        result = run_preflight(cwd=cwd, run_reports_dir=str(tmp_path))
        assert result.passed is False
        model_avail = next(c for c in result.checks if c.name == _CHECK_MODEL_AVAILABLE)
        assert model_avail.passed is False
        assert "ollama pull" in model_avail.detail


# ---------------------------------------------------------------------------
# PreflightResult — serialization
# ---------------------------------------------------------------------------


class TestPreflightResultSerialization:
    def _make_result(self) -> PreflightResult:
        return PreflightResult(
            passed=True,
            checks=[
                CheckResult(name="env_file_present", passed=True, blocking=True, detail="ok"),
            ],
            baseline_report="/some/path/run_report.json",
        )

    def test_to_dict_structure(self):
        r = self._make_result()
        d = r.to_dict()
        assert "passed" in d
        assert "checks" in d
        assert "baseline_report" in d
        assert isinstance(d["checks"], list)

    def test_to_json_is_valid_json(self):
        r = self._make_result()
        raw = r.to_json()
        parsed = json.loads(raw)
        assert parsed["passed"] is True

    def test_summary_lines_contains_check_name(self):
        r = self._make_result()
        lines = r.summary_lines()
        combined = "\n".join(lines)
        assert "env_file_present" in combined
        assert "PASS" in combined

    def test_summary_lines_blocked(self):
        r = PreflightResult(
            passed=False,
            checks=[
                CheckResult(name="env_file_present", passed=False, blocking=True, detail="MISSING"),
            ],
        )
        lines = r.summary_lines()
        combined = "\n".join(lines)
        assert "BLOCKED" in combined
        assert "❌" in combined


# ---------------------------------------------------------------------------
# main() — CLI
# ---------------------------------------------------------------------------


class TestMain:
    def _mock_run_preflight(self, monkeypatch, passed: bool = True):
        result = PreflightResult(
            passed=passed,
            checks=[
                CheckResult(
                    name=_CHECK_ENV_FILE, passed=passed, blocking=True, detail="ok" if passed else "MISSING"
                )
            ],
            baseline_report="/path/run_report.json" if passed else None,
        )
        monkeypatch.setattr(
            "hoch_agent_swarm.trial_preflight.run_preflight",
            lambda **kwargs: result,
        )
        return result

    def test_exit_0_on_pass(self, monkeypatch, capsys):
        self._mock_run_preflight(monkeypatch, passed=True)
        code = main([])
        assert code == 0

    def test_exit_1_on_fail(self, monkeypatch, capsys):
        self._mock_run_preflight(monkeypatch, passed=False)
        code = main([])
        assert code == 1

    def test_json_flag_outputs_valid_json(self, monkeypatch, capsys):
        self._mock_run_preflight(monkeypatch, passed=True)
        code = main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "passed" in parsed
        assert code == 0

    def test_json_flag_fail_outputs_valid_json(self, monkeypatch, capsys):
        self._mock_run_preflight(monkeypatch, passed=False)
        code = main(["--json"])
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["passed"] is False
        assert code == 1

    def test_human_output_on_pass(self, monkeypatch, capsys):
        self._mock_run_preflight(monkeypatch, passed=True)
        main([])
        captured = capsys.readouterr()
        assert "PASS" in captured.out

    def test_human_output_on_fail_writes_to_stderr(self, monkeypatch, capsys):
        self._mock_run_preflight(monkeypatch, passed=False)
        main([])
        captured = capsys.readouterr()
        assert "blocked" in captured.err.lower()
