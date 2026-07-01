import os
import pytest
from unittest import mock
from backend.runtime_paths import (
    project_root,
    data_root,
    evidence_root,
    resolve_under_project,
    optional_ag_scratch_root,
    optional_ag_brain_root
)

def test_default_roots():
    # Clear env vars to check defaults
    with mock.patch("os.path.exists", return_value=True):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert str(project_root()) == "/app"
            assert str(data_root()) == "/app/data"
            assert str(evidence_root()) == "/app/docs/evidence"
            assert str(optional_ag_scratch_root()) == "/app/data/ag_scratch"
            assert str(optional_ag_brain_root()) == "/app/data/ag_brain"

def test_root_override():
    with mock.patch.dict(os.environ, {
        "HAS_PROJECT_ROOT": "/custom/project",
        "HAS_DATA_ROOT": "/custom/data",
        "HAS_EVIDENCE_ROOT": "/custom/evidence"
    }):
        assert str(project_root()) == "/custom/project"
        assert str(data_root()) == "/custom/data"
        assert str(evidence_root()) == "/custom/evidence"

def test_resolve_under_project():
    with mock.patch.dict(os.environ, {"HAS_PROJECT_ROOT": "/app"}):
        resolved = resolve_under_project("backend", "main.py")
        assert str(resolved) == "/app/backend/main.py"
        
        # Test traversal protection
        with pytest.raises(ValueError):
            resolve_under_project("..", "etc", "passwd")

def test_no_users_path_emitted():
    with mock.patch("os.path.exists", return_value=True):
        with mock.patch.dict(os.environ, {}, clear=True):
            for path_fn in [project_root, data_root, evidence_root, optional_ag_scratch_root, optional_ag_brain_root]:
                assert "Users" not in str(path_fn())
                assert "michaelhoch" not in str(path_fn())
