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

## The swarm roster — every agent is covered

The commit-boundary detector fires on **any** `git commit` to this repo, no matter which tool makes it
(the hook is wired through `core.hooksPath`, not into any one agent). So Claude, Grok, the ChatGPT CLI,
and the AG IDE are **already** covered for detection the moment the hook is enabled — there is no
per-agent code to write. The only per-agent step is giving each one a stable **holder identity** so the
conflict record names the right author. Set it once per tool:

| Agent | holder id | how it sets identity |
|---|---|---|
| Claude (this agent) | `claude` | `export HELM_SOURCE_HOLDER=claude` in its shell env |
| Grok CLI / `agent` | `grok` | `export HELM_SOURCE_HOLDER=grok` |
| ChatGPT CLI (e.g. `codex`) | `chatgpt-cli` | `export HELM_SOURCE_HOLDER=chatgpt-cli` |
| AG IDE | `ag-ide` | `export HELM_SOURCE_HOLDER=ag-ide` |

If an agent sets no `HELM_SOURCE_HOLDER`, the detector falls back to `git config user.name`, then
`$USER` — so a conflict is still recorded, just under whatever identity git sees. To make a cooperating
agent also **take** leases before editing (so others are actively blocked, not just warned after), wire
the `acquire()/record_own_write()/release()` calls from the snippet above into that agent's edit step.
Detection at the commit boundary needs nothing; prevention needs the agent to take the lease.

> The holder ids above are a starting convention for the agents named so far. If the roster differs
> (different binary, more agents), the guard doesn't care — any string works — but keeping the ids
> consistent is what makes the conflict journal readable.

## Active prevention — `guarded_edit` (upgrade from detect to prevent)

Detection (the commit hook) records a collision after it happened. **Prevention** stops it: an agent
takes the lease *before* editing, so a second agent is turned away instead of warned later. The
`guarded_edit` facade makes this one wrapper for any agent.

**Python agent:**
```python
from backend.mission_control.guarded_edit import guarded_edit
with guarded_edit("frontend_live/command.html", holder="claude") as g:
    if not g.ok:
        ...                      # held by g.held_by — back off
    else:
        ...                      # edit; lease auto-released on exit, even if the edit raises
```

**Shell-driven agent (Grok / ChatGPT CLI / AG IDE)** — wrap the edit command atomically:
```bash
python -m backend.mission_control.guarded_edit run frontend_live/command.html \
    --holder grok -- <your-edit-command>
```
If the file is held by another agent, the command is **not executed** and it exits `3`. Verified live:
`grok` edits successfully; while `grok` holds it, `claude`'s wrapped edit is refused and the file is
untouched — the clobber never happens. Also available: `acquire` / `release` / `status` subcommands for
agents that hold a lease across several steps.

Detection needs nothing (the hook covers every agent). Prevention needs the agent to route its edits
through `guarded_edit` — start with the highest-contention files (the shared UI + API).

## What it deliberately does NOT claim

- It does not prevent a non-cooperating process from overwriting a file mid-edit. It **detects** that
  (`verify_no_clobber`, and the commit-boundary journal), which is the enforceable, honest guarantee.
- It is per-file, never global: two agents editing two different files never contend.

## Tests

`tests/test_source_lease.py` (14 tests, written before the implementation): reproduces the clobber and
proves the lease stops it, TTL reclaim of a dead agent's lease, stale-writer fencing, corrupt-lock
quarantine, injective paths, content-hash clobber detection, and the commit-boundary detector in every
mode. Run: `python -m pytest tests/test_source_lease.py -q --import-mode=importlib`.
