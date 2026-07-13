/**
 * Epic Fury e2e authentication — REAL magic-link flow. No bypass. No demo route.
 *
 * FOUNDER CONTRACT (2026-07-12/13):
 *   - /api/auth/demo is NOT restored and must stay 404.
 *   - Tests authenticate through the product's actual supported boundary:
 *       POST /auth/v1/otp -> Mailpit captures the mail -> open the verify link ->
 *       /auth/callback establishes the Supabase SSR session.
 *   - Test-only ONLY by environment: a LOCAL Supabase (127.0.0.1) + LOCAL mail sink.
 *     assertLocalOnly() REFUSES any other target, so the harness cannot point at prod.
 *   - No credential, token, cookie, or key is ever committed. All read from env.
 *
 * RACE FIX (D1/agent): the previous helper shared ONE inbox across parallel specs, so a
 * worker could consume another worker's magic link. Now `loginAsFreshUser()` mints a
 * UNIQUE identity per call (e2e+<nonce>@epicfury.local), provisions it via the LOCAL admin
 * API, and the Mailpit poll filters strictly on that recipient. Parallel-safe by
 * construction. Role-specific specs still pin a fixed allowlisted email deterministically.
 */
import type { Page } from "@playwright/test";
import { randomUUID } from "node:crypto";

const supabaseUrl = () => process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321";
const ANON = () => process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const SERVICE = () => process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
const MAILPIT = () => process.env.EPIC_FURY_MAILPIT_URL ?? "http://127.0.0.1:54324";
const APP = () => process.env.EPIC_FURY_BASE_URL ?? "http://localhost:3003";

export const TEST_EMAIL = process.env.EPIC_FURY_TEST_EMAIL ?? "e2e-test@epicfury.local";

function assertLocalOnly(): void {
  const u = supabaseUrl();
  if (!/^https?:\/\/(127\.0\.0\.1|localhost)/.test(u)) {
    throw new Error(`EPIC_FURY_AUTH_REFUSED: magic-link harness may only target a LOCAL Supabase, got ${u}.`);
  }
  if (!/^https?:\/\/(127\.0\.0\.1|localhost)/.test(MAILPIT())) {
    throw new Error(`EPIC_FURY_AUTH_REFUSED: Mailpit must be local, got ${MAILPIT()}.`);
  }
}

async function provisionUser(email: string, role?: "admin" | "subscriber"): Promise<void> {
  // LOCAL admin API, local service key from env. Never committed. The live app reads
  // entitlement from app_metadata.role (middleware.getUserRole) -- so a role-scoped test
  // identity gets exactly its intended permission and nothing broader.
  const app_metadata = role ? { role } : undefined;
  await fetch(`${supabaseUrl()}/auth/v1/admin/users`, {
    method: "POST",
    headers: { apikey: SERVICE(), authorization: `Bearer ${SERVICE()}`, "content-type": "application/json" },
    body: JSON.stringify({ email, password: `E2e-${randomUUID()}`, email_confirm: true, app_metadata }),
  }).catch(() => {});
  // if it already existed, PATCH the role so entitlement is deterministic
  if (role) {
    // GoTrue admin list supports ?filter= on email; fall back to scanning pages.
    const list = await (await fetch(`${supabaseUrl()}/auth/v1/admin/users?per_page=200`, {
      headers: { apikey: SERVICE(), authorization: `Bearer ${SERVICE()}` } })).json().catch(() => ({}));
    const u = (list.users ?? []).find((x: any) => (x.email ?? "").toLowerCase() === email.toLowerCase());
    if (u) await fetch(`${supabaseUrl()}/auth/v1/admin/users/${u.id}`, {
      method: "PUT",
      headers: { apikey: SERVICE(), authorization: `Bearer ${SERVICE()}`, "content-type": "application/json" },
      body: JSON.stringify({ app_metadata: { role } }) }).catch(() => {});
  }
}

async function requestOtp(email: string): Promise<void> {
  const r = await fetch(`${supabaseUrl()}/auth/v1/otp`, {
    method: "POST",
    headers: { apikey: ANON(), "content-type": "application/json" },
    body: JSON.stringify({ email, create_user: false }),
  });
  if (!r.ok) throw new Error(`OTP request failed for ${email}: HTTP ${r.status}`);
}

/** The magic link addressed to EXACTLY this recipient — never another worker's. */
async function magicLinkFor(email: string, timeoutMs = 15000): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const list = await (await fetch(`${MAILPIT()}/api/v1/search?query=${encodeURIComponent("to:" + email)}&limit=5`)).json();
    for (const msg of list.messages ?? []) {
      if (((msg.To ?? [])[0]?.Address ?? "").toLowerCase() !== email.toLowerCase()) continue;
      const body = await (await fetch(`${MAILPIT()}/api/v1/message/${msg.ID}`)).text();
      const m = body.match(/https?:\/\/[^\s"'<>]+auth\/v1\/verify[^\s"'<>]*/) ??
                body.match(/https?:\/\/127\.0\.0\.1[^\s"'<>]+token[^\s"'<>]*/);
      if (m) return m[0].replace(/&amp;/g, "&");
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`no magic link arrived for ${email} within ${timeoutMs}ms`);
}

async function loginWithEmail(page: Page, email: string): Promise<void> {
  assertLocalOnly();
  await requestOtp(email);
  const link = await magicLinkFor(email);
  await page.goto(link, { waitUntil: "domcontentloaded" });
  await page.goto(`${APP()}/dashboard`, { waitUntil: "domcontentloaded" }).catch(() => {});
}

/** Fixed identity (e.g. an allowlisted founder/qa email). Provisions if needed. */
export async function loginAsTestUser(page: Page, email = TEST_EMAIL,
                                     role?: "admin" | "subscriber"): Promise<void> {
  assertLocalOnly();
  await provisionUser(email, role);
  await loginWithEmail(page, email);
}

/** Attempt login for an identity that is NOT provisioned. Must FAIL (no mail sent). */
export async function expectLoginDenied(email: string): Promise<void> {
  assertLocalOnly();
  await requestOtp(email);            // create_user:false -> unknown email -> no mail
  await magicLinkFor(email, 3000);    // throws "no magic link arrived"
}

/** UNIQUE per call. Use where the test only needs "some authenticated user". Race-proof. */
export async function loginAsFreshUser(page: Page, slug = "u"): Promise<string> {
  assertLocalOnly();
  const email = `e2e+${slug}-${randomUUID().slice(0, 8)}@epicfury.local`;
  await provisionUser(email);
  await loginWithEmail(page, email);
  return email;
}
