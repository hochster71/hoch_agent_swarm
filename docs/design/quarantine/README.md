# Quarantine Directory — superseded-visual-authority-do-not-use

**Purpose**: Temporary holding for superseded visual authority artifacts, old packages, contact sheets, screenshots of VS Code/Grok/Finder, and bad image candidates.

**Rules**:
- This directory must remain **text-only** in the active repo (READMEs only).
- All binary image/ZIP/contact-sheet files have been moved to the external archive: `/Users/michaelhoch/hoch_agent_swarm_archive/visual-garbage-do-not-use/`.
- None of these files are visual authority.
- The only approved authority is `docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg` (SHA256 21bd9aef213e45824295a9a3e85b4f8817f841962a9ad24e817a12bdc3b1f442).
- Do not reference any file in this directory as runtime authority.
- WORKSPACE_VISUAL_HYGIENE script will FAIL if binary visual garbage remains in the repo quarantine or root.

This quarantine prevents discovery of garbage by Grok/VS Code startup analysis.
