#!/usr/bin/env python3
"""actor_f2_classify.py — resolve the ACTOR-F2 account boundary from collected records.

Reads coordination/governance/actor_f2_observations.jsonl and classifies each context:

    SAME_HOST_ACCOUNT     same host authority AND same OS account as another record
    DISTINCT_HOST_ACCOUNT same host, different OS account
    NAMESPACE_ONLY        different kernel/host identity reachable via namespace remapping
                          (bwrap, container, VM) — identity INSIDE that namespace only
    REMOTE_OR_EXTERNAL    a separate authority entirely (GitHub runner, remote machine)
    UNRESOLVED            insufficient evidence to classify

HARD RULE, from the review: this resolves the ACCOUNT boundary ONLY. It says NOTHING
about key custody. Shared account is NECESSARY BUT NOT SUFFICIENT for shared custody —
Secure Enclave, Keychain ACLs, and separate security principals can partition key access
within one account. Custody is ACTOR-F3 and requires its own observation.

A single record cannot establish a shared/distinct relationship: those are RELATIONS,
and a relation needs two terms. With one record the answer is UNRESOLVED, not "isolated".
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "coordination" / "governance" / "actor_f2_observations.jsonl"

# Kernels/hostnames that indicate the record came from inside a remapped namespace
# rather than from the macOS host itself.
_NAMESPACE_PARENTS = {"bwrap", "containerd-shim", "docker-init", "runc", "systemd-nspawn"}


def load():
    if not OBS.exists():
        print(f"FAIL: no observations at {OBS.relative_to(ROOT)}. Run the collector first.",
              file=sys.stderr)
        raise SystemExit(2)
    recs = []
    for line in OBS.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARN: skipping malformed record: {e}", file=sys.stderr)
    return recs


def classify(recs):
    # Group by (hostname, os_user). Two records share an account only if BOTH match
    # AND neither is namespace-remapped — a bwrap uid says nothing about the host.
    buckets = defaultdict(list)
    out = []
    for r in recs:
        o = r.get("observed", {})
        host, user = o.get("hostname", "?"), o.get("os_user", "?")
        parent = (o.get("grandparent_process") or "") + " " + (o.get("parent_process") or "")
        namespaced = any(p in parent for p in _NAMESPACE_PARENTS)
        buckets[(host, user, namespaced)].append(r.get("context_label", "?"))
        out.append({"label": r.get("context_label"), "host": host, "user": user,
                    "uid": o.get("uid"), "uname": o.get("uname"),
                    "namespaced": namespaced,
                    "git": f"{o.get('git_user_name')} <{o.get('git_user_email')}>",
                    "signingkey": o.get("git_signingkey"),
                    "runner": bool(r.get("observed", {}).get("runner_os"))})

    for e in out:
        key = (e["host"], e["user"], e["namespaced"])
        peers = [p for p in buckets[key] if p != e["label"]]
        if e["runner"]:
            e["classification"] = "REMOTE_OR_EXTERNAL"
            e["basis"] = "GitHub-hosted runner; separate authority"
        elif e["namespaced"]:
            e["classification"] = "NAMESPACE_ONLY"
            e["basis"] = (f"parent lineage indicates namespace remapping; uid {e['uid']} is "
                          "identity INSIDE that namespace and does not describe the host")
        elif peers:
            e["classification"] = "SAME_HOST_ACCOUNT"
            e["basis"] = f"same host+account as: {', '.join(peers)}"
        else:
            same_host_other_user = [lbl for (h, u, n), lbls in buckets.items()
                                    if h == e["host"] and u != e["user"] and not n
                                    for lbl in lbls]
            if same_host_other_user:
                e["classification"] = "DISTINCT_HOST_ACCOUNT"
                e["basis"] = f"same host, different account from: {', '.join(same_host_other_user)}"
            else:
                e["classification"] = "UNRESOLVED"
                e["basis"] = ("no comparable peer record. SHARED and DISTINCT are RELATIONS "
                              "and need two terms — one record cannot establish either.")
    return out


def main() -> int:
    recs = load()
    rows = classify(recs)
    print(f"ACTOR-F2 ACCOUNT BOUNDARY — {len(rows)} record(s)\n")
    for e in rows:
        print(f"  {e['label']}")
        print(f"      {e['classification']}")
        print(f"      host={e['host']} user={e['user']} uid={e['uid']} os={e['uname']}")
        print(f"      git={e['git']}  signingkey={e['signingkey']}")
        print(f"      basis: {e['basis']}\n")

    unresolved = [e for e in rows if e["classification"] == "UNRESOLVED"]
    print("=" * 72)
    if len(rows) < 2:
        print("ACTOR-F2 INCOMPLETE — fewer than 2 records. No boundary relation is derivable.")
    elif unresolved:
        print(f"ACTOR-F2 INCOMPLETE — {len(unresolved)} context(s) UNRESOLVED.")
    else:
        print("ACTOR-F2 account boundary RESOLVED for all collected contexts.")
    print("ACTOR-F3 (key custody) remains BLOCKED regardless: a shared account is "
          "NECESSARY BUT NOT SUFFICIENT for shared custody. Custody needs its own observation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
