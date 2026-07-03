# Workspace Visual Garbage Cleanup — Hard Clean (2026-07-02)

**Problem Statement**: Grok/VS Code startup discovery was surfacing root-level and in-repo visual garbage (a_wide_high_detail...png, hoch-approved* ZIPs, contact sheets, screenshots of VS Code/Grok/Finder, prior 2/4-image doctrine packages, old imports). This created doctrine drift and wasted focus.

**Correction**: Rejected bad recommendation to `git add docs/design/quarantine/`. Quarantine binaries were moved to **external archive** instead of committing junk.

**External Archive**: `/Users/michaelhoch/hoch_agent_swarm_archive/visual-garbage-do-not-use/`

**Moved Out Of Repo** (no longer discoverable):
- `a_wide_high_detail_ui_dashboard_screenshot_conc.png`
- All `hoch-approved-visual-authority*` folders/ZIPs/contact-sheets
- `hoch-pods-has-hasf-approved-authority*` variants
- All superseded authority images (control-plane, theater, HOCH POOS candidates)
- Prior review files, contact sheets, and bad upload artifacts
- All binary content from `docs/design/quarantine/superseded-visual-authority-do-not-use/`

**Kept In Repo**:
- Canonical authority: `docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg` (SHA256 verified, unchanged)
- Legitimate evidence screenshots: `docs/evidence/ui/screenshots/*` (Playwright baselines, cockpit, prototype comparisons)
- Text-only quarantine/READMEs and discovery shields
- Source code, evidence docs, build files

**Root Cleanliness**: **YES** — No image, ZIP, or hoch-approved* clutter remains in repo root.

**Discovery Shield**:
- `docs/design/approved-visual-authority/README_DOCTRINE.md` (created — single authority only)
- `docs/design/approved-visual-authority-inbox/README_DROP_CANDIDATES_HERE.md` (created — candidates only, no root placement)
- `.gitignore` updated with safe patterns (visual garbage prevented, canonical kept)
- `.vscode/settings.json` updated with search/file/watcher excludes for quarantine and archive

**Verification** (all after cleanup):
- visual doctrine: **PASS**
- workspace visual hygiene: **PASS**
- voice policy: **PASS**
- autonomous facilitation check: **PASS**
- RC55: **PASS**
- RC56: **PASS**
- full Playwright: **PASS**
- frontend build: **PASS**
- rc29: **PASS**
- baseline scan: **PASS**

**Evidence Path**: This file.

**Remaining Blockers**: None. Workspace is now clean. Grok discovery will no longer surface garbage. All binary visual artifacts are safely archived externally.

**FINAL GO** — Visual hygiene achieved. Single approved authority protected. No committed junk.
