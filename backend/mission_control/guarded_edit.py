"""guarded_edit — active prevention wrapper around the source-tree lease.

The lease + commit-boundary detector give DETECTION. This facade gives PREVENTION: an agent takes the
lease BEFORE it edits, so a second agent is actively turned away rather than merely warned after the
fact. It is deliberately tiny to adopt:

Python agent:
    from backend.mission_control.guarded_edit import guarded_edit
    with guarded_edit("frontend_live/command.html", holder="claude") as g:
        if not g.ok:
            ...            # another agent holds it — back off
        else:
            ...            # edit the file; the lease is released automatically on exit

Shell-driven agent (Grok / ChatGPT CLI / AG IDE) — wrap the edit command atomically:
    python -m backend.mission_control.guarded_edit run frontend_live/command.html \
        --holder grok -- <your-edit-command>

If the file is held by someone else, `run` does NOT execute the command and exits non-zero. That is the
whole point: the clobber never happens instead of being recorded after it did.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.mission_control.source_lease import SourceLeaseManager  # noqa: E402


class EditBlocked(Exception):
    """Raised (in blocking mode) when the file is already held by another agent."""


@dataclass
class GuardResult:
    ok: bool
    held_by: Optional[str]
    lease: Optional[Dict[str, Any]]


@contextmanager
def guarded_edit(rel_path: str, holder: str, *, manager: Optional[SourceLeaseManager] = None,
                 duration_seconds: Optional[int] = None, block: bool = True) -> Iterator[GuardResult]:
    """Acquire the file lease for the duration of an edit, then release it — even on exception.

    block=True  -> raise EditBlocked if another agent holds the file (default; safest).
    block=False -> yield GuardResult(ok=False, held_by=...) so the caller can decide.

    On success the holder's own write is recorded (record_own_write) so it is never later mistaken for
    a foreign clobber, then the lease is released in a finally-block so a crash cannot leak the lock.
    """
    mgr = manager or SourceLeaseManager()
    kwargs = {"duration_seconds": duration_seconds} if duration_seconds else {}
    lease = mgr.acquire(rel_path, holder=holder, **kwargs)
    if lease is None:
        held = mgr.read_lease(rel_path) or {}
        held_by = held.get("holder")
        if block:
            raise EditBlocked(f"{mgr._norm(rel_path)} is held by '{held_by}' — not editing")
        yield GuardResult(ok=False, held_by=held_by, lease=None)
        return
    try:
        yield GuardResult(ok=True, held_by=holder, lease=lease)
        mgr.record_own_write(rel_path, lease["lease_id"])     # my edit is recorded, not a clobber
    finally:
        mgr.release(rel_path, lease["lease_id"])              # never leak the lock, even on exception


# ----------------------------------------------------------------------------- CLI (shell agents)
def _mk_manager(args) -> SourceLeaseManager:
    ld = Path(args.lease_dir) if args.lease_dir else None
    rr = Path(args.repo_root) if args.repo_root else None
    return SourceLeaseManager(lease_dir=ld, repo_root=rr)


def _cmd_acquire(args) -> int:
    mgr = _mk_manager(args)
    lease = mgr.acquire(args.path, holder=args.holder,
                        **({"duration_seconds": args.seconds} if args.seconds else {}))
    if lease is None:
        held = mgr.read_lease(args.path) or {}
        sys.stderr.write(f"HELD by '{held.get('holder')}' (lease {held.get('lease_id')}) — refused\n")
        return 3
    sys.stdout.write(lease["lease_id"] + "\n")                 # emit lease id for a later release
    return 0


def _cmd_release(args) -> int:
    mgr = _mk_manager(args)
    lease = mgr.read_lease(args.path)
    if not lease or lease.get("__corrupt__"):
        sys.stderr.write("no active lease to release\n")
        return 1
    # release by explicit lease-id if given, else by holder-match (you may release a lease you own)
    if args.lease_id and lease.get("lease_id") != args.lease_id:
        sys.stderr.write("lease-id mismatch — refused\n")
        return 1
    if not args.lease_id and lease.get("holder") != args.holder:
        sys.stderr.write(f"held by '{lease.get('holder')}', not '{args.holder}' — refused\n")
        return 1
    ok = mgr.release(args.path, lease["lease_id"])
    return 0 if ok else 1


def _cmd_status(args) -> int:
    mgr = _mk_manager(args)
    lease = mgr.read_lease(args.path)
    if not lease:
        sys.stdout.write("FREE\n"); return 0
    if lease.get("__corrupt__"):
        sys.stdout.write("CORRUPT\n"); return 0
    state = "ACTIVE" if (lease.get("status") == "ACTIVE" and not mgr.is_expired(lease)) else "EXPIRED"
    sys.stdout.write(f"{state} holder={lease.get('holder')} token={lease.get('fencing_token')}\n")
    return 0


def _cmd_run(args) -> int:
    """Atomic wrapper for shell agents: acquire -> run the edit command -> record -> release.
    If the file is held by another agent, the command is NOT executed."""
    mgr = _mk_manager(args)
    if not args.cmd:
        sys.stderr.write("no command given after --\n"); return 2
    lease = mgr.acquire(args.path, holder=args.holder,
                        **({"duration_seconds": args.seconds} if args.seconds else {}))
    if lease is None:
        held = mgr.read_lease(args.path) or {}
        sys.stderr.write(f"HELD by '{held.get('holder')}' — not running the edit (would clobber)\n")
        return 3
    try:
        proc = subprocess.run(args.cmd)
        mgr.record_own_write(args.path, lease["lease_id"])
        return proc.returncode
    finally:
        mgr.release(args.path, lease["lease_id"])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="guarded_edit",
                                description="Take a source-file lease around an edit (active prevention).")
    sub = p.add_subparsers(dest="cmd_name", required=True)

    def _holder_default():
        return os.environ.get("HELM_SOURCE_HOLDER")

    for name in ("acquire", "release", "status", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("path")
        sp.add_argument("--holder", default=_holder_default(),
                        required=_holder_default() is None)
        sp.add_argument("--seconds", type=int, default=None)
        # also accept these AFTER the subcommand (ergonomic for shell agents); the top-level copies
        # are kept for `guarded_edit --lease-dir X acquire ...` ordering too.
        sp.add_argument("--lease-dir", default=os.environ.get("HELM_SOURCE_LEASE_DIR"))
        sp.add_argument("--repo-root", default=os.environ.get("HELM_SOURCE_REPO_ROOT"))
        if name == "release":
            sp.add_argument("--lease-id", default=None)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Everything after a literal `--` is the edit command (only used by `run`). Split it off BEFORE
    # argparse so options like --holder are not swallowed by the command's own flags.
    cmd: List[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    args = build_parser().parse_args(argv)
    args.cmd = cmd
    return {"acquire": _cmd_acquire, "release": _cmd_release,
            "status": _cmd_status, "run": _cmd_run}[args.cmd_name](args)


if __name__ == "__main__":
    raise SystemExit(main())
