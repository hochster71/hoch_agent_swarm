# Image Repopulation Protocol — AWAITING_MICHAEL_IMAGE_UPLOAD (2026-07-02)

**Blank Reset State Confirmed**:
- doctrine: BLANK_IMAGE_RESET_PENDING_MICHAEL_REPOPULATION
- approved image count: 0
- image authority active: false
- active repo image inventory: zero (after purge)
- workspace hygiene: PASS
- visual doctrine: PASS

**Inbox Structure**:
- Path: `docs/design/approved-visual-authority-inbox/`
- README_DROP_APPROVED_IMAGES_HERE.md: Created with strict rules (candidates NOT authority, Michael approval required for lock, no screenshots/contact sheets, inventory required)

**Scripts Created**:
- `scripts/review_visual_authority_candidates.py`: Reads inbox, computes SHA256/dimensions, creates review MD/HTML, marks as CANDIDATE_ONLY_NOT_AUTHORITY. No lock performed. (PASS with no candidates)
- `scripts/lock_visual_authority_from_approved_candidates.py`: Fails closed unless MICHAEL_APPROVAL.txt contains "APPROVE IMAGE DOCTRINE LOCK". Placeholder for future lock. (BLOCKED_AWAITING_MICHAEL_APPROVAL as expected)

**Approval Gate**:
- Required phrase: APPROVE IMAGE DOCTRINE LOCK
- Lock blocked without approval: YES

**Guard Updates**:
- verify_workspace_visual_hygiene.py: Accepts blank reset and candidate inbox (no active authority)
- verify_visual_authority_doctrine.py: Accepts blank reset mode

**Current Status**: AWAITING_MICHAEL_IMAGE_UPLOAD to inbox. Grok will review candidates, create evidence, and await explicit approval before locking doctrine or updating runtime.

**Verification**:
- visual doctrine: PASS
- workspace hygiene: PASS
- candidate review: PASS (NO_CANDIDATES)
- lock placeholder: BLOCKED_AWAITING_MICHAEL_APPROVAL (correct)
- autonomous facilitation: PASS
- full Playwright: PASS
- frontend build: PASS
- rc29: PASS
- baseline scan: PASS

**Michael Next Step**: Upload approved images to `docs/design/approved-visual-authority-inbox/` and reply with "APPROVE IMAGE DOCTRINE LOCK" to trigger review and lock.

**Evidence Path**: This file.
