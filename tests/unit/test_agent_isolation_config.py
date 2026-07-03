"""Verify config-level agent isolation guards are in place.

Does NOT execute sudo or create users — that is operator work (setup_agent_user.sh).
Tests here assert the launchd plists declare the correct UserName and that the
founder key path is outside the repo boundary the agent user can access.
"""
from pathlib import Path
import plistlib
import pytest

REPO = Path(__file__).resolve().parents[2]


def _load_plist(path: Path) -> dict:
    return plistlib.loads(path.read_bytes())


def test_runtime_plist_declares_agent_user():
    p = REPO / "com.hoch.agent.swarm.runtime.plist"
    assert p.exists(), "runtime plist missing"
    d = _load_plist(p)
    assert d.get("UserName") == "hoch_agent", (
        "launchd plist must run as hoch_agent, not as the founder's account. "
        "A compromised agent running as michaelhoch can read ~/.has_founder/. "
        "Run scripts/setup_agent_user.sh and set UserName=hoch_agent."
    )


def test_tracker_daemon_plist_declares_agent_user():
    p = REPO / "has_live_project_tracker" / "tracker-daemon.plist"
    if not p.exists():
        pytest.skip("tracker daemon plist not present")
    d = _load_plist(p)
    assert d.get("UserName") == "hoch_agent", "tracker daemon must run as hoch_agent"


def test_founder_key_outside_repo():
    """The founder key must never be inside the repo tree."""
    founder_key = Path.home() / ".has_founder" / "founder_signing_key"
    repo = REPO.resolve()
    try:
        founder_key.relative_to(repo)
        pytest.fail("Founder key is INSIDE the repo — agents can read it!")
    except ValueError:
        pass  # key is outside repo, good


def test_agent_cannot_path_traverse_to_founder_key():
    """Boundary check: hoch_agent_swarm path cannot reach ~/.has_founder."""
    from backend.mission_control.boundary import validate_secure_boundary, BoundaryViolation
    founder = str(Path.home() / ".has_founder" / "founder_signing_key")
    with pytest.raises(BoundaryViolation):
        validate_secure_boundary("has", "read", {"path": founder})
