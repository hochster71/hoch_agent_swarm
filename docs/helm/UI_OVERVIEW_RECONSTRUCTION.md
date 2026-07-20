# HELM Executive Operations Center — visual reconstruction vs reference

**Pass (2026-07-17, Builder/Claude).** `/`, `/hub`, `/overview` now serve a componentized
reconstruction of the authoritative reference PNG (1536×1024). Runtime APIs, routes, and truth
semantics are unchanged — only the visual layer was rebuilt.

## What was reproduced (per the reference composition)
Left nav rail (brand + 13 nav items + SYSTEM HEALTH card w/ sparkline + RUNTIME TRUTH card w/ dot
row) · executive header (greeting, HELM CORE / constitutional-status card, GOAL REACHED card,
date-time-weather card) · MISSION STATUS with dominant circular gauge + checklist · full-width
CRITICAL PATH / PERT node walk · FOUNDER DECISIONS · FAMILY / HOME / FINANCE / CYBERSECURITY /
EVENTS & ALERTS domain row · AI RESOURCES (frontier | local split) · FACTORIES · EXECUTIVE BRIEF
SUMMARY · RECOMMENDED NEXT ACTION · governance footer rail · centered slogan
**ONE GOAL. ONE TRUTH. ONE SYSTEM. VERIFIED. GOVERNED. OPERATIONAL.**

Component CSS blocks map 1:1 to the requested names (HelmSidebar, HelmExecutiveHeader,
HelmGoalStatus, HelmMissionStatus, HelmCriticalPath, HelmFounderDecisions, HelmFamilyCard,
HelmHomeCard, HelmFinanceCard, HelmCyberCard, HelmEventsPanel, HelmAIResources, HelmFactories,
HelmExecutiveSummary, HelmRecommendedAction, HelmGovernanceRail).

Style system honored: near-black-navy bg with cyan radial atmospheric glow; dark blue-black
panels, 1px blue-gray border, 14px radius, inner highlight, cyan glow only on high-value panels
(HELM CORE, GOAL, RECOMMENDED); technical sans typography with uppercase expanded-tracking
micro-labels and oversized numeric values; the full semantic palette (cyan/green/amber/red/
purple/blue/gray). 12-column grid, desktop-first 1536×1024, degrades at 1280 and stacks below 820.

## Runtime-truth honesty (NO FAKE GREEN)
The reference shows illustrative personal data (Alison/dentist, HVAC, "2 Bills Due", etc.). Those
are **not** reproduced as values. HELM has no family/home/finance source, so **FAMILY, HOME, and
FINANCE render `NOT CONNECTED`** with a "connect source" affordance. Everything else binds to live
endpoints (`/executive-brief`, `/goal-pert`, `/council/status`, `/council/activity`, `/factories`)
and renders `UNKNOWN` / `UNVERIFIED` when a field is absent. VERIFIED-green appears only where the
runtime truth supports it (e.g. GOAL% from goal-pert, node DONE counts, lane readiness).

## Development overlay
`/overview?referenceOverlay=1` overlays the reference PNG above the implementation, opacity slider
0–100 %, **O** toggles it, control chip bottom-right. Not present in production nav. Requires the
PNG at `frontend_live/ref_overview.png` (served by the dev-only `/ref_overview.png` route).

## Visual-diff test
`tests/ui/test_overview_visual.py` (Playwright + Pillow) captures the reconstruction at 1536×1024
and, when the reference PNG is present, writes `overview_sidebyside.png`, an amplified
`overview_diff.png`, and `overview_diff.json` (mean/max diff, % differing pixels). Runs on the
machine hosting the live API; skips honestly if server or reference is absent.

## Remaining deviations (documented, not hidden)
1. **Reference PNG not embedded in this repo.** The image lives in the chat upload, not the
   sandbox filesystem, so it could not be copied in automatically. The overlay + diff activate the
   moment the PNG is placed at `frontend_live/ref_overview.png`. Until then the overlay 404s
   (by design) and the Playwright test captures the actual only, then SKIPS the diff.
2. **No auto-run side-by-side yet.** Because the live API runs on Michael's Mac (not the sandbox),
   the screenshot + diff must be produced there (`pytest tests/ui/test_overview_visual.py -s`).
   The <5%-geometry acceptance number can only be certified after that run — not claimed here.
3. **Weather card** shows `weather not connected` (no weather source wired) rather than the
   reference's "75°F Clear". Time/date are real (client clock).
4. **`/factories` drill-down** is still task #63 (pending); the nav link resolves to it once built.
   All other reference nav routes are live.
5. **Icons** are Unicode/inline-SVG glyphs approximating the reference's icon set, not a licensed
   icon font — visually equivalent, not pixel-identical.
6. **Founder-decision copy** (priority/created/impact lines) binds to whatever the brief exposes;
   where the brief lacks those fields it shows owner/status rather than inventing HIGH/dates.

## Acceptance-criteria status
Reproduced geometry & hierarchy ✓ · componentized ✓ · semantic colors truth-bound ✓ · no fake
family/finance/home/cyber values ✓ · existing routes/tests functional ✓ · overlay dev mode ✓ ·
Playwright screenshot+diff test generated ✓ · **side-by-side ≤5% geometry certification: PENDING
the on-machine test run with the reference PNG in place.**
