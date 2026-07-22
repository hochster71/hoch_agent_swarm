#!/usr/bin/env python3
r"""
HELM Transition History & Hash-Chain Verifier (v1.0.0 Normative) — Milestone R1.2
===================================================================================
Audits tamper-evident lifecycle transition history chains in `conformance_report.json`.
Enforces:
  1. Genesis hash initialization (GENESIS_HASH_000000...).
  2. Transition hash linkage continuity across transitions.
  3. Domain-tagged SHA-256 calculation ("HELM-CONFORMANCE-TRANSITION-V1\n").
  4. RFC 8785 canonical serialization of transition record payloads.
  5. State machine transition rules (GENERATED -> VERIFIED -> PUBLISHED -> [SUPERSEDED | REVOKED]).
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.helm.canonical_json import compute_transition_hash, GENESIS_HASH

VALID_STATE_TRANSITIONS = {
    ("GENERATED", "VERIFIED"),
    ("VERIFIED", "PUBLISHED"),
    ("PUBLISHED", "SUPERSEDED"),
    ("PUBLISHED", "REVOKED"),
}


def verify_transition_history(report_path: str) -> bool:
    p = Path(report_path)
    if not p.exists():
        print(f"[ERROR] Conformance report file not found: {report_path}", file=sys.stderr)
        return False

    with open(p, "r", encoding="utf-8") as f:
        try:
            report_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to parse JSON report: {e}", file=sys.stderr)
            return False

    lifecycle = report_data.get("lifecycle", {})
    current_state = lifecycle.get("state")
    history = lifecycle.get("transition_history", [])

    if not history:
        print("[ERROR] Transition history is empty", file=sys.stderr)
        return False

    expected_prev_hash = GENESIS_HASH
    errors = []

    for i, t in enumerate(history):
        t_id = t.get("transition_id", f"TRANS-IDX-{i}")
        prev_hash = t.get("previous_transition_hash")
        t_hash = t.get("transition_hash")
        from_state = t.get("from")
        to_state = t.get("to")

        # 1. State Machine Validity
        if (from_state, to_state) not in VALID_STATE_TRANSITIONS:
            errors.append(f"[{t_id}] Invalid state transition: {from_state} -> {to_state}")

        # 2. Previous Hash Linkage Check
        if prev_hash != expected_prev_hash:
            errors.append(
                f"[{t_id}] Hash chain link broken!\n"
                f"  Expected previous_hash: {expected_prev_hash}\n"
                f"  Stored previous_hash:   {prev_hash}"
            )

        # 3. Domain-Tagged Transition Hash Recomputation
        recomputed_hash = compute_transition_hash(t, prev_hash)
        if recomputed_hash != t_hash:
            errors.append(
                f"[{t_id}] Transition hash mismatch!\n"
                f"  Stored:     {t_hash}\n"
                f"  Recomputed: {recomputed_hash}"
            )

        expected_prev_hash = t_hash

    # Final Lifecycle State Alignment
    last_transition_to = history[-1].get("to")
    if current_state != last_transition_to:
        errors.append(
            f"Lifecycle current state ('{current_state}') does not match final transition target ('{last_transition_to}')"
        )

    if errors:
        print("======================================================================", file=sys.stderr)
        print("HELM TRANSITION HISTORY VERIFICATION: FAILED", file=sys.stderr)
        print("======================================================================", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return False

    print("======================================================================")
    print(f"HELM TRANSITION HISTORY VERIFICATION: PASS ({len(history)} transitions verified)")
    print(f"  [✓] Genesis link: {GENESIS_HASH[:16]}...")
    print(f"  [✓] State machine state: {history[0]['from']} -> ... -> {current_state}")
    print(f"  [✓] Domain tag: 'HELM-CONFORMANCE-TRANSITION-V1\\n'")
    print(f"  [✓] Hash chain integrity unbroken")
    print("======================================================================")
    return True


if __name__ == "__main__":
    target_report = sys.argv[1] if len(sys.argv) > 1 else "docs/helm/conformance_report.json"
    success = verify_transition_history(target_report)
    sys.exit(0 if success else 1)
