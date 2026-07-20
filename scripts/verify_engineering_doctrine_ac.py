#!/usr/bin/env python3
"""verify_engineering_doctrine_ac.py — method-bound proof of EDR-0006 AC-1..AC-6 (v2).

HELM-GOV | extends: scripts/goal validators + Evidence Doctrine | doctrine: Governance-before-Capability
         | edr: EDR-0006 (Acceptance criteria) | why: a DETERMINISTIC, NON-VACUOUS harness an
         | independent Auditor runs to confirm the six acceptance criteria. v2 addresses the Auditor's
         | REJECT (GROK_AC_VERDICT_20260718T164430Z): AC-1 now requires LIVE carry-rate (no over-claim),
         | AC-2 binds state-advancement methodology, AC-4 uses a pos/neg control (not a stub), AC-5
         | inventories ledgers + proves gate purity, AC-6 binds the constitution path + baseline hash.

Every check states its METHOD and carries a control where applicable. A check that errors, or that
cannot bind its evidence, is a FAIL or UNKNOWN — never a silent PASS. No Fake Green.

Exit 0 = all AC PASS; non-zero = at least one AC not satisfied (fail-closed).
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CONSTITUTION = "docs/helm/HELM_CONSTITUTION_v1.0.md"
# The ratified HELM Constitution v1.0 blob id (git hash-object of the frozen baseline). AC-6 compares
# the working tree to THIS pinned digest — an independent baseline, not "whatever HEAD happens to be"
# (Auditor F-A7/F-B6). If HEAD is ever rewritten, this pin still catches it.
CONSTITUTION_RATIFIED_BLOB = "4b99e881045ac92bb8d6a46477af98e8fa0f6b19"
GATE_MODULES = ["backend/helm_runtime/governance_manifest.py", "backend/helm_runtime/governance_engine.py"]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, text=True).stdout.strip()


def _complete_record() -> dict:
    return {
        "authorized": {"authority": "EDR-0006", "decision_id": "AC-CHECK", "gate": "govern_decision"},
        "explanation": "acceptance-criteria verification decision",
        "trace": {"correlation_id": "ac1", "input_digests": ["sha256:abc"]},
        "proven": {"proof_command": "verify_engineering_doctrine_ac", "exit_code": 0, "evidence_hash": "sha256:def"},
        "audit": {"record_hash": "h1", "prev_hash": None},
        "reproducibility": {"tested_commit": _git("rev-parse", "HEAD"), "environment": "verifier"},
        "evidence_class": "OBSERVED",
    }


def ac1_fail_closed_and_live_carry() -> tuple[str, dict]:
    """AC-1 has TWO parts, BOTH required (this is the over-claim fix):
      A) unit fail-closed: removing ANY property, or ASSERTED evidence, or no record -> not GOVERNED.
      B) live carry-rate: of NEW (post-adoption) material decisions, 100% carry a valid Proof Record.
    Returns 'PASS' only if A holds AND B has material>0 with carry_rate==1.0 and governed_rate==1.0.
    If B has no NEW decisions yet -> 'UNKNOWN' (honest — not PASS). If B<1.0 -> 'FAIL'."""
    from backend.helm_runtime.extensions.constitutional_gate import govern_decision
    from backend.security.helm_conmon import governance_coverage

    # A) unit fail-closed — bind to may_advance AND state (not free text)
    negatives = {}
    a_ok = govern_decision(_complete_record()).may_advance is True
    for prop in ("authorized", "explanation", "trace", "proven", "audit", "reproducibility"):
        rec = copy.deepcopy(_complete_record()); del rec[prop]
        r = govern_decision(rec)
        ok = (r.may_advance is False and r.governance_state != "GOVERNED")
        negatives[prop] = {"may_advance": r.may_advance, "state": r.governance_state, "control_holds": ok}
        a_ok = a_ok and ok
    for label, mut in (("evidence_class=ASSERTED", {"evidence_class": "ASSERTED"}), ("no_record", None)):
        rec = None if mut is None else {**_complete_record(), **mut}
        r = govern_decision(rec)
        ok = (r.may_advance is False and r.governance_state != "GOVERNED")
        negatives[label] = {"may_advance": r.may_advance, "state": r.governance_state, "control_holds": ok}
        a_ok = a_ok and ok

    # B) live carry-rate over NEW decisions
    cov = governance_coverage()
    material = cov.get("material_decisions", cov.get("material", 0))
    carry = cov.get("carry_rate")
    governed = cov.get("governed_rate")
    if not a_ok:
        state = "FAIL"
    elif material == 0:
        state = "UNKNOWN"   # no NEW decisions yet — honest, not a pass
    elif carry == 1.0 and governed == 1.0:
        state = "PASS"
    else:
        state = "FAIL"
    return state, {"unit_fail_closed": a_ok, "negative_controls": negatives,
                   "live_coverage": cov, "note": "AC-1 PASS requires unit fail-closed AND live carry_rate==1.0"}


def ac2_single_state_authority() -> tuple[str, dict]:
    """AC-2 (method-bound): prove ONE authority advances material state, not just one function name.
    Method: (a) exactly one module defines govern_decision; (b) the GOVERNED verdict (may_advance) is
    produced in exactly one place; (c) enumerate every may_advance_state() call site so the Auditor can
    see state-advancement routes through the delegating gate."""
    # --untracked: the gate primitive (governance_manifest.py) is a new file not yet committed; a
    # tracked-only search would miss it and give a false negative. Search tracked + untracked (not ignored).
    defs = [f for f in _git("grep", "--untracked", "-l", "def govern_decision", "--", "backend").splitlines() if f]
    # the may_advance verdict is computed in exactly one place (fixed-string, robust to regex metachars)
    gov_assign = [l for l in _git("grep", "--untracked", "-nF", "may = state == _gm.GOVERNED", "--", "backend").splitlines() if l]
    # GOVERNED is emitted as an advancing verdict from exactly one classifier line
    governed_literal = [l for l in _git("grep", "--untracked", "-nF", "return GOVERNED, []", "--", "backend").splitlines() if l]
    advance_callers = [l for l in _git("grep", "--untracked", "-nF", "may_advance_state(", "--", "backend").splitlines() if l]
    one_gate = (len([f for f in defs if f.endswith("governance_engine.py")]) == 1 and
                all(f.endswith("governance_engine.py") for f in defs))
    one_verdict = len(gov_assign) == 1  # may_advance True computed in exactly one place
    one_classifier = len(governed_literal) == 1  # GOVERNED verdict emitted from exactly one classifier line
    # F-B3: whole-repo scan (not just backend) for any parallel GOVERNED classifier. Exclude tooling
    # that references the string as a search literal (this harness, the fire script, the tests).
    _TOOLING = ("verify_engineering_doctrine_ac.py", "fire_doctrine_auditor.py", "test_engineering_doctrine.py")
    repo_classifier = [l for l in _git("grep", "--untracked", "-nF", "return GOVERNED, []", "--", "*.py").splitlines()
                       if l and not any(t in l for t in _TOOLING)]
    repo_single_classifier = (len(repo_classifier) == 1 and "governance_manifest.py" in repo_classifier[0])
    passed = one_gate and one_verdict and one_classifier and repo_single_classifier
    return ("PASS" if passed else "FAIL"), {
        "gate_definitions": defs, "may_advance_verdict_sites": gov_assign,
        "governed_classifier_sites": governed_literal, "state_advance_callers": advance_callers,
        "repo_wide_governed_classifier_sites": repo_classifier, "repo_single_classifier": repo_single_classifier,
        "method": "one gate def + one verdict site + one classifier line (backend) + WHOLE-REPO scan confirms no parallel classifier"}


def ac3_legacy_gate_enforced() -> tuple[str, dict]:
    """AC-3 (now gate-enforced): a LEGACY-sourced complete record is refused GOVERNED without a
    migration record — even via govern_decision(legacy=False). Positive + negative control."""
    from backend.helm_runtime import governance_manifest as gm
    from backend.helm_runtime.extensions.constitutional_gate import govern_decision

    legacy_no_mig = copy.deepcopy(_complete_record()); legacy_no_mig["source"] = gm.SOURCE_LEGACY
    r1 = govern_decision(legacy_no_mig)  # legacy=False on purpose (mis-flag path)
    legacy_mig = copy.deepcopy(legacy_no_mig); legacy_mig["migration"] = {"migration_ref": "MIG-1", "migrated_by": "builder"}
    r2 = govern_decision(legacy_mig)
    classifier_ok = (gm.classify_legacy(_complete_record())[0] == "VERIFIED" != "GOVERNED")
    passed = (r1.governance_state == "NEEDS_MIGRATION" and not r1.may_advance
              and r2.governance_state == "GOVERNED" and classifier_ok)
    return ("PASS" if passed else "FAIL"), {
        "legacy_no_migration": r1.governance_state, "legacy_with_migration": r2.governance_state,
        "classifier_verified_not_governed": classifier_ok}


def ac4_conmon_live_rederivation() -> tuple[str, dict]:
    """AC-4 (pos/neg control, not a stub): prove ConMon RE-DERIVES coverage from the corpus by showing
    the number CHANGES with the corpus. Write a governed event -> coverage sees it; write an ungoverned
    one -> carry_rate drops. A static stub could not move."""
    from backend.helm_runtime.event_bus import publish_event
    from backend.security import helm_conmon as hc

    tmp = Path(tempfile.mkdtemp()) / "helm_events.jsonl"
    orig_ledger, orig_cut = hc.EVENTS_LEDGER, hc._adoption_cutoff
    try:
        hc.EVENTS_LEDGER = tmp
        hc._adoption_cutoff = lambda: "2026-07-18T00:00:00Z"
        rec = {**_complete_record(), "governance_state": "GOVERNED"}
        from backend.helm_runtime.extensions.constitutional_gate import publish_governed_event as _pge
        _pge(type="COUNCIL_SOLVED", producer="council_router", mission_id="COUNCIL", proof_record=rec, path=tmp)
        after_governed = hc.governance_coverage()
        # now add an ungoverned council decision -> carry_rate must fall below 1.0 (re-derivation proof)
        with open(tmp, "a") as fh:
            fh.write('{"producer":"council_router","type":"COUNCIL_SOLVED","timestamp":"2026-07-18T18:00:00Z","proof_record":null}\n')
        after_ungoverned = hc.governance_coverage()
    finally:
        hc.EVENTS_LEDGER, hc._adoption_cutoff = orig_ledger, orig_cut
    moved = (after_governed.get("carry_rate") == 1.0 and after_ungoverned.get("carry_rate") == 0.5)
    return ("PASS" if moved else "FAIL"), {
        "after_one_governed": after_governed, "after_adding_ungoverned": after_ungoverned,
        "re_derivation_proven": moved, "method": "coverage number moves with the corpus -> not a static stub"}


def ac5_ledger_inventory_and_purity() -> tuple[str, dict]:
    """AC-5 (HISTORICAL append-only, Auditor F-A6/F-B5): a git-diff cannot prove history — a committed
    rewrite leaves HEAD clean. Hash-chain LINKAGE can: no record may be deleted/reordered without a
    dangling prev-pointer. Verify every governed ledger's chain + content-recompute where we own the
    scheme + gate purity (gate cannot write ledgers)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from verify_ledger_chains import run as _chains

    chains = _chains()
    write_tokens = []
    for m in GATE_MODULES:
        src = (ROOT / m).read_text()
        hits = [l.strip() for l in src.splitlines() if "open(" in l or ".write(" in l or "os.replace" in l]
        if hits:
            write_tokens.append({"module": m, "write_lines": hits})
    passed = chains["all_chains_intact"] and len(write_tokens) == 0
    return ("PASS" if passed else "FAIL"), {
        "hash_chain_verification": chains, "gate_modules_pure_no_writes": len(write_tokens) == 0,
        "gate_write_sites": write_tokens,
        "method": "hash-chain linkage (delete/reorder breaks prev-pointer) + content recompute + gate purity"}


def ac6_constitution_frozen_bound() -> tuple[str, dict]:
    """AC-6 (path + baseline + content-hash bound): the constitution's working-tree content hash equals
    its HEAD blob hash — proving byte-identity against a named baseline, not a scopeless empty diff."""
    import hashlib

    p = ROOT / CONSTITUTION
    exists = p.exists()
    wt_hash = "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest() if exists else None
    head_blob = _git("rev-parse", f"HEAD:{CONSTITUTION}")           # git blob id at HEAD
    wt_blob = _git("hash-object", CONSTITUTION)                     # git blob id of working tree
    # PIN: working tree must equal the RATIFIED baseline digest (not merely HEAD). Also confirm HEAD
    # still equals the pin — a rewritten HEAD would diverge from the pin and fail here.
    matches_pin = wt_blob == CONSTITUTION_RATIFIED_BLOB
    head_matches_pin = head_blob == CONSTITUTION_RATIFIED_BLOB
    passed = exists and matches_pin and head_matches_pin
    return ("PASS" if passed else "FAIL"), {
        "path": CONSTITUTION, "exists": exists, "working_tree_sha256": wt_hash,
        "ratified_baseline_blob": CONSTITUTION_RATIFIED_BLOB,
        "working_tree_blob_id": wt_blob, "head_blob_id": head_blob,
        "working_tree_matches_ratified_pin": matches_pin, "head_matches_ratified_pin": head_matches_pin,
        "method": "working-tree blob == PINNED ratified v1.0 baseline digest (independent of HEAD)"}


CHECKS = [
    ("AC-1", "NEW decisions fail-closed AND live carry_rate==1.0", ac1_fail_closed_and_live_carry),
    ("AC-2", "single state authority (method-bound)", ac2_single_state_authority),
    ("AC-3", "legacy gate-enforced (no promotion w/o migration)", ac3_legacy_gate_enforced),
    ("AC-4", "ConMon live re-derivation (pos/neg control)", ac4_conmon_live_rederivation),
    ("AC-5", "ledger inventory + append-only + gate purity", ac5_ledger_inventory_and_purity),
    ("AC-6", "Constitution frozen (blob-id bound)", ac6_constitution_frozen_bound),
]


def main() -> int:
    results = []
    for ac_id, title, fn in CHECKS:
        try:
            state, evidence = fn()
        except Exception as e:
            state, evidence = "FAIL", {"error": repr(e)}
        results.append({"id": ac_id, "title": title, "state": state, "evidence": evidence})

    all_pass = all(r["state"] == "PASS" for r in results)
    any_fail = any(r["state"] == "FAIL" for r in results)
    verdict = {
        "schema": "HELM_DOCTRINE_AC_VERDICT_v2",
        "edr": "EDR-0006",
        "assessed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tested_commit": _git("rev-parse", "HEAD"),
        "builder_run": True,
        "auditor_confirmation": "PENDING — independent Auditor (Grok) must run + adversarially confirm",
        "all_acceptance_criteria_pass": all_pass,
        "any_fail": any_fail,
        "results": results,
        "doctrine": "PASS requires bound evidence + controls; UNKNOWN is not PASS; an errored check is FAIL",
    }
    out_dir = ROOT / "docs" / "evidence" / "doctrine"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase1_ac_verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")

    for r in results:
        print(f"  [{r['state']:7s}] {r['id']}  {r['title']}")
    print(f"\n  ALL PASS: {all_pass}  |  ANY FAIL: {any_fail}")
    print("  auditor_confirmation: PENDING (independent verification required)")
    # exit 0 only if all pass; UNKNOWN or FAIL -> non-zero (fail-closed)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
