"""Mission State Engine — executive operational view."""

from backend.mission_control.mission_state import (
    build_mission_state,
    render_executive_text,
    render_speech,
    write_mission_state,
)


def test_build_mission_state_shape():
    s = build_mission_state()
    assert s["schema"] == "HELM_MISSION_STATE_v1"
    assert "mission" in s
    assert "dashboard" in s
    assert "critical_path" in s
    assert "overall" in s
    assert s["overall"]["status"] in (
        "BLOCKED_EXTERNAL",
        "BLOCKED_FOUNDER",
        "READY_INTERNAL",
        "IN_PROGRESS",
        "UNKNOWN",
    )
    # Revenue must not claim earnings without ledger dollars
    rev = s.get("revenue") or {}
    assert rev.get("status") in ("NOT_STARTED", "LIVE", "UNKNOWN")
    if rev.get("status") == "NOT_STARTED":
        assert rev.get("settled_usd") in (0, 0.0, None)


def test_executive_text_has_table_and_path():
    t = render_executive_text()
    assert "MISSION" in t
    assert "Critical Path" in t
    assert "Area" in t


def test_write_and_speech():
    s = write_mission_state()
    sp = render_speech(s)
    assert "Mission" in sp
    assert len(sp) > 20


def test_api_mission_routes():
    from fastapi.testclient import TestClient
    import backend.helm_live_api as api

    c = TestClient(api.app)
    r = c.get("/api/v1/helm/mission")
    assert r.status_code == 200
    body = r.json()
    # wrapped in truth_response
    assert body.get("truth_class") == "HELM_MISSION_STATE" or "dashboard" in body
    r2 = c.get("/api/v1/helm/mission/executive")
    assert r2.status_code == 200
    assert "Critical Path" in r2.text
    r3 = c.get("/mission")
    assert r3.status_code == 200
    assert "MISSION STATE" in r3.text
