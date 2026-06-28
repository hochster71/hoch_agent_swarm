from unittest.mock import patch, mock_open
import os
import json
from backend.main import production_readiness

def test_release_authorization_pending_when_missing():
    orig_exists = os.path.exists
    def mock_exists(path):
        if "release_authorization.json" in str(path):
            return False
        return orig_exists(path)
        
    with patch("os.path.exists", side_effect=mock_exists):
        res = production_readiness()
        assert res["go_no_go"] == "PENDING_VERIFICATION"

def test_release_authorization_pending_when_unauthorized():
    mock_data = json.dumps({"authorized": False, "verdict": "PENDING_VERIFICATION"})
    
    orig_exists = os.path.exists
    def mock_exists(path):
        if "release_authorization.json" in str(path):
            return True
        return orig_exists(path)

    with patch("os.path.exists", side_effect=mock_exists):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            res = production_readiness()
            assert res["go_no_go"] == "PENDING_VERIFICATION"

def test_release_authorization_go_when_authorized():
    mock_data = json.dumps({"authorized": True, "verdict": "GO"})
    
    orig_exists = os.path.exists
    def mock_exists(path):
        if "release_authorization.json" in str(path):
            return True
        return orig_exists(path)

    with patch("os.path.exists", side_effect=mock_exists):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            res = production_readiness()
            assert res["go_no_go"] == "GO"
