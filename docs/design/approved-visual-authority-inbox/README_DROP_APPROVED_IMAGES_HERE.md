# approved-visual-authority-inbox

**Purpose**: Michael places candidate images here ONLY for review.

**Strict Rules**:
- Candidate images go here for review.
- Candidates are **NOT** approved authority until Michael explicitly approves with: "APPROVE IMAGE DOCTRINE LOCK"
- Grok must not move candidate images into runtime or approved-visual-authority.
- Grok must not lock doctrine or update manifest until Michael explicitly approves.
- Screenshots of VS Code, Grok, Finder, ChatGPT are **forbidden**.
- Contact sheets are **forbidden** as authority.
- Generated derivatives are **forbidden** unless Michael explicitly approves them.
- Each candidate image must be inventoried with:
  - filename
  - dimensions
  - SHA256
  - visual preview (in review HTML)
  - proposed allowed use
- ChatGPT must audit the candidate review before doctrine lock.
- After approval, Grok will run `scripts/lock_visual_authority_from_approved_candidates.py` to update manifest, runtime marker, and doctrine.

This inbox prevents premature authority and ensures Michael-controlled repopulation after blank image reset.
