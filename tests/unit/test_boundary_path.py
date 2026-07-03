"""CWE-23 partial-path-traversal regression tests for secure_boundary."""
import os
import pytest
from backend.mission_control.boundary import validate_secure_boundary, BoundaryViolation

HOME = os.path.expanduser("~")
INSIDE = os.path.join(HOME, "hoch_agent_swarm", "artifacts", "x.json")
SIBLING = os.path.join(HOME, "hoch_agent_swarm_evil", "steal.json")  # the bug
OUTSIDE = "/etc/passwd"
ESCAPE = os.path.join(HOME, "hoch_agent_swarm", "..", "..", "etc", "passwd")


def test_inside_allowed():
    assert validate_secure_boundary("has", "run", {"path": INSIDE}) is True


def test_sibling_prefix_rejected():
    """The exact bug: sibling dir sharing the root's string prefix."""
    with pytest.raises(BoundaryViolation):
        validate_secure_boundary("has", "run", {"path": SIBLING})


def test_absolute_outside_rejected():
    with pytest.raises(BoundaryViolation):
        validate_secure_boundary("has", "run", {"path": OUTSIDE})


def test_dotdot_escape_rejected():
    with pytest.raises(BoundaryViolation):
        validate_secure_boundary("has", "run", {"path": ESCAPE})


def test_nul_byte_rejected():
    with pytest.raises(BoundaryViolation):
        validate_secure_boundary("has", "run", {"path": INSIDE + "\x00.txt"})


def test_no_path_param_ok():
    assert validate_secure_boundary("has", "run", {}) is True
