# Epic Fury 2026 — Founder Submission Checklist (the 3 founder-gated milestones)

The champion gate honestly reports `TESTFLIGHT` and `APP_STORE_CONNECT` as **UNKNOWN**,
and `REQ-TO-002` (ships to production) as unmet, because the truth lives in App Store
Connect — not in any local file. A JSON asserting success is NOT evidence. To turn these
green *honestly*, two things have to happen, split by who can do them.

## Current state (verified 2026-07-15)
- ✅ Paperwork gates PASS: SIGNING_READINESS, STORE_METADATA, PRIVACY, MONETIZATION,
  SUBMISSION_PACKAGE (all release docs + founder release decision present).
- ✅ ASC API credentials are PROVISIONED in the launchd env
  (`APP_STORE_CONNECT_KEY_ID`, `ASC_API_KEY`, `APP_STORE_CONNECT_ISSUER_ID`) — so HELM
  *can* read live state once the read is implemented.
- ❌ No build uploaded (no `.ipa`/`.xcarchive` in the tree; nothing in TestFlight).
- ⏳ Validator does not yet call App Store Connect — it returns UNKNOWN, correctly, until
  a live read exists.

## Part A — YOURS to do (Xcode + App Store Connect; Claude cannot sign or submit)
1. **Archive the build** in Xcode: Product → Archive (Release config, distribution cert +
   provisioning profile — SIGNING_READINESS already approved).
2. **Upload to App Store Connect** (Organizer → Distribute App → App Store Connect, or
   `xcrun altool`/Transporter). This creates the build TestFlight reads.
3. **TestFlight**: in App Store Connect → your app → TestFlight, confirm the build
   processed, add it to an internal (and/or external) test group, add at least one tester.
   → this is what makes `CP-TESTFLIGHT` a real, readable state.
4. **Submit for review**: App Store Connect → your app → the version → attach the build →
   Submit for Review (metadata/privacy/pricing already DONE per the passing gates).
   → this is what makes `CP-APP_STORE_CONNECT` a real, readable state.
5. Wait for Apple to process/approve → `REQ-TO-002` (ships to production) becomes true when
   the app is actually live / released.

## Part B — AGENT-actionable (optional, HELM verifies instead of guessing)
Right now the gate can never leave UNKNOWN because nothing reads App Store Connect. Since
the ASC credentials are already provisioned, Claude can implement a **live ASC read** in
`scripts/goal/verify_champion_gates.py`:
- Sign a JWT with the `.p8` key (App Store Connect API auth) — Claude writes the code;
  it uses the launchd-provided creds at runtime and **never sees the secret values**.
- Query the ASC API for the app's build/TestFlight state and app-version review state.
- The gate then reports the REAL state (PASS / rejected / in-review), fail-closed to
  UNKNOWN on any error — no fabricated green.
This turns TESTFLIGHT/APP_STORE_CONNECT from "UNKNOWN forever" into "verified from Apple"
once you complete Part A. It makes real network calls to Apple with your credentials, so
it's built only on your say-so.

## Order that makes sense
Do Part A steps 1–2 (get a build up) → have Claude build Part B (the ASC read) → do Part A
3–4 (TestFlight + submit) → re-run `verify_champion_gates.py`, which now reads Apple and
flips the gates on real evidence.
