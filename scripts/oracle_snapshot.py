#!/usr/bin/env python3
"""oracle_snapshot.py — capture immutable oracle snapshots for promotion verification.

FOUNDER DECISION 2026-07-20: live oracles use SNAPSHOT_COPY, not quiescence and not a
freshness window.

    PROMOTION VERIFICATION   snapshot bytes pinned; tests + cold review use the snapshot
    RUNTIME HEALTH           source stays live; freshness window; never claims byte identity

Never mix the classes. A freshness window supports monitoring; it cannot establish that two
reviewers evaluated the same oracle content.

ATOMICITY
---------
A plain copy can race the writer. Minimum acceptable protocol (founder-specified):

    hash source  ->  copy  ->  hash snapshot  ->  hash source again

Accept ONLY when source_sha256_at_capture == snapshot_sha256. The second source hash MAY
differ — that is expected for a live file — but the drift must be RECORDED, not hidden.
post_capture_source_drift_allowed is true by design: the snapshot is the oracle, the live
source is not.
"""
from __future__ import annotations
import hashlib, json, shutil, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def capture(rel: str, snapshot_dir: Path, retries: int = 3) -> dict:
    src = ROOT / rel
    if not src.exists():
        raise SystemExit(f"FAIL: oracle absent: {rel}")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snap = snapshot_dir / Path(rel).name
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for attempt in range(1, retries + 1):
        h1 = _sha(src)                    # hash source
        shutil.copy2(src, snap)           # copy
        hsnap = _sha(snap)                # hash snapshot
        h2 = _sha(src)                    # hash source again
        if h1 == hsnap:
            return {
                "source_path": rel,
                "source_live": True,
                "capture_started_at": started,
                "source_sha256_at_capture": h1,
                "snapshot_path": str(snap.relative_to(ROOT)) if snap.is_relative_to(ROOT) else str(snap),
                "snapshot_sha256": hsnap,
                "capture_method": "read_hash_read",
                "attempts": attempt,
                "post_capture_source_drift_allowed": True,
                "post_capture_source_sha256": h2,
                "post_capture_drift_observed": h2 != h1,
            }
        # torn read: the writer landed mid-copy. Retry rather than record a bad pin.
    raise SystemExit(
        f"FAIL: {rel} — could not capture a coherent snapshot in {retries} attempts. "
        "The writer is landing inside the copy window. Increase retries, or escalate to "
        "quiescence for this oracle."
    )

def main() -> int:
    out = ROOT / "coordination" / "governance" / "oracle_snapshots"
    rels = sys.argv[1:] or [
        "coordination/goal/goal_state.json",
        "coordination/goal/build_to_goal_status.json",
    ]
    recs = [capture(r, out) for r in rels]
    print(json.dumps(recs, indent=2))
    drift = [r["source_path"] for r in recs if r["post_capture_drift_observed"]]
    if drift:
        print(f"\nNOTE: source drifted after capture (expected for live oracles): {drift}",
              file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
