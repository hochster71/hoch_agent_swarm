# QA Gate Refresh Report — Stale Gate Attempt

- Generated (UTC): 2026-07-16T12:52:32Z
- Author: HELM subagent (read-only verifier attempt)
- Matrix source: `has_live_project_tracker/data/qa_gate_matrix.json`
- Doctrine: NO FAKE GREEN — matrix was NOT modified; nothing was marked PASS without a real passing run.

## Summary
The matrix header declares `total_gates: 12, passing: 10, stale: 2`, but the `gates` array only
enumerates 2 gate objects, and both carry `"freshness_state": "FRESH"`. There is no gate object
with a literal `"freshness_state": "STALE"` in the file (the array is incomplete — 2 of the claimed
12 gates are present). The 2 enumerated gates are the only ones with a `command_or_task`, and both
were last run `2026-07-02T11:29:00Z` — 14 days before today (`2026-07-16`), which is what the
header's `stale: 2` count reflects. I treated these 2 as the gates to refresh and recorded the
freshness/enumeration discrepancy honestly below.

## The 2 stale gates

| gate_id | command_or_task | last_run | field says | header says |
|---|---|---|---|---|
| `visual_doctrine` | `python scripts/verify_visual_authority_doctrine.py` | 2026-07-02T11:29:00Z | FRESH | counted in stale:2 |
| `workspace_hygiene` | `python scripts/verify_workspace_visual_hygiene.py` | 2026-07-02T11:29:00Z | FRESH | counted in stale:2 |

## What I ran in THIS sandbox (Linux, system python3)

Both verifier scripts are pure Python **stdlib** (`hashlib`, `json`, `sys`, `pathlib`) — there is
**no third-party import**, so the `.venv` (macOS-only) is NOT the blocker. The real blocker is that
both scripts hardcode `ROOT = Path("/Users/michaelhoch/hoch_agent_swarm")`. That absolute macOS path
does not exist in this Linux sandbox (the repo is mounted at `/sessions/.../mnt/hoch_agent_swarm`),
and the sandbox root filesystem is read-only (I cannot even `mkdir /Users` to place a compatibility
symlink). Therefore the scripts read non-existent paths and fail spuriously.

### Command 1 — verify_visual_authority_doctrine.py (verbatim)
```
$ cd <repo root> && python3 scripts/verify_visual_authority_doctrine.py
HAS/HASF VISUAL AUTHORITY DOCTRINE GUARD
============================================================
VISUAL_AUTHORITY_DOCTRINE: FAIL - Manifest missing
EXIT=1
```
This FAIL is a path artifact (script looked under `/Users/michaelhoch/...` which is absent on Linux),
NOT a real gate result.

### Command 2 — verify_workspace_visual_hygiene.py (verbatim)
```
$ python3 scripts/verify_workspace_visual_hygiene.py
WORKSPACE VISUAL HYGIENE GUARD
==================================================
WORKSPACE_VISUAL_HYGIENE: FAIL - Doctrine shield README missing
EXIT=1
```
Also a path artifact. I attempted to redirect the hardcoded path at the real mounted repo via a
`/Users/michaelhoch/hoch_agent_swarm` symlink; the sandbox root is read-only
(`mkdir: cannot create directory '/Users': Permission denied`), so a genuine sandbox run is impossible.

## Read-only host verification of the real repo state
Since I could not execute the gates against the real tree in the sandbox, I verified (read-only) every
precondition the two scripts check, using the real files:

**visual_doctrine preconditions — all satisfied → gate would PASS on the Mac:**
- `docs/design/approved-visual-authority/visual-authority-manifest.json`: `approved_image_count = 1`,
  `no_variance = true`, doctrine LOCKED (not blank-reset).
- Canonical image present: `docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg`.
- SHA256 matches expected `21bd9aef213e45824295a9a3e85b4f8817f841962a9ad24e817a12bdc3b1f442` (confirmed via `sha256sum` on the mounted file).
- No forbidden filename patterns ("HOCH POOS" / "two-image" / "four-image" / "multi-image" / "contact-sheet") outside quarantine.

**workspace_hygiene preconditions — ONE FAILS → gate would currently FAIL on the Mac:**
- Root-level visual garbage IS present: **`helm_concept_v1.png` sits at the repo root.**
  The script runs `ROOT.glob("*.png")` and will detect this file →
  `WORKSPACE_VISUAL_HYGIENE: FAIL - Root-level visual garbage detected`.
- Required READMEs exist (`approved-visual-authority/README_DOCTRINE.md`,
  `approved-visual-authority-inbox/README_DROP_CANDIDATES_HERE.md`).
- No binary garbage in `docs/design/quarantine`; no `*HOCH*POOS*` / `*contact-sheet*` filenames.

## Honest gate status
- `visual_doctrine`: **UNKNOWN in sandbox** (could not truly run) — but all preconditions verified;
  expected to PASS on a real Mac run.
- `workspace_hygiene`: **UNKNOWN in sandbox** — and the real tree currently has a blocker
  (`helm_concept_v1.png` at repo root). A real run today would return **FAIL**, not PASS.
  This gate must NOT be marked FRESH/PASS until the root PNG is removed/relocated. (I did not move it —
  that is a repo-state change outside read-only scope.)

## Precise real-machine (Mac + repo .venv) commands to bring these FRESH
```bash
cd /Users/michaelhoch/hoch_agent_swarm
source .venv/bin/activate   # optional; scripts use only stdlib

# Gate 1 — expected PASS
python scripts/verify_visual_authority_doctrine.py ; echo "exit=$?"

# Gate 2 — FIRST clear the root-level garbage, else it FAILS honestly:
#   move helm_concept_v1.png out of the repo root (e.g. to the external
#   /Users/michaelhoch/hoch_agent_swarm_archive/visual-garbage-do-not-use/,
#   or into an approved subfolder). Then:
python scripts/verify_workspace_visual_hygiene.py ; echo "exit=$?"
```
Only after BOTH commands print their `... : PASS` lines with `exit=0` should the founder's freshness
tooling stamp `last_run_time` and set `freshness_state: FRESH` for these two gate ids. Per NO FAKE
GREEN, do not edit `qa_gate_matrix.json` to claim PASS ahead of those real runs.
