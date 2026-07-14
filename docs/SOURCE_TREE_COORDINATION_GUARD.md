# Source-Tree Coordination Guard

**Problem it solves.** On 2026-07-14 a Claude agent and a Grok agent edited the same source files
(`backend/helm_live_api.py`, `frontend_live/command.html`) concurrently with no mutual exclusion. It
merged by luck. The AU-9 chain enforces a single writer on the **evidence** plane; nothing did the
same for the **source** tree. This guard closes that gap — it is the source-edition of the per-task
lease, reusing the same hardened mechanics (atomic `O_EXCL` acquire, monotonic per-file fencing
tokens, TTL reclaim that is enforced not decorative, corrupt-lock quarantine, injective digest paths).

## Two layers, honestly scoped

A lease only constrains agents that **acquire** it. It cannot stop a non-participating editor from
writing a file — claiming otherwise would be theatre. So the guard has two teeth:

1. **`SourceLeaseManager`** (`backend/mission_control/source_lease.py`) — per-file mutual exclusion
   for cooperating agents. `acquire()` returns `None` if another holder has an active lease.
   `verify_no_clobber()` uses a content hash to detect a write by a **non-holder** after the fact.
2. **Commit-boundary detector** (`backend/mission_control/detect_source_conflicts.py`) — the
   fail-closed enforcement point that **every** agent passes through (`git commit`), whether or not it
   cooperated with the lease. This is the AU-9 principle applied to source: make a collision
   impossible to hide, even when you do not prevent it.

## How an agent cooperates

```python
from backend.mission_control.source_lease import SourceLeaseManager
mgr = SourceLeaseManager()
lease = mgr.acquire("frontend_live/command.html", holder="claude")
if lease is None:
    ...  # another agent holds it — do NOT edit; back off
# ...edit the file...
mgr.record_own_write("frontend_live/command.html", lease["lease_id"])  # my edits aren't a clobber
mgr.release("frontend_live/command.html", lease["lease_id"])
```

## How enforcement works at commit time

```
git config core.hooksPath .githooks          # enable the pre-commit hook (one-time, per clone)
export HELM_SOURCE_HOLDER=claude              # this agent's identity (else falls back to git user.name)
```

On `git commit`, the hook checks every staged file:

| Situation | Result |
|---|---|
| File under **another** holder's active lease | **default:** WARN + journal to `_conflict_journal.jsonl`, commit proceeds · **strict:** `HELM_SOURCE_LEASE_STRICT=1` → commit **blocked** |
| File the committer holds itself | allowed |
| File under an **expired** lease | allowed (expired leases are reclaimed first — a dead agent must not wedge the team) |
| File under no lease | allowed |

Default is **warn + record** so a non-participating agent (e.g. one not yet wired to take leases) is
not hard-blocked, but the collision is durably recorded. Flip to **strict** for full single-writer
enforcement once every agent in the swarm takes leases.

## What it deliberately does NOT claim

- It does not prevent a non-cooperating process from overwriting a file mid-edit. It **detects** that
  (`verify_no_clobber`, and the commit-boundary journal), which is the enforceable, honest guarantee.
- It is per-file, never global: two agents editing two different files never contend.

## Tests

`tests/test_source_lease.py` (14 tests, written before the implementation): reproduces the clobber and
proves the lease stops it, TTL reclaim of a dead agent's lease, stale-writer fencing, corrupt-lock
quarantine, injective paths, content-hash clobber detection, and the commit-boundary detector in every
mode. Run: `python -m pytest tests/test_source_lease.py -q --import-mode=importlib`.
