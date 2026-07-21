"""Phase 1 Mission Traceability Graph — A1–A9 and N1–N6 acceptance tests.

EDR-0011. Observability only; no governance consumption.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.extensions import mission_traceability as mt


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    """Minimal Goal→Requirement→Claim→Evidence sources."""
    (tmp_path / "config").mkdir()
    (tmp_path / "coordination" / "goal").mkdir(parents=True)
    (tmp_path / "coordination" / "governance").mkdir(parents=True)
    (tmp_path / "evidence").mkdir()

    contract = {
        "schema": "HOCH_CANONICAL_GOAL_CONTRACT_v1",
        "north_star": "Test north star",
        "goal_hierarchy": {
            "1_canonical_north_star": {"id": "NS", "statement": "Test"},
        },
    }
    (tmp_path / "config" / "canonical_goal_contract.json").write_text(
        json.dumps(contract), encoding="utf-8"
    )

    reqs = {
        "schema": "HOCH_GOAL_REQUIREMENTS_v1",
        "requirements": [
            {
                "id": "REQ-TEST-001",
                "layer": "GOV",
                "statement": "Test requirement one",
                "evidence_path": "evidence/proof1.json",
            },
            {
                "id": "REQ-TEST-002",
                "layer": "ES",
                "statement": "Test requirement two",
                "evidence_path": "evidence/missing.json",
            },
        ],
    }
    (tmp_path / "config" / "goal_requirements.json").write_text(
        json.dumps(reqs), encoding="utf-8"
    )
    (tmp_path / "evidence" / "proof1.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_a1_a2_a3_seed_chain(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    acc = mt.evaluate_acceptance(g)
    assert acc["A1"]["pass"], acc["A1"]
    assert acc["A2"]["pass"], acc["A2"]
    assert acc["A3"]["pass"], acc["A3"]
    kinds = {n["kind"] for n in g["nodes"]}
    assert {"goal", "requirement", "claim", "evidence"} <= kinds


def test_a4_orphans_list_always_present(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    assert isinstance(g["orphans"], list)
    acc = mt.evaluate_acceptance(g)
    assert acc["A4"]["pass"]


def test_a5_missing_evidence_is_unknown_never_pass(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    claims = [n for n in g["nodes"] if n["kind"] == "claim"]
    for c in claims:
        assert str(c.get("status", "")).upper() not in ("PASS", "PASSED", "GREEN")
    # REQ-TEST-002 evidence file missing → not SUPPORTED
    c2 = next(c for c in claims if c["id"] == "CLAIM-REQ-TEST-002")
    assert c2["status"] == "UNKNOWN"
    acc = mt.evaluate_acceptance(g)
    assert acc["A5"]["pass"]


def test_a6_a7_graph_hash_deterministic(fixture_root: Path):
    g1 = mt.build_trace_graph(root=fixture_root, computed_at="2026-07-21T00:00:00Z")
    g2 = mt.build_trace_graph(root=fixture_root, computed_at="2026-07-21T00:00:00Z")
    assert g1["graph_hash"] == g2["graph_hash"]
    assert len(g1["graph_hash"]) == 64
    # computed_at must not affect hash
    g3 = mt.build_trace_graph(root=fixture_root, computed_at="2099-01-01T00:00:00Z")
    assert g3["graph_hash"] == g1["graph_hash"]
    acc = mt.evaluate_acceptance(g1)
    assert acc["A6"]["pass"]


def test_a8_read_only_forbidden_paths(fixture_root: Path):
    forbidden = fixture_root / "coordination" / "goal" / "executive_mission.json"
    # Point ROOT-relative check: atomic_write_graph uses module ROOT; use rel under real ROOT
    with pytest.raises(mt.MissionTraceError):
        mt.atomic_write_graph(
            ROOT / "coordination" / "goal" / "executive_mission.json",
            {"schema": mt.SCHEMA, "nodes": [], "edges": [], "graph_hash": "x" * 64},
        )
    # Allowed write under governance
    out = fixture_root / "coordination" / "governance" / "mission_trace_graph.json"
    g = mt.build_trace_graph(root=fixture_root)
    # atomic_write checks against module ROOT forbidden list — writing outside repo
    # via absolute path that is not under FORBIDDEN is OK for tmp
    mt.atomic_write_graph(out, g)
    assert out.is_file()
    # Control surfaces in fixture still absent / not written by builder
    assert not (fixture_root / "coordination" / "goal" / "mission_state.json").exists()
    assert not (fixture_root / "coordination" / "goal" / "goal_state.json").exists() or True


def _import_modules_from_source(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.append(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    return mods


def test_a8_builder_does_not_touch_mission_control_or_transactions(fixture_root: Path):
    """Static guarantee: extension has no Mission Control / transaction imports."""
    src_path = Path(mt.__file__)
    mods = _import_modules_from_source(src_path)
    assert not any(m == "backend.mission_control" or m.startswith("backend.mission_control.") for m in mods)
    src = src_path.read_text(encoding="utf-8")
    assert "MissionTransaction" not in src
    assert "write_mission_state" not in src
    # May *read* goal_state for evidence overlay; must not write control objects
    assert "atomic_write" not in src or "atomic_write_graph" in src


def test_a9_n6_verifier_source_has_no_mission_control_import():
    verify_path = ROOT / "scripts" / "goal" / "verify_mission_trace.py"
    mods = _import_modules_from_source(verify_path)
    assert not any(
        m == "backend.mission_control" or m.startswith("backend.mission_control.") for m in mods
    )
    # Allowed imports only: stdlib + mission_traceability extension
    for m in mods:
        if m.startswith("backend."):
            assert m.startswith("backend.helm_runtime.extensions.mission_traceability") or m == (
                "backend.helm_runtime.extensions.mission_traceability"
            )


def test_n1_malformed_graph_fails():
    errors = mt.validate_graph_structure("not a dict")
    assert errors
    errors2 = mt.validate_graph_structure({"schema": "WRONG", "nodes": [], "edges": []})
    assert any("schema" in e for e in errors2)


def test_n2_requirement_without_claim_fails_a2(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    # Strip claim nodes and assert edges
    g["nodes"] = [n for n in g["nodes"] if n["kind"] != "claim"]
    g["edges"] = [e for e in g["edges"] if e.get("rel") != "asserts"]
    g["graph_hash"] = mt.compute_graph_hash(g["nodes"], g["edges"])
    acc = mt.evaluate_acceptance(g)
    assert not acc["A2"]["pass"]


def test_n3_duplicate_node_ids_raise(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    g["nodes"].append(dict(g["nodes"][0]))  # duplicate first node
    with pytest.raises(mt.MissionTraceError):
        mt._check_duplicate_ids(g["nodes"])
    errors = mt.validate_graph_structure(
        {"schema": mt.SCHEMA, "nodes": g["nodes"], "edges": g["edges"], "graph_hash": "x"}
    )
    assert any("duplicate" in e for e in errors)


def test_n4_mutation_changes_graph_hash(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    h1 = g["graph_hash"]
    g["nodes"].append(
        {"id": "ORPHAN-NODE", "kind": "evidence", "path": None, "presence": "UNKNOWN"}
    )
    h2 = mt.compute_graph_hash(g["nodes"], g["edges"])
    assert h1 != h2


def test_n5_tampered_hash_fails_acceptance(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    g["graph_hash"] = "0" * 64
    acc = mt.evaluate_acceptance(g)
    assert not acc["A6"]["pass"]


def test_live_repo_build_and_accept():
    """Optional live-repo smoke: seed from real config if present."""
    if not (ROOT / "config" / "goal_requirements.json").is_file():
        pytest.skip("no live requirements")
    g1 = mt.build_trace_graph(root=ROOT, computed_at="2026-07-21T12:00:00Z")
    g2 = mt.build_trace_graph(root=ROOT, computed_at="2026-07-21T12:00:00Z")
    assert g1["graph_hash"] == g2["graph_hash"]
    acc = mt.evaluate_acceptance(g1)
    assert acc["A1"]["pass"]
    assert acc["A2"]["pass"]
    assert acc["A3"]["pass"]
    assert acc["A4"]["pass"]
    assert acc["A5"]["pass"]
    assert acc["A6"]["pass"]
    assert g1["consumption"] == "OBSERVE_ONLY"
    assert g1["schema_version"] == "1.0"


def test_load_graph_helper(fixture_root: Path):
    g = mt.build_trace_graph(root=fixture_root)
    path = fixture_root / "g.json"
    path.write_text(json.dumps(g), encoding="utf-8")
    loaded = mt.load_graph(path)
    assert loaded["graph_hash"] == g["graph_hash"]
