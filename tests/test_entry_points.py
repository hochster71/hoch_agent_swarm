"""
tests/test_entry_points.py — unit tests for main.py entry points.

No real LLM calls are made. All crew interactions are monkeypatched.
Tests verify:
  - _default_inputs() produces correct non-empty fields
  - run() passes correct inputs to crew.kickoff() and validates artifacts
  - run_with_trigger() extracts topic/current_year from payload (with fallbacks)
  - run_with_trigger() rejects missing payload and invalid JSON
  - train(), replay(), test() are importable and route correctly
  - archive step is invoked before kickoff

Run with:
    uv run pytest tests/test_entry_points.py -v
"""

import json
import os
import sys
import types
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

pytest.importorskip("crewai", reason="legacy-crewai-factory lane inactive: crewai is optionalized out of the default runtime (council-authorized, 2026-07-19). Install the 'legacy-crewai-factory' extra to activate this test lane. See docs/helm/LEGACY_CREWAI_FACTORY_RUNBOOK.md")

import hoch_agent_swarm.main as main_module
from hoch_agent_swarm.main import (  # noqa: E402
    _default_inputs,
    _archive_existing_artifacts,
    run,
    run_with_trigger,
    train,
    replay,
    test as crew_test,
)


# ---------------------------------------------------------------------------
# _default_inputs()
# ---------------------------------------------------------------------------

class TestDefaultInputs:

    def test_topic_is_non_empty(self):
        inputs = _default_inputs()
        assert inputs["topic"] and len(inputs["topic"]) > 0

    def test_current_year_is_string(self):
        inputs = _default_inputs()
        assert isinstance(inputs["current_year"], str)

    def test_current_year_is_plausible(self):
        inputs = _default_inputs()
        year = int(inputs["current_year"])
        assert 2024 <= year <= 2030, f"Unexpected year: {year}"

    def test_current_year_matches_now(self):
        inputs = _default_inputs()
        assert inputs["current_year"] == str(datetime.now().year)

    def test_custom_topic_is_respected(self):
        inputs = _default_inputs(topic="custom topic")
        assert inputs["topic"] == "custom topic"

    def test_required_keys_present(self):
        inputs = _default_inputs()
        for key in ("topic", "current_year", "antigravity_role", "crewai_role", "integration_mode"):
            assert key in inputs, f"Missing required input key: {key}"

    def test_no_empty_string_values(self):
        inputs = _default_inputs()
        for key, val in inputs.items():
            assert val and len(str(val)) > 0, f"Key '{key}' has empty value"


# ---------------------------------------------------------------------------
# _archive_existing_artifacts()
# ---------------------------------------------------------------------------

class TestArchiveExistingArtifacts:

    def test_archives_existing_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        # Create a fake canonical artifact
        security_dir = tmp_path / "artifacts" / "security_reviews"
        security_dir.mkdir(parents=True)
        artifact = security_dir / "security_audit_report.md"
        artifact.write_text("# Security Audit Report\n\nSome content.")

        # Override the constant so the function uses our tmp paths
        monkeypatch.setattr(main_module, "_ARCHIVE_DIR", "artifacts/crew_runs")
        monkeypatch.setattr(
            main_module,
            "_CANONICAL_ARTIFACTS",
            ["artifacts/security_reviews/security_audit_report.md"],
        )

        _archive_existing_artifacts("20260101T000000")

        archived = tmp_path / "artifacts" / "crew_runs" / "20260101T000000" / "security_audit_report.md"
        assert archived.exists(), "Archived file should exist"
        assert archived.read_text() == "# Security Audit Report\n\nSome content."

    def test_no_archive_if_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(main_module, "_ARCHIVE_DIR", "artifacts/crew_runs")
        monkeypatch.setattr(main_module, "_CANONICAL_ARTIFACTS", ["artifacts/nonexistent.md"])

        _archive_existing_artifacts("20260101T000000")

        archive_dir = tmp_path / "artifacts" / "crew_runs" / "20260101T000000"
        assert not archive_dir.exists(), "Archive dir should not be created for missing source"


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

class TestRun:

    def test_run_calls_kickoff_with_correct_inputs(self, monkeypatch):
        mock_crew = MagicMock()
        mock_crew_instance = MagicMock()
        mock_crew.return_value.crew.return_value = mock_crew_instance

        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_run_validation", MagicMock(return_value={}))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        run()

        mock_crew_instance.kickoff.assert_called_once()
        call_kwargs = mock_crew_instance.kickoff.call_args
        inputs = call_kwargs.kwargs.get("inputs") or call_kwargs.args[0]
        assert inputs["topic"] == "AI LLMs"
        assert inputs["current_year"] == str(datetime.now().year)

    def test_run_calls_validation_after_kickoff(self, monkeypatch):
        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        validation_mock = MagicMock(return_value={})
        monkeypatch.setattr(main_module, "_run_validation", validation_mock)

        run()

        validation_mock.assert_called_once()

    def test_run_archives_before_kickoff(self, monkeypatch):
        call_order = []

        mock_crew = MagicMock()
        mock_crew.return_value.crew.return_value.kickoff.side_effect = lambda **_: call_order.append("kickoff")
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)

        def fake_archive(ts):
            call_order.append("archive")
            return []  # must return list for RunReport.record_archived_artifacts

        monkeypatch.setattr(main_module, "_archive_existing_artifacts", fake_archive)
        monkeypatch.setattr(main_module, "_run_validation", MagicMock(return_value={}))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        run()

        assert call_order.index("archive") < call_order.index("kickoff"), (
            "Archive must run before kickoff"
        )

    def test_run_raises_on_crew_exception(self, monkeypatch):
        mock_crew = MagicMock()
        mock_crew.return_value.crew.return_value.kickoff.side_effect = RuntimeError("model error")
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_run_validation", MagicMock(return_value={}))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        with pytest.raises(Exception, match="An error occurred while running the crew"):
            run()


# ---------------------------------------------------------------------------
# run_with_trigger()
# ---------------------------------------------------------------------------

class TestRunWithTrigger:

    def _mock_argv(self, monkeypatch, payload: dict):
        monkeypatch.setattr(sys, "argv", ["run_with_trigger", json.dumps(payload)])

    def test_extracts_topic_from_payload(self, monkeypatch):
        self._mock_argv(monkeypatch, {"topic": "my custom topic"})

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_run_validation", MagicMock(return_value={}))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        run_with_trigger()

        call_kwargs = mock_crew.return_value.crew.return_value.kickoff.call_args
        inputs = call_kwargs.kwargs.get("inputs") or call_kwargs.args[0]
        assert inputs["topic"] == "my custom topic"

    def test_uses_default_topic_when_missing(self, monkeypatch):
        self._mock_argv(monkeypatch, {})  # no topic key

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_run_validation", MagicMock(return_value={}))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        run_with_trigger()

        call_kwargs = mock_crew.return_value.crew.return_value.kickoff.call_args
        inputs = call_kwargs.kwargs.get("inputs") or call_kwargs.args[0]
        assert inputs["topic"]  # non-empty
        assert inputs["topic"] != ""

    def test_current_year_always_non_empty(self, monkeypatch):
        self._mock_argv(monkeypatch, {})

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_run_validation", MagicMock(return_value={}))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        run_with_trigger()

        call_kwargs = mock_crew.return_value.crew.return_value.kickoff.call_args
        inputs = call_kwargs.kwargs.get("inputs") or call_kwargs.args[0]
        assert inputs["current_year"] and inputs["current_year"] != ""
        assert int(inputs["current_year"]) >= 2024

    def test_raises_when_no_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_with_trigger"])  # no payload arg
        with pytest.raises(Exception, match="No trigger payload provided"):
            run_with_trigger()

    def test_raises_on_invalid_json(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run_with_trigger", "not-valid-json{"])
        with pytest.raises(Exception, match="Invalid JSON payload"):
            run_with_trigger()

    def test_validates_artifacts_after_kickoff(self, monkeypatch):
        self._mock_argv(monkeypatch, {"topic": "test"})

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)
        monkeypatch.setattr(main_module, "_archive_existing_artifacts", MagicMock(return_value=[]))
        monkeypatch.setattr(main_module, "_write_report", MagicMock())

        validation_mock = MagicMock(return_value={})
        monkeypatch.setattr(main_module, "_run_validation", validation_mock)

        run_with_trigger()

        validation_mock.assert_called_once()


# ---------------------------------------------------------------------------
# train(), replay(), test() — import and routing smoke tests
# ---------------------------------------------------------------------------

class TestOtherEntryPoints:

    def test_train_is_importable(self):
        assert callable(train)

    def test_replay_is_importable(self):
        assert callable(replay)

    def test_crew_test_is_importable(self):
        assert callable(crew_test)

    def test_train_routes_to_crew_train(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["train", "2", "training.json"])

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)

        train()

        mock_crew.return_value.crew.return_value.train.assert_called_once_with(
            n_iterations=2,
            filename="training.json",
            inputs=_default_inputs(),
        )

    def test_replay_routes_to_crew_replay(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["replay", "task-abc-123"])

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)

        replay()

        mock_crew.return_value.crew.return_value.replay.assert_called_once_with(
            task_id="task-abc-123"
        )

    def test_crew_test_routes_to_crew_test(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["test", "3", "gpt-4o-mini"])

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)

        crew_test()

        mock_crew.return_value.crew.return_value.test.assert_called_once_with(
            n_iterations=3,
            eval_llm="gpt-4o-mini",
            inputs=_default_inputs(),
        )

    def test_train_raises_clearly_on_bad_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["train", "not-an-int", "file.json"])

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)

        with pytest.raises(Exception):
            train()

    def test_replay_raises_clearly_on_missing_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["replay"])  # no task_id

        mock_crew = MagicMock()
        monkeypatch.setattr(main_module, "HochAgentSwarm", mock_crew)

        with pytest.raises(Exception):
            replay()
