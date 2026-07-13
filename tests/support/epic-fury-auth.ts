/**
 * REQ-CP-TEST remediation — REAL authentication for Epic Fury e2e tests.
 *
 * FOUNDER CONTRACT (2026-07-12): do NOT restore /api/auth/demo. Authenticate through the
 * same supported boundary a real user uses. This module drives the ACTUAL magic-link flow:
 *
 *     POST /auth/v1/otp  →  Mailpit captures the email  →  open the verify link in the
 *     browser  →  /auth/callback establishes the Supabase SSR session cookie.
 *
 * No bypass. No demo route. The only thing that makes this test-only is the ENVIRONMENT:
 * a LOCAL Supabase (127.0.0.1:54321) with a LOCAL mail sink (Mailpit, 127.0.0.1:54324).
 * Neither exists in production. Production still requires a real inbox + real Supabase.
 *
 * Credentials are read from the environment (.env.local / CI secret store). Nothing here
 * commits a token, cookie, password, or key.
 */
import type { BrowserContext, Page } from "@playwright/test";

const currentSupabaseUrl = () => process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321";
const ANON = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const MAILPIT = process.env.EPIC_FURY_MAILPIT_URL ?? "http://127.0.0.1:54324";
const APP = process.env.EPIC_FURY_BASE_URL ?? "http://localhost:3003";

// A dedicated, non-production test identity. Created by the test setup, never a real user.
export const TEST_EMAIL = process.env.EPIC_FURY_TEST_EMAIL ?? "e2e-test@epicfury.local";

function assertLocalOnly() {
  // Refuse to run the magic-link harness against anything but a LOCAL Supabase. This is
  // the guard that makes the mechanism "impossible to enable in production".
  const SUPABASE_URL = currentSupabaseUrl();
  if (!/(^https?:\/\/(127\.0\.0\.1|localhost))/.test(SUPABASE_URL)) {
    throw new Error(
      `EPIC_FURY_AUTH_REFUSED: magic-link test harness may only target a LOCAL Supabase, ` +
        `got ${SUPABASE_URL}. Production auth must use a real inbox.`,
    );
  }
  if (!/(^https?:\/\/(127\.0\.0\.1|localhost))/.test(MAILPIT)) {
    throw new Error(`EPIC_FURY_AUTH_REFUSED: Mailpit must be local, got ${MAILPIT}`);
  }
}

async function requestOtp(email: string): Promise<void> {
  const r = await fetch(`${currentSupabaseUrl()}/auth/v1/otp`, {
    method: "POST",
    headers: { apikey: ANON, "content-type": "application/json" },
    body: JSON.stringify({ email, create_user: false }),
  });
  if (!r.ok) throw new Error(`OTP request failed: HTTP ${r.status}`);
}

async function latestMagicLink(email: string, timeoutMs = 15000): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const list = await (await fetch(`${MAILPIT}/api/v1/messages?limit=5`)).json();
    for (const msg of list.messages ?? []) {
      const to = (msg.To ?? [])[0]?.Address;
      if (to !== email) continue;
      const body = await (await fetch(`${MAILPIT}/api/v1/message/${msg.ID}`)).text();
      const m =
        body.match(/https?:\/\/[^\s"'<>]+auth\/v1\/verify[^\s"'<>]*/) ??
        body.match(/https?:\/\/127\.0\.0\.1[^\s"'<>]+token[^\s"'<>]*/);
      if (m) return m[0].replace(/&amp;/g, "&");
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("no magic link arrived in Mailpit within timeout");
}

/** Authenticate `page` as the test identity through the real magic-link flow. */
export async function loginAsTestUser(page: Page, email = TEST_EMAIL): Promise<void> {
  assertLocalOnly();
  await requestOtp(email);
  const link = await latestMagicLink(email);
  // Opening the verify link establishes the Supabase SSR session cookie via /auth/callback.
  await page.goto(link, { waitUntil: "domcontentloaded" });
  // land somewhere authenticated
  await page.goto(`${APP}/dashboard`, { waitUntil: "domcontentloaded" }).catch(() => {});
}

/** Save an authenticated storageState for reuse across specs. */
export async function establishSession(context: BrowserContext): Promise<void> {
  const page = await context.newPage();
  await loginAsTestUser(page);
  await page.close();
}
