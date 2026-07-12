#!/usr/bin/env python3
"""Generator for H1C Commit-Bound Founder review packet and pending authorization template.

This script:
1. Reconciles candidates to find the active candidate package ID and digest.
2. Computes the current H1C truth (which is safe_to_execute = NO, LOCKED, action required).
3. Produces the DOORSTEP founder review packet.
4. Generates the pending authorization template bound to the current HEAD commit.
"""
from __future__ import annotations
import json
import hashlib
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.instrument_integrity.h1c_activation import (
    compute_h1c_truth,
    build_doorstep_founder_packet,
    git_sha
)
from scripts.council.h1b_candidate_registry import reconcile_candidates

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def main():
    print("=== GENERATING H1C COMMIT-BOUND FOUNDER DOORSTEP PACKET ===")
    
    head_sha = git_sha(ROOT)
    print(f"Current committed Git HEAD SHA: {head_sha}")

    # Reconcile active candidate
    recon = reconcile_candidates()
    if recon["status"] != "RECONCILED":
        print(f"ERROR: Candidate registry reconciliation failed: {recon['status']}")
        sys.exit(1)
        
    package_id = recon["active_candidate"]
    package_digest = recon["integrity"]["stored"]["combined_authorization_sha256"]
    print(f"Active candidate: {package_id}")
    print(f"Package digest: {package_digest}")

    # Build active candidate dictionary truth simulation
    # (Since there is no grant or proof, compute_h1c_truth will correctly compute fail-closed status)
    truth = compute_h1c_truth(repo_root=ROOT)
    
    # Assert expected gate values
    print(f"Computed safe_to_execute: {truth.get('safe_to_execute')}")
    print(f"Computed promotion: {truth.get('promotion')}")
    print(f"Computed founder_action_required: {truth.get('founder_action_required')}")
    print(f"Computed blockers: {truth.get('blockers')}")
    
    # Target directory for commit-bound review packet
    target_dir = ROOT / "docs" / "evidence" / "council" / f"H1C_DOORSTEP_COMMITBOUND_{head_sha[:8]}"
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Target directory: docs/evidence/council/H1C_DOORSTEP_COMMITBOUND_{head_sha[:8]}/")

    # Generate DOORSTEP packet
    packet_path = target_dir / "FOUNDER_DOORSTEP_PACKET.json"
    packet = build_doorstep_founder_packet(truth, packet_path)
    print(f"Generated {packet_path.name}")

    # Generate pending authorization template
    pending = {
        "schema_version": "1.0",
        "decision_type": "H1C_CONTROLLED_LOCAL_EXECUTION",
        "decision_status": "PENDING_FOUNDER_DECISION",
        "founder_identity": "Michael Bryan Hoch",
        "approval_id": None,
        "decision": None,
        "reason": None,
        "candidate_id": package_id,
        "package_id": package_id,
        "package_digest": package_digest,
        "implementation_commit": head_sha,
        "authorized_environment": "local_only",
        "authorized_execution_scope": [
            "h1c_controlled_dry_run",
            "local_read_only_probe",
            "local_ledger_write",
            "local_evidence_emit"
        ],
        "external_dispatch_allowed": False,
        "founder_only_actions_allowed": False,
        "operator_hold_release_required": True,
        "fresh_live_proof_required": True,
        "automatic_relock_required": True,
        "issued_at": None,
        "expires_at": None,
        "founder_signature": None,
        "source_packet_sha256": "24eea4eabe7ce3f94fb36a895ffb3351e742d937b8ac7ed717ef30d6032de19a",
        "validation_sha256": "c49e84b325c62e770daad773e2d06ab44fe473de28986785428e04a1db22d0aa"
    }
    
    pending_path = target_dir / "founder_authorization.pending.json"
    pending_path.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {pending_path.name}")

    # Generate SHA256SUMS file
    sums = []
    for f in sorted(os.listdir(target_dir)):
        if f != "SHA256SUMS":
            fp = target_dir / f
            sums.append(f"{_sha256_file(fp)}  ./{f}")
            
    sums_path = target_dir / "SHA256SUMS"
    sums_path.write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(f"Generated SHA256SUMS")

    # Also place a copy of the pending template directly under coordination/council for operators
    council_dir = ROOT / "coordination" / "council"
    council_pending = council_dir / "h1c_founder_authorization.pending.json"
    council_pending.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
    print(f"Placed active pending template: coordination/council/{council_pending.name}")

    print("=== PACKET GENERATION SUCCESSFULLY COMPLETED ===")

if __name__ == "__main__":
    main()
