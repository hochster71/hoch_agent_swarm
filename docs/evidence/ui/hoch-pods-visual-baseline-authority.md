# HOCH PODS Visual Baseline Authority Audit (2026-07-02)

## Repo Identity
- pwd: /Users/michaelhoch/hoch_agent_swarm
- git root: /Users/michaelhoch/hoch_agent_swarm
- git status summary: Evidence, data JSONs, frontend/index.html (JS patch), verification scripts. No invalid paths used.

## Visual Authority
- approved image path: docs/design/assets/hoch-pods-theater-reference.jpeg
- SHA256: c186e1f1d09a2bb5edbe43003bf81714060496fb914ed73b3cfd500d28eeac59
- rendered HTML src: /docs/design/assets/hoch-pods-theater-reference.jpeg (served 200 OK from 8765)
- visual compliance reference: docs/design/assets/hoch-pods-theater-reference.jpeg (used by audit_hoch_pods_theater_visual_compliance.py and rc52_1 tests)
- do they match: YES

## Candidate Images Found
- a_wide_high_detail_ui_dashboard_screenshot_conc.png (SHA256: c49bf6f3c7b0a2c581858779bd096e2f100918f93fc3bdb3a7e5fcebb6cb1659) — initial control-plane screenshot; NOT the theater shell reference (different hash, different content)
- docs/design/assets/hoch-pods-theater-reference.jpeg (approved theater shell)
- docs/design/assets/hoch-pods-theater-agent-liftoff-reference.jpeg
- docs/design/assets/hoch-pods-theater-intro-movie-agent-spinups-reference.jpeg
- Multiple evidence screenshots (hoch-pods-theater-*.png, rc52_1-*.png) derived from the approved reference.
- tools/hoch_pods_theme_guard/.../hoch-pods-theater-reference.jpeg (copy)

The `a_wide_high_detail_ui_dashboard_screenshot_conc.png` was a prior control-plane prototype; the approved Hoch Pods Theater baseline is the dedicated `hoch-pods-theater-reference.jpeg` (17-frame cinematic storyboard). Rendered HTML and compliance scripts correctly use the theater reference. No drift.

## Changed Files
- docs/evidence/ui/hoch-pods-visual-baseline-authority.md (this audit)
- frontend/index.html (minor JS patch for test stability, not visual)
- docs/evidence/ui/screenshots/rc52_1-hoch-pods-theater-current.png (new capture)

## Commands Run
- `pwd && git rev-parse --show-toplevel && git status --short`: PASS
- `find . -maxdepth 5 -type f \( -iname "*.png" ... \)`: PASS (inventory)
- `grep -RIn "hoch-pods-theater-reference|..." ...`: PASS (references confirmed)
- `curl -I http://127.0.0.1:8765/docs/design/assets/hoch-pods-theater-reference.jpeg`: 200 PASS
- `curl -I http://127.0.0.1:8765/a_wide_high_detail_ui_dashboard_screenshot_conc.png`: 404 (correct, not used)
- `shasum -a 256 ...`: PASS (hashes recorded)
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:8765 npx playwright test tests/e2e/rc52_1-hoch-pods-theater-visual-baseline.spec.ts`: PASS (THEME_COMPLIANCE: PASS, screenshot captured)
- `bash scripts/rc29_release_verify.sh`: PASS (full gates)

## Screenshot Evidence
- docs/evidence/ui/screenshots/rc52_1-hoch-pods-theater-current.png (current theater render)
- docs/evidence/ui/screenshots/hoch-pods-theater-reference-vs-current.png (side-by-side)
- docs/evidence/ui/screenshots/hoch-pods-theater-cockpit-current.png

## Visual Drift Finding
No drift. The rendered browser at http://127.0.0.1:8765/ uses `docs/design/assets/hoch-pods-theater-reference.jpeg` as the base-shell (200 OK, SHA256 c186e1f1..., THEME_COMPLIANCE PASS across all 17 frames, IDs, layout, stale-safe mapping). The `a_wide_high_detail_ui_dashboard_screenshot_conc.png` is a separate earlier control-plane screenshot and was never the theater shell authority. All tests, compliance scripts, evidence, and HTML consistently reference the correct dedicated theater reference image. Previous concern was a naming mix-up between prototype screenshot and production theater shell; resolved by inventory and live verification.

## Evidence Path
docs/evidence/ui/hoch-pods-visual-baseline-authority.md

## Remaining Blockers
None

## Single Next Operator Command
open docs/evidence/ui/hoch-pods-visual-baseline-authority.md