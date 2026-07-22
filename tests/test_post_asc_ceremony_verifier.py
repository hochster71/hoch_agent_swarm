"""Synthetic positive/negative paths for scripts/goal/verify_post_asc_ceremony.py
(v3 — founder preflight closeout, 2026-07-22).

The live positive path can only be demonstrated after the founder's real
ceremony; these tests prove the verifier's LOGIC on fabricated artifact sets
in an isolated root:

  P1   fully consistent post-ceremony set          -> exit 0, WITHHELD
  V1   verifier is strictly read-only (byte-identical root before/after)
  T1a  ceremony-id strict format
  T1b  ceremony-id uniqueness across 10,000 generations
  F1   missing ceremony store                       -> FAIL, exit 1
  F2   snapshot/receipt ceremony-id mismatch        -> identity FAIL
  F3   malformed snapshot JSON                      -> explicit FAIL
  F4   recompute artifact predates ceremony         -> temporal FAIL
  F5   recompute chain rc != 0                      -> step FAIL
  F6   goal SATISFIED but Apple IN_REVIEW           -> INCONSISTENT
  F7   Apple REJECTED                               -> verbatim FAIL
  F8   Apple IN_REVIEW honest advisory              -> EXTERNAL-PENDING, exit 0
  R1   temp receipt file present                    -> store FAIL
  R2   partially written receipt                    -> store FAIL
  R3   filename/internal-id disagreement            -> store FAIL
  R4   two receipts, same started_at                -> ambiguous, FAIL
  R5   snapshot digest mismatch vs receipt          -> binding FAIL
  R6   output digest changed w/o newer timestamp    -> tamper FAIL
  R7   rollback: ledger last entry is older receipt -> FAIL
  R8   superseded older receipt + honest ledger     -> newest wins, exit 0
  R9   unknown/unmapped Apple state                 -> FAIL-CLOSED
  R10  gate-script digest mismatch                  -> binding FAIL
"""
from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _verifier():
    return _load("scripts/goal/verify_post_asc_ceremony.py",
                 "verify_post_asc_ceremony")


def _gate():
    return _load("scripts/founder/asc_credentials_gate.py",
                 "asc_credentials_gate_mod")


def _iso(minutes_ago: float) -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=minutes_ago)).isoformat()


def _cid(minutes_ago: float, suffix: str = "8f2c9a16d76b4310") -> str:
    ts = (datetime.datetime.now(datetime.timezone.utc)
          - datetime.timedelta(minutes=minutes_ago))
    return "ASC-CEREMONY-" + ts.strftime("%Y%m%dT%H%M%S.%fZ") + "-" + suffix


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_root(tmp_path: Path, *, state="READY_FOR_SALE", req_state="SATISFIED",
              snap_cid=None, chain_rc=0, gates_minutes_ago=50.0,
              gate_status="PASS", started_minutes_ago=60.0) -> tuple[Path, str]:
    """Fabricate a complete, internally consistent post-ceremony artifact set."""
    cid = _cid(started_minutes_ago)

    def w(rel, obj) -> Path:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=1))
        return p

    # goal artifacts first (so the receipt can bind their digests)
    gates_ts = _iso(gates_minutes_ago)
    p_gates = w("coordination/goal/champion_gates.json", {
        "generated_at": gates_ts,
        "gates": [
            {"gate": "TESTFLIGHT", "status": gate_status,
             "evidence": ["asc:builds"], "detail": "fixture"},
            {"gate": "APP_STORE_CONNECT", "status": gate_status,
             "evidence": ["asc:appStoreVersions"], "detail": "fixture"},
        ]})
    goal_ts = _iso(53)
    p_goal = w("coordination/goal/goal_state.json", {
        "computed_at": goal_ts,
        "requirements_detail": [
            {"id": "REQ-CP-APP_STORE_CONNECT", "state": req_state,
             "validator": "fixture", "checked_at": goal_ts}]})
    p_mission = w("coordination/goal/mission_state.json",
                  {"computed_at": goal_ts})
    shipped_ts = _iso(54)
    p_shipped = w("coordination/goal/shipped_report.json", {
        "read_at": shipped_ts, "asc_state": state,
        "shipped": state == "READY_FOR_SALE", "asc_detail": ""})
    w("coordination/goal/build_to_goal_status.json", {
        "updated_at": _iso(50), "percent_to_goal": 90.0, "state": "PARTIAL",
        "nodes": {"N3_VERIFY": "HOLD"}})
    w("coordination/goal/intake_to_doorstep.json", {"computed_at": _iso(45)})
    w("coordination/security/helm_control_posture.json", {
        "assessed_at": _iso(600), "posture_percent": 76.9,
        "controls_assessed": 13})
    p_snap = w("coordination/evidence/external/asc_epic_fury.json", {
        "appStoreState": state, "versionString": "1.0.2",
        "observed_at": _iso(started_minutes_ago - 2),
        "bundle_id": "com.epicfury.dashboard",
        "ceremony_id": snap_cid or cid, "source": "live read (test fixture)"})
    gate_stub = tmp_path / "scripts/founder/asc_credentials_gate.py"
    gate_stub.parent.mkdir(parents=True, exist_ok=True)
    gate_stub.write_text("# gate script stand-in\n")

    def bind(p: Path, ts: str) -> dict:
        return {"path": str(p.relative_to(tmp_path)), "sha256": _sha(p),
                "timestamp": ts, "parsed_state": {}}

    receipt = {
        "schema": "ASC_CEREMONY_RECEIPT_v2", "ceremony_id": cid,
        "started_at": _iso(started_minutes_ago),
        "validated_at": _iso(started_minutes_ago - 2),
        "bundle_id": "com.epicfury.dashboard", "appStoreState": state,
        "snapshot_binding": {
            "path": "coordination/evidence/external/asc_epic_fury.json",
            "sha256": _sha(p_snap),
            "observed_at": _iso(started_minutes_ago - 2)},
        "gate_script_digest": _sha(gate_stub),
        "git_head": "deadbeef" * 5,
        "worktree_status_digest_at_start": "0" * 64,
        "recompute_chain": [
            {"step": "champion_gate_recompute",
             "cmd": "scripts/goal/verify_champion_gates.py",
             "returncode": chain_rc, "completed_at": _iso(55),
             "correlation": "receipt-bound digest",
             "outputs": [bind(p_gates, gates_ts)]},
            {"step": "shipped_recompute",
             "cmd": "scripts/goal/verify_shipped.py",
             "returncode": chain_rc, "completed_at": _iso(54),
             "correlation": "receipt-bound digest",
             "outputs": [bind(p_shipped, shipped_ts)]},
            {"step": "goal_engine_recompute",
             "cmd": "scripts/goal/goal_engine.py",
             "returncode": chain_rc, "completed_at": _iso(53),
             "correlation": "receipt-bound digest",
             "outputs": [bind(p_goal, goal_ts), bind(p_mission, goal_ts)]},
            {"step": "pert_regeneration", "cmd": None, "returncode": None,
             "status": "DEFERRED_TO_POST_GATE_LANE",
             "outputs": [{"path": "coordination/goal/build_to_goal_status.json"}],
             "correlation": "temporal(started_at)"},
            {"step": "doorstep_regeneration", "cmd": None, "returncode": None,
             "status": "DEFERRED_TO_POST_GATE_LANE",
             "outputs": [{"path": "coordination/goal/intake_to_doorstep.json"}],
             "correlation": "temporal(started_at)"},
        ]}
    cdir = tmp_path / "coordination/evidence/external/asc_ceremonies"
    cdir.mkdir(parents=True, exist_ok=True)
    rp = cdir / f"{cid}.json"
    rp.write_text(json.dumps(receipt, indent=1))
    (cdir / "LEDGER.jsonl").write_text(json.dumps(
        {"ceremony_id": cid, "started_at": receipt["started_at"],
         "receipt_sha256": _sha(rp)}) + "\n")
    return tmp_path, cid


def _by(rows):
    return {r["label"]: r for r in rows}


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


# ---- P1 / V1 / T1 -----------------------------------------------------------------

def test_p1_consistent_ceremony_passes_but_stays_withheld(tmp_path):
    root, cid = make_root(tmp_path)
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 0
    assert by["Overall posture"]["status"] == "WITHHELD"
    assert by["Ceremony receipt store"]["ok"] is True
    assert by["Ceremony receipt & identity"]["ok"] is True
    assert by["Apple snapshot digest binding"]["ok"] is True
    assert by["Gate script digest binding"]["ok"] is True
    assert by["REQ-CP-APP_STORE_CONNECT"]["status"] == "SATISFIED"
    assert by["Champion-gate recomputation"]["ok"] is True
    for r in rows:
        if r["source"] and r["source"] not in (".git",
                                               "coordination/evidence/external/asc_ceremonies"):
            assert r["sha256"], r["label"]


def test_v1_verifier_is_strictly_read_only(tmp_path):
    root, _ = make_root(tmp_path)
    before = _tree_digest(root)
    _verifier().run(root)
    assert _tree_digest(root) == before


def test_t1a_ceremony_id_strict_format():
    gate = _gate()
    cid = gate.generate_ceremony_id()
    assert gate.CEREMONY_ID_RE.match(cid)
    v = _verifier()
    assert v.CEREMONY_ID_RE.match(cid)  # gate and verifier agree on format
    assert "ASC-CEREMONY-" in cid and cid.count("-") == 3
    ts, suffix = cid.rsplit("-", 1)[0].split("ASC-CEREMONY-")[1], cid.rsplit("-", 1)[1]
    assert "." in ts and ts.endswith("Z")   # microseconds present
    assert len(suffix) == 16                # 64 bits of randomness
    for banned in ("KEYID", "ISSUER", "michael", "hoch"):
        assert banned.lower() not in cid.lower()


def test_t1b_ceremony_id_uniqueness_10000():
    gate = _gate()
    ids = {gate.generate_ceremony_id() for _ in range(10_000)}
    assert len(ids) == 10_000


# ---- F-series ---------------------------------------------------------------------

def test_f1_missing_store_fails_closed(tmp_path):
    root, _ = make_root(tmp_path)
    shutil.rmtree(root / "coordination/evidence/external/asc_ceremonies")
    rows, code = _verifier().run(root)
    assert code == 1
    assert _by(rows)["Ceremony receipt store"]["ok"] is False


def test_f2_ceremony_id_mismatch_fails(tmp_path):
    root, _ = make_root(tmp_path, snap_cid=_cid(999, "aaaaaaaaaaaaaaaa"))
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["Ceremony receipt & identity"]["ok"] is False
    assert "identity mismatch" in by["Ceremony receipt & identity"]["reason"]


def test_f3_malformed_snapshot_fails_explicitly(tmp_path):
    root, _ = make_root(tmp_path)
    (root / "coordination/evidence/external/asc_epic_fury.json"
     ).write_text("{not json")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["Apple API authentication"]["ok"] is False
    assert "malformed" in by["Apple API authentication"]["reason"]


def test_f4_recompute_predating_ceremony_fails(tmp_path):
    root, _ = make_root(tmp_path, gates_minutes_ago=120.0)
    rows, code = _verifier().run(root)
    assert code == 1
    assert _by(rows)["TESTFLIGHT runtime truth"]["ok"] is False


def test_f5_nonzero_recompute_chain_fails(tmp_path):
    root, _ = make_root(tmp_path, chain_rc=1)
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["Champion-gate recomputation"]["ok"] is False
    assert by["Goal-engine recomputation"]["ok"] is False


def test_f6_satisfied_claim_with_nonaccept_state_is_inconsistent(tmp_path):
    root, _ = make_root(tmp_path, state="IN_REVIEW", req_state="SATISFIED")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["REQ-CP-APP_STORE_CONNECT"]["status"] == "INCONSISTENT"


def test_f7_rejected_reported_verbatim_and_fails(tmp_path):
    root, _ = make_root(tmp_path, state="REJECTED", req_state="FAILED")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["REQ-CP-APP_STORE_CONNECT"]["status"] == "FAILED:REJECTED"


def test_f8_in_review_is_honest_advisory_not_success(tmp_path):
    root, _ = make_root(tmp_path, state="IN_REVIEW", req_state="FAILED",
                        gate_status="UNKNOWN")
    rows, code = _verifier().run(root)
    by = _by(rows)
    req = by["REQ-CP-APP_STORE_CONNECT"]
    assert req["status"].startswith("EXTERNAL-PENDING")
    assert req["ok"] is None
    assert by["APP_STORE_CONNECT runtime truth"]["ok"] is True
    assert code == 0


# ---- R-series: receipt store / replay protection ----------------------------------

def _cdir(root):
    return root / "coordination/evidence/external/asc_ceremonies"


def test_r1_temp_receipt_file_rejected(tmp_path):
    root, _ = make_root(tmp_path)
    (_cdir(root) / ".receipt.abc123.tmp").write_text("partial")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert "temporary/partial" in by["Ceremony receipt store"]["reason"]


def test_r2_partial_receipt_rejected(tmp_path):
    root, cid = make_root(tmp_path)
    (_cdir(root) / f"{_cid(10, 'bbbbbbbbbbbbbbbb')}.json").write_text("{trunc")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert "malformed receipt" in by["Ceremony receipt store"]["reason"]


def test_r3_filename_internal_id_disagreement_rejected(tmp_path):
    root, cid = make_root(tmp_path)
    src = _cdir(root) / f"{cid}.json"
    (_cdir(root) / f"{_cid(10, 'cccccccccccccccc')}.json"
     ).write_text(src.read_text())
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert "disagreement" in by["Ceremony receipt store"]["reason"]


def test_r4_two_receipts_same_started_at_ambiguous(tmp_path):
    root, cid = make_root(tmp_path)
    src = _cdir(root) / f"{cid}.json"
    data = json.loads(src.read_text())
    cid2 = _cid(10, "dddddddddddddddd")
    data["ceremony_id"] = cid2  # same started_at, different id
    (_cdir(root) / f"{cid2}.json").write_text(json.dumps(data))
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert "ambiguous" in by["Ceremony receipt store"]["reason"]


def test_r5_snapshot_digest_mismatch_rejected(tmp_path):
    root, cid = make_root(tmp_path)
    p = root / "coordination/evidence/external/asc_epic_fury.json"
    d = json.loads(p.read_text())
    d["versionString"] = "9.9.9"  # content changed after receipt, same cid
    p.write_text(json.dumps(d, indent=1))
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["Apple snapshot digest binding"]["ok"] is False
    assert "snapshot changed after ceremony" in \
        by["Apple snapshot digest binding"]["reason"]


def test_r6_output_digest_change_without_newer_timestamp_is_tamper(tmp_path):
    root, _ = make_root(tmp_path)
    p = root / "coordination/goal/champion_gates.json"
    d = json.loads(p.read_text())
    d["gates"][0]["status"] = "PASS_TOTALLY_LEGIT"  # same generated_at
    p.write_text(json.dumps(d, indent=1))
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert "tampering suspected" in by["Champion-gate recomputation"]["reason"]


def test_r7_rollback_older_receipt_in_ledger_rejected(tmp_path):
    root, cid_new = make_root(tmp_path)
    # an older ceremony receipt appears, and the ledger's LAST entry is the
    # OLD one — i.e., someone tried to roll authority back after acceptance
    old_cid = _cid(600, "eeeeeeeeeeeeeeee")
    src = json.loads((_cdir(root) / f"{cid_new}.json").read_text())
    src["ceremony_id"] = old_cid
    src["started_at"] = _iso(600)
    (_cdir(root) / f"{old_cid}.json").write_text(json.dumps(src))
    ledger = _cdir(root) / "LEDGER.jsonl"
    ledger.write_text(ledger.read_text() + json.dumps(
        {"ceremony_id": old_cid, "started_at": _iso(600)}) + "\n")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert "superseded/rolled-back" in by["Ceremony receipt store"]["reason"]


def test_r8_superseded_older_receipt_newest_wins(tmp_path):
    root, cid_new = make_root(tmp_path)
    # an older, fully valid receipt exists claiming the same outputs; the
    # ledger honestly ends with the newer ceremony -> newest wins, exit 0
    old_cid = _cid(600, "ffffffffffffffff")
    src = json.loads((_cdir(root) / f"{cid_new}.json").read_text())
    src["ceremony_id"] = old_cid
    src["started_at"] = _iso(600)
    (_cdir(root) / f"{old_cid}.json").write_text(json.dumps(src))
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 0
    assert by["Ceremony receipt store"]["value"] == cid_new


def test_r9_unknown_apple_state_fails_closed(tmp_path):
    root, _ = make_root(tmp_path, state="MYSTERIOUS_NEW_STATE",
                        req_state="FAILED")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["REQ-CP-APP_STORE_CONNECT"]["status"].startswith("FAIL-CLOSED")
    assert "MYSTERIOUS_NEW_STATE" in by["REQ-CP-APP_STORE_CONNECT"]["status"]


def test_r10_gate_script_digest_mismatch_rejected(tmp_path):
    root, _ = make_root(tmp_path)
    (root / "scripts/founder/asc_credentials_gate.py"
     ).write_text("# modified after ceremony\n")
    rows, code = _verifier().run(root)
    by = _by(rows)
    assert code == 1
    assert by["Gate script digest binding"]["ok"] is False
