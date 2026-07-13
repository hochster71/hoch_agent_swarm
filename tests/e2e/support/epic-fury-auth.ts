/**
 * Epic Fury 2026 — REAL authentication for e2e tests.
 *
 * FOUNDER DECISION (2026-07-12): /api/auth/demo must NOT be restored. The production app
 * keeps its fail-closed authentication and entitlement behaviour. Tests authenticate
 * through the SAME boundary a real user uses.
 *
 * WHAT THIS DOES
 *   1. asks Supabase for a magic link via the real /auth/v1/otp endpoint
 *   2. reads the resulting email out of the LOCAL mail sink (Mailpit)
 *   3. follows the link, so the app's own /auth/callback establishes the session
 *
 * There is no bypass. No test-only route. No forged cookie. No elevated privilege.
 * The only thing that differs from a human signing in is that the test can read its own
 * inbox -- which is possible only because the mail sink is a LOCAL container.
 *
 * ENVIRONMENT
 *   Requires a LOCAL Supabase stack (`supabase start`) -- 127.0.0.1:54321 + Mailpit
 *   127.0.0.1:54324. This is impossible to point at production:
 *     - MAIL_SINK_URL is loopback-only and asserted below
 *     - production has no local mail sink to read, so this fixture CANNOT authenticate
 *       against production even if someone pointed it there
 *
 * SECRETS
 *   Keys come from the environment (written by `supabase status -o env` into a
 *   gitignored