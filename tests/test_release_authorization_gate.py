from unittest.mock import patch, mock_open, MagicMock
import os
import json
import builtins
from pathlib import Path

# Save original functions
orig_exists = os.path.exists
orig_open = builtins.open

def setup_readiness_mocks(monkeypatch, authorization_data=None):
    # Mock os.path.exists
    def mock_exists(path):
        path_str = str(path)
        if "release_authorization.json" in path_str:
            return authorization_data is not None
        if any(cfg in path_str for cfg in [
            "hoch_pert_workstreams.json",
            "hoch_northstar_controls.json",
            "asset_trust_registry.json",
            "cluster_worker_profiles.json",
            "port_hardening_audit.json",
            "skill_registry.json",
            "qa_evidence_matrix.json"
        ]):
            return True
        return orig_exists(path)
    monkeypatch.setattr(os.path, "exists", mock_exists)

    # Mock Path.exists
    orig_path_exists = Path.exists
    def mock_path_exists(self):
        path_str = str(self)
        if "release_authorization.json" in path_str:
            return authorization_data is not None
        if any(cfg in path_str for cfg in [
            "hoch_pert_workstreams.json",
            "hoch_northstar_controls.json",
            "asset_trust_registry.json",
            "cluster_worker_profiles.json",
            "port_hardening_audit.json",
            "skill_registry.json",
            "qa_evidence_matrix.json"
        ]):
            return True
        return orig_path_exists(self)
    monkeypatch.setattr(Path, "exists", mock_path_exists)

    # Mock builtins.open
    def mock_open_file(path, *args, **kwargs):
        path_str = str(path)
        if "release_authorization.json" in path_str:
            if authorization_data is not None:
                m = mock_open(read_data=json.dumps(authorization_data))
                return m(path, *args, **kwargs)
            raise FileNotFoundError()
        if "hoch_pert_workstreams.json" in path_str:
            return mock_open(read_data='{"workstreams": [{"id": "P1"}, {"id": "P2"}, {"id": "P3"}, {"id": "P4"}, {"id": "P8"}, {"id": "P5"}, {"id": "P9"}]}')(path, *args, **kwargs)
        if "hoch_northstar_controls.json" in path_str:
            return mock_open(read_data='{"northstar_sealed": true}')(path, *args, **kwargs)
        if "asset_trust_registry.json" in path_str:
            return mock_open(read_data='{"nodes": []}')(path, *args, **kwargs)
        if "cluster_worker_profiles.json" in path_str:
            return mock_open(read_data='{"profiles": []}')(path, *args, **kwargs)
        if "port_hardening_audit.json" in path_str:
            return mock_open(read_data='{"summary": {"overall_status": "PASS", "swarm_ports_compliant": 2, "non_swarm_lan_review_required": 0}}')(path, *args, **kwargs)
        if "skill_registry.json" in path_str:
            return mock_open(read_data='{}')(path, *args, **kwargs)
        if "qa_evidence_matrix.json" in path_str:
            controls_list = [{"id": f"C{i}", "tests": [{"batch": "P9", "result": "PASS"}]} for i in range(10)]
            data = {"summary": {"tested": 10, "pending": 0, "tests_pass": 10, "total_tests": 10, "ready_for_p9": True, "matrix_status": "PASS"}, "controls": controls_list}
            return mock_open(read_data=json.dumps(data))(path, *args, **kwargs)
        return orig_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", mock_open_file)

    # Mock Path.read_text
    orig_read_text = Path.read_text
    def mock_read_text(self, *args, **kwargs):
        path_str = str(self)
        if "hoch_pert_workstreams.json" in path_str:
            return '{"workstreams": [{"id": "P1"}, {"id": "P2"}, {"id": "P3"}, {"id": "P4"}, {"id": "P8"}, {"id": "P5"}, {"id": "P9"}]}'
        if "hoch_northstar_controls.json" in path_str:
            return '{"northstar_sealed": true}'
        if "asset_trust_registry.json" in path_str:
            return '{"nodes": []}'
        if "cluster_worker_profiles.json" in path_str:
            return '{"profiles": []}'
        if "port_hardening_audit.json" in path_str:
            return '{"summary": {"overall_status": "PASS", "swarm_ports_compliant": 2, "non_swarm_lan_review_required": 0}}'
        if "skill_registry.json" in path_str:
            return '{}'
        if "qa_evidence_matrix.json" in path_str:
            controls_list = [{"id": f"C{i}", "tests": [{"batch": "P9", "result": "PASS"}]} for i in range(10)]
            data = {"summary": {"tested": 10, "pending": 0, "tests_pass": 10, "total_tests": 10, "ready_for_p9": True, "matrix_status": "PASS"}, "controls": controls_list}
            return json.dumps(data)
        return orig_read_text(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", mock_read_text)

    # Mock get_registry_summary
    from backend.skill_gate import get_registry_summary
    monkeypatch.setattr("backend.main._sg_summary", lambda: {"gate_status": "ACTIVE", "total_skills": 10})

    # Mock FinalVerdict
    from backend.final_verifier.final_verdict import FinalVerdict
    monkeypatch.setattr(FinalVerdict, "get_final_verdict", lambda self: {"status": "VERIFIED", "readiness_score": 100.0, "readiness_caps": []})

    # Mock glob.glob
    import glob
    monkeypatch.setattr(glob, "glob", lambda *args, **kwargs: ["attestation-bundle-mock"])

def test_release_authorization_pending_when_missing(monkeypatch):
    setup_readiness_mocks(monkeypatch, authorization_data=None)
    from backend.main import production_readiness
    res = production_readiness()
    assert res["go_no_go"] == "PENDING_VERIFICATION"

def test_release_authorization_pending_when_unauthorized(monkeypatch):
    setup_readiness_mocks(monkeypatch, authorization_data={"authorized": False, "verdict": "PENDING_VERIFICATION"})
    from backend.main import production_readiness
    res = production_readiness()
    assert res["go_no_go"] == "PENDING_VERIFICATION"

def test_release_authorization_go_when_authorized(monkeypatch):
    setup_readiness_mocks(monkeypatch, authorization_data={"authorized": True, "verdict": "GO"})
    from backend.main import production_readiness
    res = production_readiness()
    assert res["go_no_go"] == "GO"
