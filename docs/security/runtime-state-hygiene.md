# Runtime State & Repository Hygiene (H3)

## Finding
The audit flagged the repo as carrying ~1.3 GB of runtime state, which makes
history unauditable and increases the odds of another secret-spill (C1-class)
accident.

## Assessment (verified 2026-07-02)
Most of the 1.3 GB is **untracked** and already covered by `.gitignore`:

| Path | Size | Tracked? |
|------|------|----------|
| `.venv/` | 767M | ignored |
| `frontend/node_modules/` | 133M | ignored |
| `node_modules/` | 69M | ignored |
| `.venv-theme-guard/` | 62M | ignored |
| `dist/artifacts/` (pptx/pdf) | ~60M | ignored |
| `artifacts/crew_runs/`, `logs/goal_runner/` | — | ignored |

Actual **tracked** size is ~109 MB. The tracked bloat that does not belong in
version control:

- 5 release tarballs (`dist/releases/*.tar.gz`, `artifacts/.../*.tar.gz`)
- 2 release zips (`dist/releases/0.1.6-.../*.zip`)
- 44 PNG screenshots under `docs/evidence` (evidence — kept, but large)

## Policy
Git is for **code + policy + schemas**, not build outputs or runtime state.
Release binaries belong in GitHub Releases / object storage, referenced by URL
and checksum — not committed. This aligns with the C3 evidence model: integrity
comes from signed manifests + external anchors, not from committing the blob.

## Actions taken
1. `.gitignore` extended to cover release binaries and all runtime-state dirs.
2. `scripts/evict_runtime_state.sh` untracks the 7 release archives/zips
   (kept on disk; removed from the index) and verifies the tree is clean.
3. Screenshots retained as evidence but flagged for migration to Git LFS if the
   evidence set keeps growing.
