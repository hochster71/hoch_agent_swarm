#!/usr/bin/env python3
"""commit_lease.py — GOVERNED COMMIT LEASE (founder decision 2026-07-20, GOV-005).

HELM is not blocked by implementation. It is blocked by uncontrolled repository authority.
Six commits advanced the governed branch while the builder sat behind a closed gate; every
review pinned before that window went stale the instant it landed.

The defect was never "another actor committed". It was that HEAD moved without exclusive
authority, without attribution, without register reconciliation, and without invalidating
reviews pinned to the prior HEAD.

WHAT THIS DOES NOT DO
---------------------
This cannot *prevent* a determined concurrent writer — git has no server-side lease here and
any actor with shell access can commit. It makes uncontrolled advancement DETECTABLE and
ATTRIBUTABLE, and it fails closed when the world moved underneath it. Do not describe it as
mutual exclusion; describe it as a fencing check with an audit trail. Claiming enforcement it
does not have would be the same defect class it exists to catch.

    acquire  -> writes a lease with a fencing token and base_head
    check    -> refuses when HEAD, remote, register, or token drifted
    release  -> records resulting SHA, invalidates prior-HEAD reviews

Usage:
    scripts/commit_lease.py acquire --actor <id> --paths <p> [<p>...] [--ttl 3600]
    scripts/commit_lease.py check
    scripts/commit_lease.py release --sha <sha>
    scripts/commit_lease.py status
"""
from __future__ import annotations
import argparse, hashlib, json, os, secrets, subprocess, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEASE = ROOT / "coordination" / "governance" / "commit_lease.json"
REGISTER = ROOT / "coordination" / "governance" / "open_claims_register.json"
REMOTE_REF = "github/helm-runtime-bridge-v1"


def _git(*a) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()

def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def _iso(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def _allowlist_hash(paths) -> str:
    return hashlib.sha256("\n".join(sorted(paths)).encode()).hexdigest()

def _register_head():
    try:
        return json.loads(REGISTER.read_text()).get("recorded_head")
    except Exception:
        return None


def acquire(args) -> int:
    if LEASE.exists():
        cur = json.loads(LEASE.read_text())
        if cur.get("state") == "ACTIVE" and _iso(_now()) < cur.get("expires_at", ""):
            print(f"REFUSED: active lease held by {cur['authorized_actor_id']} "
                  f"(session {cur['owner_session_id']}) until {cur['expires_at']}", file=sys.stderr)
            return 4
    head = _git("rev-parse", "HEAD")
    lease = {
        "state": "ACTIVE",
        "owner_session_id": os.environ.get("HELM_SESSION_ID", "stoic-loving-babbage"),
        "authorized_actor_id": args.actor,
        "runtime": "claude/builder",
        "base_head": head,
        "remote_ref": REMOTE_REF,
        "remote_base_head": _git("rev-parse", REMOTE_REF) or None,
        "allowed_paths": sorted(args.paths),
        "allowlist_hash": _allowlist_hash(args.paths),
        "fencing_token": secrets.token_hex(16),
        "acquired_at": _iso(_now()),
        "expires_at": _iso(_now() + datetime.timedelta(seconds=args.ttl)),
    }
    LEASE.parent.mkdir(parents=True, exist_ok=True)
    LEASE.write_text(json.dumps(lease, indent=2) + "\n")
    print(json.dumps(lease, indent=2))
    return 0


def check(_args=None) -> int:
    """Fail closed on ANY drift. Returns 0 only when every precondition holds."""
    if not LEASE.exists():
        print("REFUSED: no lease. Commits require an acquired lease (GOV-005).", file=sys.stderr)
        return 2
    L = json.loads(LEASE.read_text())
    fails = []
    if L.get("state") != "ACTIVE":
        fails.append(f"lease state is {L.get('state')}, not ACTIVE")
    if _iso(_now()) >= L.get("expires_at", ""):
        fails.append(f"lease expired at {L['expires_at']}")

    head = _git("rev-parse", "HEAD")
    if head != L["base_head"]:
        fails.append(f"HEAD DRIFTED — another actor advanced the branch\n"
                     f"      lease base_head {L['base_head']}\n"
                     f"      current HEAD    {head}\n"
                     "      All reviews pinned to base_head are INVALIDATED.")

    remote = _git("rev-parse", L["remote_ref"]) or None
    if remote != L.get("remote_base_head"):
        fails.append(f"remote {L['remote_ref']} drifted: "
                     f"{L.get('remote_base_head')} -> {remote}")

    reg = _register_head()
    if reg != head:
        fails.append(f"REGISTER STALE — register.recorded_head {reg} != HEAD {head}. "
                     "The governance register is not bound to repository truth (GOV-006).")

    staged = [p for p in _git("diff", "--cached", "--name-only").splitlines() if p]
    if staged and sorted(staged) != L["allowed_paths"]:
        fails.append(f"staged set != allowlist\n      allowed {L['allowed_paths']}\n"
                     f"      staged  {sorted(staged)}")

    if fails:
        print("COMMIT LEASE CHECK: FAIL", file=sys.stderr)
        for f in fails:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print(f"COMMIT LEASE CHECK: OK\n  actor {L['authorized_actor_id']}  "
          f"token {L['fencing_token'][:12]}…  base {L['base_head'][:12]}  "
          f"paths {L['allowed_paths']}")
    return 0


def release(args) -> int:
    if not LEASE.exists():
        print("no lease to release", file=sys.stderr); return 2
    L = json.loads(LEASE.read_text())
    L["state"] = "RELEASED"
    L["released_at"] = _iso(_now())
    L["resulting_sha"] = args.sha
    L["reviews_invalidated_at_head"] = L["base_head"]
    L["note"] = ("Any review, snapshot package, or cold-review verdict pinned to "
                 f"{L['base_head']} is INVALID. Re-pin to {args.sha}.")
    LEASE.write_text(json.dumps(L, indent=2) + "\n")
    print(json.dumps(L, indent=2))
    return 0


def status(_args=None) -> int:
    print(LEASE.read_text() if LEASE.exists() else "no lease")
    head = _git("rev-parse", "HEAD")
    print(f"\ncurrent HEAD          {head}")
    print(f"register.recorded_head {_register_head()}")
    print(f"{REMOTE_REF:22s} {_git('rev-parse', REMOTE_REF) or '(absent)'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("acquire"); a.add_argument("--actor", required=True)
    a.add_argument("--paths", nargs="+", required=True); a.add_argument("--ttl", type=int, default=3600)
    a.set_defaults(fn=acquire)
    sub.add_parser("check").set_defaults(fn=check)
    r = sub.add_parser("release"); r.add_argument("--sha", required=True); r.set_defaults(fn=release)
    sub.add_parser("status").set_defaults(fn=status)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
