"""Tests for the EDR-0003 normalization layer (backend/helm_runtime/normalization.py).

Covers the four EDR-0003 fixes as code invariants:
  N2 — one canonical /mission shape (regression: bridge projection == normalizer).
  N3 — alias table round-trips both ways.
  N4 — verification hash is implementation-only and doc-edit stable.
Plus dispatch/worker/provider record normalization to canonical shapes.
"""
from __future__ import annotations

from backend.helm_runtime import normalization as N


# --------------------------------------------------------------------------- #
# N2 — canonical mission shape
# --------------------------------------------------------------------------- #

def test_mission_view_always_canonical_shape():
    view = N.normalize_mission_view({"mission_version": 7, "state": "ACTIVE"})
    assert set(view.keys()) == set(N.CANONICAL_MISSION_FIELDS)
    assert view["mission_version"] == 7
    assert view["occ_note"].startswith("PATCH must send expected_parent_version")
    assert N.mission_shape_ok(view)


def test_mission_view_absent_mission_keeps_version_key_none():
    # Fail-closed: absent mission still has mission_version present, as None.
    view = N.normalize_mission_view({"error": "MISSION_ABSENT", "mission_version": None})
    assert "mission_version" in view
    assert view["mission_version"] is None
    assert N.mission_shape_ok(view)


def test_mission_view_none_doc_is_canonical():
    view = N.normalize_mission_view(None)
    assert N.mission_shape_ok(view)
    assert all(view[f] is None for f in N.CANONICAL_MISSION_FIELDS if f != "occ_note")


def test_mission_view_folds_legacy_keys_without_shadowing_canonical():
    view = N.normalize_mission_view({"version": 3, "status": "DEGRADED"})
    assert view["mission_version"] == 3          # 'version' folded in
    assert view["operational_status"] == "DEGRADED"  # 'status' folded in
    # Canonical key wins when both present.
    view2 = N.normalize_mission_view({"version": 3, "mission_version": 9})
    assert view2["mission_version"] == 9


def test_mission_view_hint_overrides_record_hint():
    hint = {"control_object": "executive_mission"}
    view = N.normalize_mission_view({"mission_version": 1, "projection_hint": {"old": True}}, hint=hint)
    assert view["projection_hint"] == hint


def test_mission_shape_ok_rejects_extra_or_missing_keys():
    good = N.normalize_mission_view({"mission_version": 1})
    assert N.mission_shape_ok(good)
    extra = dict(good, unexpected="x")
    assert not N.mission_shape_ok(extra)
    missing = {k: v for k, v in good.items() if k != "mission_version"}
    assert not N.mission_shape_ok(missing)


def test_regression_bridge_projection_matches_normalizer():
    """N2 regression: the canonical shape is single — the frozen bridge
    projection and the normalizer agree field-for-field for the same inputs."""
    from backend.helm_runtime.bridge_api import _mission_view

    bridge = _mission_view()  # reads real mission + real hint
    from backend.helm_runtime.mission_store import read_mission
    from backend.helm_runtime.mission_runtime import mission_projection_hint

    norm = N.normalize_mission_view(read_mission(), hint=mission_projection_hint())
    assert set(bridge.keys()) == set(norm.keys()) == set(N.CANONICAL_MISSION_FIELDS)
    assert bridge == norm


# --------------------------------------------------------------------------- #
# N3 — alias table
# --------------------------------------------------------------------------- #

def test_alias_table_round_trips_both_ways():
    for entry in N.alias_table():
        canonical = entry["constitutional"]
        for alias in entry["code_aliases"]:
            assert N.constitutional_name(alias) == canonical
        # canonical resolves to itself
        assert N.constitutional_name(canonical) == canonical
        assert N.code_aliases(canonical) == entry["code_aliases"]


def test_alias_lookup_unknown_returns_none():
    assert N.constitutional_name("nonexistent_thing.py") is None
    assert N.code_aliases("Nonexistent Registry") == []


def test_alias_table_is_a_copy_not_internal_state():
    t = N.alias_table()
    t.append({"constitutional": "Injected", "code_aliases": [], "kind": "x"})
    assert N.constitutional_name("Injected") is None  # internal table untouched


# --------------------------------------------------------------------------- #
# Worker / provider / dispatch record normalization
# --------------------------------------------------------------------------- #

def test_normalize_worker_record_from_gateway_row():
    from backend.helm_runtime.dispatch_gateway import default_gateway

    for row in default_gateway().worker_role_health():
        norm = N.normalize_worker_record(row)
        assert set(norm.keys()) == set(N.CANONICAL_WORKER_FIELDS)
        assert norm["status"] in ("AVAILABLE", "BLOCKED")
        assert norm == row  # gateway rows are already canonical → identity


def test_normalize_worker_record_from_binding_maps_provider_to_binding():
    binding = {"role": "builder", "provider": "anthropic", "model": "claude", "configured": True}
    norm = N.normalize_worker_record(binding)
    assert norm["binding"] == "anthropic"
    # No dispatch_enabled flag on a raw binding → fail-closed BLOCKED.
    assert norm["dispatch_enabled"] is False
    assert norm["status"] == "BLOCKED"


def test_normalize_worker_status_derived_from_dispatch_enabled():
    enabled = N.normalize_worker_record({"role": "builder", "dispatch_enabled": True})
    assert enabled["status"] == "AVAILABLE"


def test_normalize_provider_health():
    from backend.helm_runtime.dispatch_gateway import default_gateway

    for h in default_gateway().health():
        norm = N.normalize_provider_health(h)
        assert set(norm.keys()) == set(N.CANONICAL_PROVIDER_FIELDS)
        assert norm["status"] in ("READY", "BLOCKED")
        assert norm["dispatch_implemented"] is False  # skeleton


def test_normalize_dispatch_record_fail_closed_default():
    # Unknown/missing outcome → 'blocked', never a fake 'dispatched'.
    assert N.normalize_dispatch_record({})["outcome"] == "blocked"
    assert N.normalize_dispatch_record({"outcome": "weird"})["outcome"] == "blocked"
    assert N.normalize_dispatch_record({"outcome": "dispatched"})["outcome"] == "dispatched"


def test_normalize_dispatch_record_lowercases_provider():
    rec = N.normalize_dispatch_record({"provider": "Anthropic", "role": "builder", "outcome": "error"})
    assert rec["provider"] == "anthropic"
    assert set(rec.keys()) == set(N.CANONICAL_DISPATCH_FIELDS)


# --------------------------------------------------------------------------- #
# N4 — implementation-only hashing
# --------------------------------------------------------------------------- #

def test_is_implementation_path():
    assert N.is_implementation_path("backend/helm_runtime/transaction.py")
    assert N.is_implementation_path("coordination/governance/role_bindings.json")
    assert N.is_implementation_path("tests/helm_runtime/test_bridge.py")
    # Docs / EDRs / reports are NOT implementation.
    assert not N.is_implementation_path("docs/helm/edr/EDR-0003-normalization.md")
    assert not N.is_implementation_path("docs/evidence/audit/report.json")
    assert not N.is_implementation_path("README.md")
    assert not N.is_implementation_path("notes.txt")


def test_hash_implementation_excludes_docs_and_is_stable():
    impl_only = [
        ("backend/helm_runtime/x.py", b"code-a"),
        ("coordination/governance/y.json", b"config-b"),
    ]
    with_docs = impl_only + [
        ("docs/helm/edr/EDR-0003-normalization.md", b"prose that changes often"),
        ("docs/evidence/audit/report.json", b"report body"),
    ]
    # N4: editing/adding docs must NOT change the id.
    assert N.hash_implementation(impl_only) == N.hash_implementation(with_docs)


def test_hash_implementation_changes_when_code_changes():
    a = [("backend/helm_runtime/x.py", b"code-a")]
    b = [("backend/helm_runtime/x.py", b"code-b")]
    assert N.hash_implementation(a) != N.hash_implementation(b)


def test_hash_implementation_order_independent():
    a = [("b.py", b"2"), ("a.py", b"1")]
    b = [("a.py", b"1"), ("b.py", b"2")]
    assert N.hash_implementation(a) == N.hash_implementation(b)


def test_hash_implementation_paths_skips_missing(tmp_path):
    (tmp_path / "real.py").write_bytes(b"x")
    digest = N.hash_implementation_paths(tmp_path, ["real.py", "ghost.py"])
    # Only 'real.py' contributes; equal to hashing it alone.
    assert digest == N.hash_implementation([("real.py", b"x")])
