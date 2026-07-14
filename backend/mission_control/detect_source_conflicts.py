"""Commit-boundary conflict detector — the fail-closed teeth of the source-tree guard.

THE ENFORCEMENT POINT
---------------------
A lease only helps agents that acquire it. But EVERY agent — Claude, Grok, a human, a script —
passes through `git commit`. So the commit boundary is where enforcement is real regardless of whether
the writer cooperated with the lease. This module answers one question at that boundary:

    "Is any file being committed currently held by a DIFFERENT holder's ACTIVE lease?"

If yes, that is a CONFLICT: two agents are about to write the same file into durable history. An
EXPIRED lease never blocks (it is reclaimable — a dead agent must not wedge the team). A file the
committer holds itself never blocks.

MODES
-----
  default : WARN + journal the conflict, let the commit proceed. Chosen so a non-participating agent
            (e.g. Grok, which does not take leases) is not hard-blocked — but the collision is RECORDED,
            which is the AU-9 principle: make it impossible to hide, even if you do not prevent it.
  strict  : HELM_SOURCE_LEASE_STRICT=1 -> exit non-zero, BLOCK the commit. Full single-writer enforcement.

Identity of the committer comes from HELM_SOURCE_HOLDER (falls back to git user.name, then $USER).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
# Run as a git hook (`python3 backend/mission_control/detect_source_conflicts.py`) the package root is
# NOT on sys.path, so `import backend...` fails. Put it there. (The unit tests passed only because
# pytest already adds the root — a gap this standalone entrypoint exposed.)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _committer() -> str:
    if os.environ.get("HELM_SOURCE_HOLDER"):
        return os.environ["HELM_SOURCE_HOLDER"]
    try:
        n = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, cwd=ROOT)
        if n.returncode == 0 and n.stdout.strip():
            return n.stdout.strip()
    except Exception:
        pass
    return os.environ.get("USER", "unknown")


def _staged_paths() -> List[str]:
    try:
        out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                             capture_output=True, text=True, cwd=ROOT)
        return [l for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def check_paths_against_leases(paths: List[str], committer: str,
                               manager: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Return a CONFLICT record for every path under another holder's ACTIVE (unexpired) lease.

    Pure and testable: no git, no I/O beyond the lease dir. An expired lease is reclaimed first so it
    never blocks. A lease held by the committer itself is not a conflict.
    """
    from backend.mission_control.source_lease import SourceLeaseManager
    mgr = manager or SourceLeaseManager()
    mgr.reclaim_expired()                       # a dead agent's stale lease must not block the team
    conflicts: List[Dict[str, Any]] = []
    for path in paths:
        lease = mgr.read_lease(path)
        if not lease or lease.get("__corrupt__"):
            continue
        if lease.get("status") != "ACTIVE" or mgr.is_expired(lease):
            continue
        if lease.get("holder") == committer:
            continue                            # you may commit a file you hold
        conflicts.append({
            "path": mgr._norm(path),
            "held_by": lease.get("holder"),
            "committer": committer,
            "lease_id": lease.get("lease_id"),
            "acquired_at": lease.get("acquired_at"),
            "fencing_token": lease.get("fencing_token"),
        })
    return conflicts


def _journal(conflicts: List[Dict[str, Any]]) -> None:
    try:
        d = ROOT / "coordination" / "source_leases"
        d.mkdir(parents=True, exist_ok=True)
        import datetime
        with open(d / "_conflict_journal.jsonl", "a", encoding="utf-8") as f:
            for c in conflicts:
                f.write(json.dumps({**c, "detected_at":
                                    datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n")
    except Exception:
        pass


def main() -> int:
    strict = os.environ.get("HELM_SOURCE_LEASE_STRICT") == "1"
    try:
        committer = _committer()
        paths = _staged_paths()
        if not paths:
            return 0
        conflicts = check_paths_against_leases(paths, committer=committer)
    except Exception as e:
        # The guard itself errored. Do NOT block a commit on our own bug in warn mode — that would be
        # a false-red wedging the whole team. Surface it loudly; block only if the operator chose strict.
        sys.stderr.write(f"\n⚠️  source-guard internal error: {e}\n"
                         f"   {'BLOCKED (strict)' if strict else 'commit allowed (warn) — guard skipped'}\n\n")
        return 1 if strict else 0
    if not conflicts:
        return 0
    _journal(conflicts)
    sys.stderr.write("\n⚠️  SOURCE-TREE COORDINATION CONFLICT\n")
    for c in conflicts:
        sys.stderr.write(
            f"   {c['path']} is held by '{c['held_by']}' (lease {c['lease_id']}, "
            f"token {c['fencing_token']}) — you are '{c['committer']}'.\n")
    if strict:
        sys.stderr.write("   BLOCKED (HELM_SOURCE_LEASE_STRICT=1). Coordinate or wait for release.\n\n")
        return 1
    sys.stderr.write("   WARN only — commit allowed, conflict RECORDED to "
                     "coordination/source_leases/_conflict_journal.jsonl\n"
                     "   (set HELM_SOURCE_LEASE_STRICT=1 to block instead.)\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
