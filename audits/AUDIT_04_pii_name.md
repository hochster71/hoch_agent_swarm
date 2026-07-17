# AUDIT 04 — PII / Founder Name Removal (Epic Fury 2026)

**Scope:** `audits/epic-fury-src` — web app (`app/`, `components/`, `lib/`, `public/`) + App Store metadata (`metadata/en-US/*.txt`).
**Mode:** READ-ONLY. No files modified/deployed. NO FAKE GREEN.
**Goal:** Remove the founder's personal NAME and personal identifiers from all user-facing surfaces, while KEEPING the anonymized credential framing ("a retired U.S. Navy LCDR, 31 years, Surface Warfare").
**Date:** 2026-07-16

> Note: the app already ships the desired anonymized framing in several places (promo text, release notes, support "About the Developer", `page.tsx` operator doctrine, `NexusDoctrinePanel`). Those carry NO personal name and are the target end-state — they are listed below as COMPLIANT, keep as-is. Only the items in the "MUST FIX" table leak the name / a personal identifier.

---

## A. USER-FACING — MUST REMOVE / ANONYMIZE

### A1. Hard name in App Store description
| # | File:Line | Exact text (excerpt) | Issue |
|---|-----------|----------------------|-------|
| 1 | `metadata/en-US/description.txt:5` | `Michael Hoch served 31 years as a U.S. Navy Mustang — enlisted to officer — retiring as a Lieutenant Commander (O-4), Surface Warfare Officer and Limited Duty Officer in Surface Operations. From the Persian Gulf to the Red Sea, from 1988 to 2019, he lived the operational realities that this app tracks in real time.` | Full personal NAME on the public App Store listing. |

**Proposed replacement (preserves credential, drops name & pinpoint 1988–2019 dates that re-identify):**
> `The developer served 31 years in the U.S. Navy as a Mustang — enlisted to officer — retiring as a Lieutenant Commander (O-4), Surface Warfare Officer and Limited Duty Officer in Surface Operations. From the Persian Gulf to the Red Sea, across three decades of service, they lived the operational realities that this app tracks in real time.`

*(Header line 1 "BUILT BY A COMBAT-SEASONED NAVAL OFFICER" and line 47 "31 years of operational naval experience" contain no name — keep.)*

### A2. Personal email (name embedded in `michael.b.hoch@gmail.com`) — public support/legal pages
| # | File:Line | Exact text | Issue |
|---|-----------|-----------|-------|
| 2 | `app/support/page.tsx:27` | `href="mailto:michael.b.hoch@gmail.com"` | Personal Gmail (contains name) shown as support contact. |
| 3 | `app/support/page.tsx:30` | `michael.b.hoch@gmail.com` (visible link text) | Same, rendered on-page. |
| 4 | `app/support/page.tsx:83` | `href="mailto:michael.b.hoch@gmail.com"` | Same. |
| 5 | `app/support/page.tsx:86` | `michael.b.hoch@gmail.com` (visible link text) | Same. |
| 6 | `app/terms/page.tsx:84` | `<a href="mailto:michael.b.hoch@gmail.com" ...>michael.b.hoch@gmail.com</a>` | Personal Gmail in Terms of Service. |
| 7 | `app/refund/page.tsx:19` | `const SUPPORT_EMAIL = 'michael.b.hoch@gmail.com'` | Personal Gmail constant, rendered at lines 65/84/111 of Refund page. |

**Proposed replacement for #2–#7:** replace every `michael.b.hoch@gmail.com` with a neutral role address on the domain the app already uses for privacy —
> `support@epicfury.app`

*(The privacy page already uses `privacy@epicfury.app` — a neutral, no-name mailbox — so this is consistent. One edit in `refund/page.tsx` (the `SUPPORT_EMAIL` const) covers all three refund-page instances; support page has 2 distinct addresses × 2 lines each; terms has 1.)*

---

## B. USER-FACING — COMPLIANT (already anonymized, KEEP AS-IS)

These carry the credential positioning with NO personal name — this is the desired framing; no action needed, listed for completeness.

| File:Line | Text | Note |
|-----------|------|------|
| `metadata/en-US/promotional_text.txt:1` | "Built by a retired U.S. Navy LCDR with 31 years of Surface Warfare experience..." | Anonymized — keep. |
| `metadata/en-US/release_notes.txt:1` | "...built by a retired U.S. Navy Surface Warfare LCDR with 31 years of operational experience." | Anonymized — keep. |
| `metadata/en-US/description.txt:1` | "BUILT BY A COMBAT-SEASONED NAVAL OFFICER. POWERED BY AI." | No name — keep. |
| `app/support/page.tsx:97-98` | "...built by a retired U.S. Navy Lieutenant Commander with 31 years of Surface Warfare experience..." (About the Developer) | No name — keep. |
| `app/page.tsx:20-27` | `OPERATOR_DOCTRINE`: "31 Years Naval Operations", "Joint Information Control Officer", "LDO Surface Line Operations 6120", "E-1 to E-9 Master Chief Operations Specialist" | No name — keep. (Detailed rank/rate ladder is identifying-adjacent but carries no name; flag as optional trim if founder wants lower re-identification risk.) |
| `components/NexusDoctrinePanel.tsx:9` | "31 years of Naval service translated into repeatable decision rhythm..." | No name — keep. |

---

## C. INTERNAL — NOTED, NOT USER-FACING (lower priority)

Not rendered to end users / App Store visitors. Flagged for hygiene only; not required for the name-removal goal.

| File:Line | Text | Classification |
|-----------|------|----------------|
| `lib/entitlements.ts:14` | `"michael.b.hoch@gmail.com";` (admin/founder allowlist default) | INTERNAL — functional server-side allowlist. Personal email hardcoded in shipped bundle. Recommend moving to an env var (e.g. `ADMIN_EMAIL`) rather than literal, but not user-visible. |
| `lib/entitlements.ts:50` | `if (adminEmails.includes(email) || email === "michael.b.hoch@gmail.com")` | INTERNAL — same allowlist logic. |
| `lib/access-control.ts:10` | `*   'admin'      — owner only (michael.b.hoch@gmail.com)` | INTERNAL — code comment. |
| `lib/autonomous-engine.ts:19` | `*   GITHUB_REPO_OWNER  — e.g. hochster71` | INTERNAL — code comment (GitHub handle example). |
| `.env.example:38` | `# GITHUB_REPO_OWNER=hochster71` | INTERNAL — env template example (GitHub handle). |

*(No occurrences of a first-person Navy bio ("I served…"), "hochster_71", or the name "Hoch" outside the items above were found anywhere in `app/`, `components/`, `lib/`, `public/`, or `metadata/`.)*

---

## D. SUMMARY

- **User-facing name/identifier leaks to fix: 7 instances across 4 files** — 1 hard name (App Store description) + 6 personal-email renderings (support ×4, terms ×1, refund const ×1).
- **Single clean fix path:** rewrite `description.txt:5` (name → "The developer"), and replace `michael.b.hoch@gmail.com` → `support@epicfury.app` everywhere it is user-facing.
- **Credential positioning is preserved** in all cases and already exists name-free elsewhere — nothing about "retired U.S. Navy LCDR / 31 years / Surface Warfare" is removed.
- **Internal identifiers (5)** are code comments / allowlist config / env examples — noted, not required for this goal; the `entitlements.ts` hardcoded admin email is the one worth moving to an env var on hygiene grounds.
