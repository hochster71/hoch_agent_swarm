import os
import json
import pytest
import fcntl
import psutil
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from backend.runtime_governor import RuntimeGovernor
from scripts.verify_runtime_governor import check_codebase_compliance

@pytest.fixture
def mock_repo_root(tmp_path):
    # Setup dummy directories
    hasf_data = tmp_path / "has_live_project_tracker" / "data"
    hasf_data.mkdir(parents=True)
    (hasf_data / "human_approval_queue.json").write_text(json.dumps({
        "pending_approvals": []
    }), encoding="utf-8")
    return tmp_path

class MockResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body
        
    def getcode(self):
        return self.status

    def read(self):
        return self.body.encode('utf-8')
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def mock_urlopen_success(url, timeout=None):
    if "/health" in url:
        return MockResponse(200, '{"status": "healthy"}')
    elif "/api/brain/runtime-truth" in url:
        return MockResponse(200, '{"status": "CONDITIONAL"}')
    elif "/api/brain/factory-runtime-truth" in url:
        return MockResponse(200, '{"status": "STALE"}')
    elif "/api/brain/source-authority" in url:
        return MockResponse(200, '{"status": "STALE", "sources": {"naics_2022": {"status": "STALE"}}}')
    elif "/api/brain/reasoning-graph" in url:
        return MockResponse(200, '{"status": "CONDITIONAL"}')
    return MockResponse(404, 'Not Found')

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_conditional_baseline(mock_urlopen, mock_proc_iter, mock_repo_root):
    # Mock no violating processes running
    mock_proc_iter.return_value = []
    # Mock all endpoints returning standard post-containment stale/conditional statuses
    mock_urlopen.side_effect = mock_urlopen_success
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    res = gov.evaluate(evidence_dir=str(mock_repo_root))
    
    assert res["verdict"] == "CONDITIONAL"
    assert "source authority is stale and reasoning graph is conditional" in "".join(res["reasons"]).lower()
    assert res["mutation_allowed"] is False
    
    # Verify decision record schema
    record_path = mock_repo_root / "decision_record.json"
    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["verdict"] == "CONDITIONAL"
    assert record["hmf_hrf_paid_execution_allowed"] is False
    assert record["hoch200_sync_allowed"] is False

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_no_go_on_containment_failure(mock_urlopen, mock_proc_iter, mock_repo_root):
    # Mock a violating process (hoch_daemon.sh)
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 9999,
        "name": "bash",
        "cmdline": ["bash", "scripts/hoch_daemon.sh"]
    }
    mock_proc_iter.return_value = [mock_proc]
    mock_urlopen.side_effect = mock_urlopen_success
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    res = gov.evaluate(evidence_dir=str(mock_repo_root))
    
    assert res["verdict"] == "NO_GO"
    assert "containment" in "".join(res["reasons"]).lower()

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_no_go_on_health_failure(mock_urlopen, mock_proc_iter, mock_repo_root):
    mock_proc_iter.return_value = []
    # Mock /health endpoint returning 500
    def mock_urlopen_fail(url, timeout=None):
        if "/health" in url:
            return MockResponse(500, 'Internal Server Error')
        return mock_urlopen_success(url, timeout)
    mock_urlopen.side_effect = mock_urlopen_fail
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    res = gov.evaluate(evidence_dir=str(mock_repo_root))
    
    assert res["verdict"] == "NO_GO"
    assert "health" in "".join(res["reasons"]).lower()

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_no_go_on_truth_endpoint_failure(mock_urlopen, mock_proc_iter, mock_repo_root):
    mock_proc_iter.return_value = []
    # Mock truth endpoint failing
    def mock_urlopen_fail(url, timeout=None):
        if "/runtime-truth" in url:
            return MockResponse(502, 'Bad Gateway')
        return mock_urlopen_success(url, timeout)
    mock_urlopen.side_effect = mock_urlopen_fail
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    res = gov.evaluate(evidence_dir=str(mock_repo_root))
    
    assert res["verdict"] == "NO_GO"
    assert "runtime_truth" in "".join(res["reasons"]).lower()

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_no_go_on_unknown_source_authority(mock_urlopen, mock_proc_iter, mock_repo_root):
    mock_proc_iter.return_value = []
    # Mock source authority returning UNKNOWN
    def mock_urlopen_unknown(url, timeout=None):
        if "/source-authority" in url:
            return MockResponse(200, '{"status": "UNKNOWN", "sources": {}}')
        return mock_urlopen_success(url, timeout)
    mock_urlopen.side_effect = mock_urlopen_unknown
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    res = gov.evaluate(evidence_dir=str(mock_repo_root))
    
    assert res["verdict"] == "NO_GO"
    assert "source authority status is unknown" in "".join(res["reasons"]).lower()

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_human_approval_mutation(mock_urlopen, mock_proc_iter, mock_repo_root):
    mock_proc_iter.return_value = []
    mock_urlopen.side_effect = mock_urlopen_success
    
    # 1. Setup APPROVED mutation item in the queue
    queue_path = mock_repo_root / "has_live_project_tracker" / "data" / "human_approval_queue.json"
    queue_path.write_text(json.dumps({
        "pending_approvals": [
            {
                "approval_id": "approve-production-mutation-manual",
                "type": "PRODUCTION_MUTATION",
                "status": "APPROVED"
            }
        ]
    }), encoding="utf-8")
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    res = gov.evaluate(evidence_dir=str(mock_repo_root))
    
    assert res["mutation_allowed"] is True
    
    # Verify decision record mutation status
    record = json.loads((mock_repo_root / "decision_record.json").read_text(encoding="utf-8"))
    assert record["mutation_allowed"] is True
    assert record["human_approval_required"] is False

@patch('psutil.process_iter')
@patch('urllib.request.urlopen')
def test_governor_lock_concurrency(mock_urlopen, mock_proc_iter, mock_repo_root):
    mock_proc_iter.return_value = []
    mock_urlopen.side_effect = mock_urlopen_success
    
    gov = RuntimeGovernor(repo_root=mock_repo_root)
    
    # Acquire flock manually on the same path
    lock_file_path = mock_repo_root / "backend" / "runtime_governor.lock"
    lock_file_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_file_path, "w")
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    
    try:
        with pytest.raises(RuntimeError) as excinfo:
            gov.evaluate(evidence_dir=str(mock_repo_root))
        assert "concurrency lock" in str(excinfo.value).lower()
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

def test_codebase_compliance():
    # Execute the static analysis checker from our verify script on our codebase
    assert check_codebase_compliance() is True
