"""H4 safety net: guard the security-critical endpoint surface of main.py.

A 12k-line main.py is one bad merge from silently dropping a gate. Until the
file is split into routers, this test pins the set of security-critical routes
(approval, release-authority, promotion, security-ops) so their accidental
removal fails CI loudly. It also caps regrowth of the monolith.

This is a structural guard, not a behavioral test — it asserts the routes
still exist and that the founder-signature enforcement string is present.
"""
import re
from pathlib import Path

MAIN = Path(__file__).resolve().parents[2] / "backend" / "main.py"
SRC = MAIN.read_text()

# Security-critical routes that must never silently disappear.
REQUIRED_ROUTES = [
    "/api/v1/approvals/{approval_id}/decision",
    "/api/v1/release/authority/request",
    "/api/v1/release/promote",
    "/api/v1/security-ops/accept-risk",
    "/api/approval/requests/{approval_id}/decisions",
]


def test_required_security_routes_present():
    missing = [r for r in REQUIRED_ROUTES if r not in SRC]
    assert not missing, f"Security-critical routes missing from main.py: {missing}"


def test_release_authority_enforces_founder_signature():
    """C2 guard: the authority endpoint must still call verify_release_authority."""
    assert "verify_release_authority" in SRC, \
        "release/authority/request no longer enforces founder signature!"


def test_approval_decision_passes_signature_through():
    assert "founder_signature=req.founder_signature" in SRC, \
        "approval decision endpoint dropped founder_signature passthrough!"


def test_main_py_not_growing_unbounded():
    """Cap regrowth. Ratchet DOWN as main.py is split into routers; never up.
    Current baseline ~12.1k lines — fail if it grows past 12.5k without a split."""
    lines = SRC.count("\n")
    assert lines < 12500, (
        f"main.py has {lines} lines (> 12500 ceiling). Extract endpoints into "
        f"backend/routers/ before adding more — see docs/security/main-split-plan.md"
    )
