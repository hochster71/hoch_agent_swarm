# Northstar Autonomy Engine — "set a goal, walk away"

The keystone that ends copy-paste. You give HAS **one northstar** (a goal in a sentence). The
engine decomposes it, runs the work autonomously to the doorstep, and surfaces only the decisions
that are legally/financially yours.

## Pieces
- **`scripts/northstar_planner.py`** — decomposes a northstar into a phased task DAG
  (Research → Design → Develop → Verify → Package → Launch), refilling the loop queue phase by
  phase. Deterministic skeleton (works offline, $0); optional model enrichment.
- **`scripts/northstar_daemon.py`** — the persistent runner. Each cycle: plan → run the next SAFE
  task through the real engine → stage founder-gated work → write progress + a doorstep digest.
- **`northstar.json`** — the current goal + phase. **`northstar_state.json`** — live progress.
  **`doorstep_digest.json`** — the short "what needs you" list.

## Autonomy levels (honest, by design)
- **AUTO ($0, no human):** Research, Design, Verify, Package — produce real docs/plans on the local
  brain, behind the verify gate.
- **DEFERRED (needs your OK once):** Develop/code tasks run only with `AGENT_ALLOW_CODE=1` — enabling
  autonomous code is a founder decision.
- **FOUNDER-GATED (always you):** Launch, submit, pay, sign, move money — staged at the doorstep,
  never executed by an agent. This is irreducible (your DOORSTEP doctrine + platform safety).

Target: ~85% hands-off. You set the goal and approve at the door — you don't paste the work.

## Use
```
python3 scripts/northstar_planner.py set "Launch HSF Story Studio as a paid product"
NS_SLEEP=5 python3 scripts/northstar_daemon.py          # runs forever; SAFE by default
# check what (if anything) needs you:
python3 scripts/northstar_planner.py status
cat has_live_project_tracker/data/doorstep_digest.json
```
To run 24/7 unattended, wrap the daemon in a launchd/systemd service.

## Governance (inherited from the harness)
Tier router (local→cheap→frontier) · verify-and-retry acceptance gate · fail-closed monthly cost
cap · DOORSTEP · change-control board. The planner and daemon are in the agent's DENY_WRITE set —
the swarm cannot edit its own brain.

**Proven 2026-07-07:** one northstar → daemon planned RESEARCH → local brain autonomously wrote a
real market-research doc at $0, no human input.
