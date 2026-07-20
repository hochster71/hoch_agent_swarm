"""Completeness and consistency gate for the open claims register.

WHY THIS EXISTS
---------------
Register revision 1 stated the rule "claim IDs must resolve to exactly one claim" and
violated it three lines later: TEL-004 meant domain aggregation in its own body,
"Founder Live hardening" in GOV-001's narrative, and implicitly the voice slice via a
collision warning that was itself factually false. Six items were absent entirely
(HELM-W1-001/003/004/005, REQ-GOV-002, N3_VERIFY).

Root cause: revision 1 was written from memory of a conversation. This file checks the
register against the ROADMAP and GOAL-STATE FILES instead. A register cannot be its own
completeness authority.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "coordination" / "governance" / "open_claims_register.json"
ROADMAP = ROOT / "docs" / "helm" / "roadmap" / "HELM_EXECUTION_SCHEDULE_WAVE_1.md"
GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"
BUILD_TO_GOAL = ROOT / "coordination" / "goal" / "build_to_goal_status.json"

# --- oracle availability: absence is FAILURE, never skip -----------------------
#
# Founder invariant, 2026-07-20: "A required governance oracle being unavailable is a
# verification failure, not an optional skip."
#
# Found when this suite was first run in a clean worktree. The roadmap doc is untracked,
# so it was absent, and test_every_roadmap_package_has_a_claim SKIPPED — disabling the
# one check that guards the revision-1 defect. The run would have printed
# "12 passed, 1 skipped", which reads as success. A check that can silently stop
# checking is worse than no check, because it still earns trust.

REQUIRED_ORACLES = {
    "register": REGISTER,
    "roadmap": ROADMAP,
    "goal_state": GOAL_STATE,
    "build_to_goal": BUILD_TO_GOAL,
}


def _require(name: str) -> Path:
    """Return an oracle path or FAIL. Never skip."""
    p = REQUIRED_ORACLES[name]
    if not p.exists():
        pytest.fail(
            f"required governance oracle '{name}' is absent at {p.relative_to(ROOT)}. "
            "This is a VERIFICATION FAILURE, not a skip: the checks that depend on it "
            "cannot run, so the suite cannot attest to completeness. If this oracle is "
            "untracked, it must be copied into any isolated worktree before verifying."
        )
    return p


def test_all_required_oracles_are_present():
    """Runs first by name order intent: prove the suite can actually verify anything."""
    missing = {n: str(p.relative_to(ROOT)) for n, p in REQUIRED_ORACLES.items()
               if not p.exists()}
    assert not missing, (
        f"required governance oracles absent: {missing}. The suite would otherwise "
        "report passes for checks that never executed."
    )


def _reg() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def _claims() -> list:
    return _reg()["claims"]


def _ids() -> set:
    return {c["claim_id"] for c in _claims()}


# --- identity: the rule the register states about itself ----------------------

def test_claim_ids_are_unique():
    ids = [c["claim_id"] for c in _claims()]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate claim_id(s): {sorted(dupes)}"


def test_each_id_resolves_to_exactly_one_title():
    by_id = {}
    for c in _claims():
        by_id.setdefault(c["claim_id"], set()).add(c["title"])
    ambiguous = {k: v for k, v in by_id.items() if len(v) > 1}
    assert not ambiguous, f"id -> multiple titles: {ambiguous}"


def test_no_claim_id_used_in_narrative_for_a_different_claim():
    """The revision-1 defect: GOV-001's prose said 'TEL-004 (Founder Live hardening)'
    while TEL-004's body was domain aggregation.

    Precision matters here. A first version of this check flagged ANY `ID (text)` and
    fired on `TEL-001 (no filesystem-time reintroduced)` — a reason, not a title gloss.
    A check that fires on correct content gets ignored, so it now flags only a gloss
    carrying DISTINCTIVE title words belonging to some other claim.
    """
    claims = _claims()
    STOP = {"the", "and", "a", "of", "to", "for", "in", "is", "not", "no", "from",
            "with", "was", "or", "be", "by", "on", "as", "at", "it", "that"}

    def tokens(title: str) -> set:
        return {w for w in re.findall(r"[a-z]{4,}", title.lower()) if w not in STOP}

    titles = {c["claim_id"]: c["title"] for c in claims}
    toks = {cid: tokens(t) for cid, t in titles.items()}
    # Distinctive = appears in exactly one claim's title.
    counts = {}
    for tset in toks.values():
        for w in tset:
            counts[w] = counts.get(w, 0) + 1
    distinctive = {cid: {w for w in tset if counts[w] == 1} for cid, tset in toks.items()}

    problems = []
    for c in claims:
        blob = json.dumps(c)
        for other_id in titles:
            if other_id == c["claim_id"]:
                continue
            for m in re.finditer(re.escape(other_id) + r"\s*\(([^)]{3,60})\)", blob):
                gloss = set(re.findall(r"[a-z]{4,}", m.group(1).lower()))
                for wrong_id, dwords in distinctive.items():
                    if wrong_id in (other_id, c["claim_id"]):
                        continue
                    if len(gloss & dwords) >= 2:
                        problems.append(
                            f"{c['claim_id']} cites {other_id} with gloss '{m.group(1)}' "
                            f"which describes {wrong_id} ('{titles[wrong_id]}')")
    assert not problems, "conflicting cross-citations:\n  " + "\n  ".join(problems)


def test_collision_warning_makes_no_false_rename_claim():
    reg = _reg()
    assert "ID_COLLISION_WARNING" not in reg, (
        "revision 1's ID_COLLISION_WARNING asserted a rename that did not happen; "
        "it must be replaced by w1_002d_disposition, which states the true mapping"
    )
    disp = reg.get("w1_002d_disposition")
    assert disp, "w1_002d_disposition missing — the collision must remain documented"
    mapped = {e["now"] for e in disp["resolution_option_A"]}
    assert {"TEL-004", "TEL-005", "TEL-008"} <= mapped, (
        f"disposition must map all three contested meanings; got {mapped}"
    )


def test_gov_001_does_not_cite_tel_004_for_founder_live():
    for c in _claims():
        if c["claim_id"] != "GOV-001":
            continue
        blob = json.dumps(c)
        assert "TEL-004" not in blob, "GOV-001 must cite PKG-W1-003, not TEL-004"
        assert "PKG-W1-003" in blob, "GOV-001 must name the Founder Live package explicitly"


# --- completeness: checked against FILES, not memory --------------------------

def test_every_roadmap_package_has_a_claim():
    roadmap = _require("roadmap")
    packages = re.findall(r"^### (HELM-W1-\d+) — (.+)$", roadmap.read_text(encoding="utf-8"), re.M)
    assert packages, "no roadmap packages parsed — check the heading format"
    ids = _ids()
    blob = json.dumps(_reg())
    missing = []
    for pkg_id, title in packages:
        num = pkg_id.split("-")[-1]
        decomposed = pkg_id in json.dumps(_reg().get("w1_002_decomposition", {}))
        covered = (f"PKG-W1-{num}" in ids) or decomposed
        if not covered:
            missing.append(f"{pkg_id} — {title}")
    assert not missing, (
        "roadmap packages with neither a PKG claim nor a recorded decomposition "
        "(the revision-1 failure):\n  " + "\n  ".join(missing)
    )


def test_critical_path_blocker_has_a_claim():
    goal_state = _require("goal_state")
    blocker = (json.loads(goal_state.read_text(encoding="utf-8"))
               .get("metrics", {}).get("current_critical_path_blocker"))
    # Distinguish schema drift from a genuine null. A MISSING key means the field was
    # renamed or removed and this check silently stopped checking — that is failure. A
    # PRESENT key holding null means there is honestly no blocker — that is a skip.
    metrics = json.loads(goal_state.read_text(encoding="utf-8")).get("metrics", {})
    assert "current_critical_path_blocker" in metrics, (
        "goal_state.metrics has no 'current_critical_path_blocker' key — the field was "
        "renamed or removed, so this check would silently stop verifying. Schema drift "
        "is a verification failure, not a skip."
    )
    if not blocker:
        pytest.skip("current_critical_path_blocker present but null — no blocker to claim")
    assert blocker in _ids(), (
        f"goal_state names '{blocker}' as the critical-path blocker; it has no claim"
    )


def test_non_done_build_to_goal_nodes_have_claims():
    build_to_goal = _require("build_to_goal")
    nodes = json.loads(build_to_goal.read_text(encoding="utf-8")).get("nodes", {})
    open_nodes = {k for k, v in nodes.items() if v != "DONE"}
    missing = open_nodes - _ids()
    assert not missing, f"build_to_goal nodes not DONE and not claimed: {sorted(missing)}"


def test_founder_gated_pending_actions_are_visible():
    """Not in the Option A required set — surfaced by reading goal_state.

    Founder-gated does not mean invisible. If these are rejected from the register,
    delete this test with the rejection recorded, do not silently drop the claims.
    """
    goal_state = _require("goal_state")
    pending = (json.loads(goal_state.read_text(encoding="utf-8"))
               .get("metrics", {}).get("founder_only_actions_pending") or [])
    missing = set(pending) - _ids()
    assert not missing, (
        f"goal_state lists founder-gated pending actions with no claim: {sorted(missing)}"
    )


# --- honesty of the record ----------------------------------------------------

def test_no_status_outside_the_declared_vocabulary():
    vocab = set(_reg()["rules"]["status_vocabulary"])
    bad = {c["claim_id"]: c["status"] for c in _claims() if c["status"] not in vocab}
    assert not bad, f"status outside declared vocabulary: {bad}"


def test_statuses_above_open_carry_evidence():
    for c in _claims():
        if c["status"] == "OPEN":
            continue
        ev = c.get("evidence") or {}
        assert ev, f"{c['claim_id']} claims {c['status']} with no evidence block"
        blob = json.dumps(ev)
        has_sha = bool(re.search(r"\b[0-9a-f]{40}\b", blob))
        has_tests = "test" in blob.lower() or "passing" in blob.lower()
        assert has_sha or has_tests, (
            f"{c['claim_id']} status {c['status']} cites neither a full SHA nor a test result"
        )


def test_integrated_claims_use_full_shas():
    for c in _claims():
        for m in re.finditer(r'"commit":\s*"([0-9a-fA-F]+)"', json.dumps(c)):
            assert len(m.group(1)) == 40, (
                f"{c['claim_id']} cites an abbreviated commit — a prefix can resolve to a "
                "different object (see the 5877ffa1 collision)"
            )


def test_revision_1_defect_is_recorded_not_erased():
    """A governance record that quietly fixes its own failure teaches nothing."""
    rec = _reg().get("revision_1_defect_record")
    assert rec, "revision 1's failure must remain in the record, not be erased"
    assert rec.get("false_statement_retracted"), "the false collision warning must be retracted explicitly"


# --- requirements[] coverage (added rev 3) ------------------------------------
#
# Cold review, 2026-07-20: revision 2 omitted REQ-GOV-003 and REQ-ES-002 — both blocking,
# agent-owned, on the goal_state critical path. This suite contained ZERO references to
# `requirements` and checked only current_critical_path_blocker (one scalar) and
# founder_only_actions_pending (one list). 25 requirements and the entire critical_path
# array were unchecked while the suite was described as file-backed completeness.

def _goal_metrics_and_reqs():
    d = json.loads(_require("goal_state").read_text(encoding="utf-8"))
    return d.get("metrics", {}) or {}, d.get("requirements", []) or [], d.get("critical_path", []) or []


def test_every_blocking_non_satisfied_requirement_has_a_claim():
    """The revision-2 omission, generalised: enumerate requirements[] rather than one scalar."""
    _, reqs, _ = _goal_metrics_and_reqs()
    assert reqs, "goal_state.requirements is empty or absent — cannot verify completeness"
    ids = _ids()
    missing = [
        f"{r.get('id')} (state={r.get('state')}, owner={r.get('owner')})"
        for r in reqs
        if isinstance(r, dict) and r.get("state") not in ("SATISFIED", None)
        and r.get("blocking") and r.get("id") not in ids
    ]
    assert not missing, (
        "blocking, non-satisfied requirements with no claim:\n  " + "\n  ".join(missing)
    )


def test_every_critical_path_item_has_a_claim():
    """The critical path is the ordered list the goal computation depends on."""
    _, _, cp = _goal_metrics_and_reqs()
    assert cp, "goal_state.critical_path is empty or absent"
    ids = _ids()
    cp_ids = [c.get("id") if isinstance(c, dict) else c for c in cp]
    missing = [i for i in cp_ids if i and i not in ids]
    assert not missing, f"critical_path items with no claim: {missing}"


def test_delivery_vocabulary_can_express_delivered_but_not_to_target():
    """TEL-001 was recorded INTEGRATED while reachable only from a non-target remote.

    The vocabulary must be able to say 'delivered somewhere, not to the declared target',
    or that distinction gets flattened again.
    """
    reg = _reg()
    vocab = set(reg["rules"]["status_vocabulary"])
    assert {"REMOTE_DELIVERED", "TARGET_INTEGRATED"} <= vocab, (
        f"vocabulary cannot distinguish delivery from target integration; got {sorted(vocab)}"
    )
    assert "INTEGRATED" not in vocab, (
        "bare INTEGRATED is ambiguous between REMOTE_DELIVERED and TARGET_INTEGRATED"
    )


def test_target_branch_is_explicitly_bound():
    b = _reg().get("branch_bindings")
    assert b and b.get("wave_1_target"), (
        "no declared Wave 1 target branch — TARGET_INTEGRATED is unverifiable without it"
    )


def test_target_integrated_claims_name_the_target_branch():
    target = _reg().get("branch_bindings", {}).get("wave_1_target")
    for c in _claims():
        if c.get("status") != "TARGET_INTEGRATED":
            continue
        assert target and target in json.dumps(c.get("evidence") or {}), (
            f"{c['claim_id']} claims TARGET_INTEGRATED without citing reachability from {target}"
        )


def test_oracle_identity_is_dual_hashed_and_flags_dirty():
    """Founder decision 2026-07-20: dual-hashed oracle mode."""
    oi = _reg().get("oracle_identity")
    # Mode evolved DUAL_HASHED -> QUIESCED_SNAPSHOT by founder decision. Both retain dual
    # hashes; the newer mode additionally requires the writer be quiesced before pinning.
    assert oi and oi.get("mode") in ("DUAL_HASHED", "QUIESCED_SNAPSHOT", "SNAPSHOT_COPY"), (
        f"unrecognised oracle mode: {oi.get('mode') if oi else None}"
    )
    for o in oi.get("oracles", []):
        assert "working_tree_sha256" in o and "committed_blob_sha256" in o, (
            f"{o.get('path')} missing a dual-hash field"
        )
        assert "dirty" in o, f"{o.get('path')} does not declare dirty state"


def test_recorded_oracle_hashes_still_match_disk():
    """A rewrite of a live oracle must invalidate the evidence automatically."""
    import hashlib
    drifted = []
    for o in _reg().get("oracle_identity", {}).get("oracles", []):
        p = ROOT / o["path"]
        if not p.exists() or o["path"].endswith("open_claims_register.json"):
            continue  # self-reference: a later revision supersedes its own recorded hash
        if o.get("live"):
            continue  # exempt ONLY if declared live; see test_live_oracles_are_declared_not_implicit
        actual = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual != o.get("working_tree_sha256"):
            drifted.append(f"{o['path']}\n      recorded {o.get('working_tree_sha256')}\n"
                           f"      on disk  {actual}")
    assert not drifted, (
        "oracle bytes changed since the identity record was written — the verification "
        "evidence is stale and must be re-established:\n    " + "\n    ".join(drifted)
    )


def test_live_oracle_policy_is_snapshot_copy():
    """Founder decision 2026-07-20: SNAPSHOT_COPY, superseding QUIESCED_SNAPSHOT.

    The earlier form of this test required the question stay UNRESOLVED so it could not be
    closed by quietly relaxing a check. It was closed the legitimate way — twice, as the
    founder refined quiesce -> snapshot-copy — so the assertion now pins the DECISION and
    keeps the superseded options on record.
    """
    oi = _reg().get("oracle_identity", {})
    t = oi.get("live_file_tension")
    assert t, "live-oracle policy must be recorded"
    assert t.get("status") == "RESOLVED", f"status is {t.get('status')}"
    assert t.get("decision") == "SNAPSHOT_COPY", f"decision is {t.get('decision')}"
    assert oi.get("mode") == "SNAPSHOT_COPY", f"oracle mode is {oi.get('mode')}"
    assert t.get("superseded_options"), "rejected options must remain on record"
    assert t.get("atomicity_protocol"), "a plain copy can race the writer; protocol required"
    # Snapshot-copy explicitly does NOT require stopping the writer. If these flip, the
    # register has silently drifted back to the heavier mode the founder did not select.
    assert t.get("writer_quiescence_required") is False, (
        "SNAPSHOT_COPY does not require quiescing the writer; that is QUIESCED_SNAPSHOT"
    )
    assert t.get("post_capture_source_drift_allowed") is True, (
        "under SNAPSHOT_COPY the snapshot is the oracle; later source drift is expected"
    )


def test_stability_gate_is_not_labelled_as_the_promotion_gate():
    """The gate verifies quiescence. A later operator must not mistake it for mandatory."""
    g = ROOT / "scripts" / "oracle_stability_gate.sh"
    if not g.exists():
        pytest.fail(f"stability gate absent at {g.relative_to(ROOT)}")
    head = g.read_text(encoding="utf-8")[:1600]
    assert "QUIESCENCE VERIFICATION" in head, "gate must declare its purpose in its header"
    assert "NOT:     SNAPSHOT COHERENCE" in head, (
        "gate must explicitly disclaim being the snapshot-coherence gate"
    )


def test_snapshot_capture_proves_a_coherent_read():
    """source_sha256_at_capture MUST equal snapshot_sha256, or the read was torn.

    post-capture source drift is EXPECTED for a live oracle and must be recorded rather
    than treated as failure — the snapshot is the oracle, the live source is not.
    """
    snaps = _reg().get("oracle_identity", {}).get("snapshots")
    assert snaps, "no snapshot records — live oracles have no pinned promotion oracle"
    for s in snaps:
        assert s["source_sha256_at_capture"] == s["snapshot_sha256"], (
            f"{s['source_path']}: torn read — source and snapshot hashes differ"
        )
        assert "post_capture_drift_observed" in s, (
            f"{s['source_path']}: post-capture drift not recorded"
        )
        assert s.get("capture_method"), f"{s['source_path']}: no capture method declared"


def test_snapshot_files_exist_and_match_recorded_hashes():
    """The pinned bytes must actually be on disk and match — otherwise the record is a claim."""
    import hashlib
    for s in _reg().get("oracle_identity", {}).get("snapshots", []):
        sp = ROOT / s["snapshot_path"]
        assert sp.exists(), f"snapshot missing on disk: {s['snapshot_path']}"
        actual = hashlib.sha256(sp.read_bytes()).hexdigest()
        assert actual == s["snapshot_sha256"], (
            f"{s['snapshot_path']} bytes changed since capture\n"
            f"  recorded {s['snapshot_sha256']}\n  on disk  {actual}\n"
            "A snapshot is immutable by definition; if it changed, it is not a snapshot."
        )


def test_verification_classes_are_not_mixed():
    """Promotion pins bytes; runtime health uses a freshness window. Conflating them
    reintroduces the ambiguity the quiesced-snapshot decision removes."""
    vc = _reg().get("oracle_identity", {}).get("verification_classes", {})
    assert "PROMOTION_VERIFICATION" in vc and "RUNTIME_HEALTH_VERIFICATION" in vc, (
        "both verification classes must be defined distinctly"
    )
    assert "must_not" in vc["RUNTIME_HEALTH_VERIFICATION"], (
        "runtime health must explicitly disclaim byte-identity"
    )


def test_six_state_evidence_machine_is_intact():
    """Founder, 2026-07-20: AUDITED / LOCAL_VERIFIED / REMOTE_DELIVERED /
    TARGET_INTEGRATED / CI_VERIFIED / ROADMAP_COMPLETE. No state implies the next."""
    vocab = set(_reg()["rules"]["status_vocabulary"])
    required = {"AUDITED", "LOCAL_VERIFIED", "REMOTE_DELIVERED",
                "TARGET_INTEGRATED", "CI_VERIFIED", "ROADMAP_COMPLETE"}
    missing = required - vocab
    assert not missing, f"evidence states missing from vocabulary: {sorted(missing)}"
    assert "INTEGRATED" not in vocab, "bare INTEGRATED is ambiguous and must not return"


def test_stale_requirement_claims_are_not_described_as_missing():
    """Precision correction, rev 4: REQ-GOV-003 and REQ-ES-002 are PRESENT in goal_state
    and STALE. Only their register claims were absent. Conflating those is a real
    misreading — one is a requirements defect, the other a register-coverage defect."""
    for c in _claims():
        if c["claim_id"] not in ("REQ-GOV-003", "REQ-ES-002"):
            continue
        ev = json.dumps(c.get("evidence") or {})
        assert "finding_precision" in ev, f"{c['claim_id']} lacks the precision note"
        assert "not a" in ev and "missing requirement" in ev, (
            f"{c['claim_id']} must explicitly deny the 'missing requirement' reading"
        )
