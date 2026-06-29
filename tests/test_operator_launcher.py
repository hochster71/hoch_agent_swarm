#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_operator_launcher.py — Verification tests for operator launcher.
"""

import pytest
from unittest import mock
import sys
import time

from hoch_agent_swarm.operator_launcher import (
    is_port_in_use,
    fetch_json,
    verify_route,
    main
)

def test_is_port_in_use():
    with mock.patch("socket.socket") as mock_sock:
        # Mock connect_ex returning 0 (port in use)
        mock_sock.return_value.__enter__.return_value.connect_ex.return_value = 0
        assert is_port_in_use(8085) is True

        # Mock connect_ex returning nonzero (port free)
        mock_sock.return_value.__enter__.return_value.connect_ex.return_value = 111
        assert is_port_in_use(8085) is False

def test_fetch_json():
    # Success case
    mock_response = mock.MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.getcode.return_value = 200
    mock_response.read.return_value = b'{"status": "ok"}'
    with mock.patch("urllib.request.urlopen", return_value=mock_response):
        res = fetch_json("http://localhost:8085")
        assert res == {"status": "ok"}

    # Error case
    with mock.patch("urllib.request.urlopen", side_effect=Exception("error")):
        res = fetch_json("http://localhost:8085")
        assert res is None

def test_verify_route():
    # Pass case
    mock_response = mock.MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.getcode.return_value = 200
    with mock.patch("urllib.request.urlopen", return_value=mock_response):
        assert verify_route("http://localhost:8085", "Test Route") is True

    # Fail case (HTTP error code)
    mock_response = mock.MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.getcode.return_value = 500
    with mock.patch("urllib.request.urlopen", return_value=mock_response):
        assert verify_route("http://localhost:8085", "Test Route") is False

    # Fail case (exception)
    with mock.patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        assert verify_route("http://localhost:8085", "Test Route") is False

@mock.patch("hoch_agent_swarm.operator_launcher.is_port_in_use")
@mock.patch("hoch_agent_swarm.operator_launcher.fetch_json")
@mock.patch("hoch_agent_swarm.operator_launcher.verify_route")
@mock.patch("subprocess.Popen")
@mock.patch("sys.exit")
def test_launcher_main_already_running(mock_exit, mock_popen, mock_verify, mock_fetch, mock_in_use):
    # Case: Port is in use, and fetch_json succeeds (our dashboard is running)
    mock_in_use.return_value = True
    mock_fetch.return_value = {
        "status": "HEALTHY",
        "components": {
            "PromptBrain": {"status": "HEALTHY", "prompts_count": 187},
            "PromptQA": {"status": "HEALTHY", "average_score": 92},
            "EvidenceBrain": {"status": "HEALTHY", "nodes_count": 12, "edges_count": 24},
            "HOCH TV": {"status": "HEALTHY", "channels_count": 80}
        }
    }
    mock_verify.return_value = True
    
    main()
    
    mock_popen.assert_not_called()
    mock_exit.assert_called_once_with(0)

@mock.patch("hoch_agent_swarm.operator_launcher.is_port_in_use")
@mock.patch("hoch_agent_swarm.operator_launcher.fetch_json")
@mock.patch("hoch_agent_swarm.operator_launcher.verify_route")
@mock.patch("subprocess.Popen")
@mock.patch("sys.exit")
def test_launcher_main_spin_up(mock_exit, mock_popen, mock_verify, mock_fetch, mock_in_use):
    # Case: Port is not in use, so it starts the server
    # First call False (port free), subsequent calls True (port bound)
    mock_in_use.side_effect = [False, True, True, True, True, True, True, True, True, True, True]
    mock_fetch.return_value = {
        "status": "HEALTHY",
        "components": {
            "PromptBrain": {"status": "HEALTHY", "prompts_count": 187},
            "PromptQA": {"status": "HEALTHY", "average_score": 92},
            "EvidenceBrain": {"status": "HEALTHY", "nodes_count": 12, "edges_count": 24},
            "HOCH TV": {"status": "HEALTHY", "channels_count": 80}
        }
    }
    mock_verify.return_value = True
    
    mock_proc = mock.Mock()
    mock_popen.return_value = mock_proc
    
    sleep_calls = []
    def mock_sleep(secs):
        sleep_calls.append(secs)
        if len(sleep_calls) > 1:
            raise KeyboardInterrupt()
            
    with mock.patch("time.sleep", side_effect=mock_sleep):
        main()
        
    mock_popen.assert_called_once()
    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_called_once()
    mock_exit.assert_called_once_with(0)
