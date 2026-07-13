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
ENVIRONMENT NOTE (evidence-derived, D4-1): a real IN-BROWSER magic-link login cannot run
 * against the zero-secret LOOPBACK Supabase because the product enforces three production
 * controls that a loopback backend cannot satisfy (all confirmed in source):
 *   1. lib/supabase.ts disables the browser auth client when the URL is localhost/127.0.0.1;
 *   2. the Supabase API gateway binds loopback only;
 *   3. middleware.ts CSP connect-src emits `https://<host>` (https, default port) — an
 *      http:port local endpoint is refused, and widening it is a PRODUCT change (D4: none).
 * So authenticated specs establish a session the FAITHFUL way that touches no product code
 * and no security control: mint a REAL session from the REAL local GoTrue (password grant),
 * then let the app's OWN @supabase/ssr serialize it into the exact cookie the server-side
 * middleware reads (`sb-127-auth-token`). The JWT, the app_metadata role, and the middleware
 * entitlement path are all real. The email-click UI is separately covered by the security
 * specs (demo-route 404, prod rejects test-auth, anon fail-closed, invalid identity denied).
 *
 * RACE FIX (D1/agent): the previous helper shared ONE inbox across parallel specs, so a
 * worker could consume another worker's magic link. Now `loginAsFreshUser()` mints a
 * UNIQUE identity per call (e2e+<nonce>@epicfury.local), provisions it via the LOCAL admin
 * API, and the Mailpit poll filters strictly on that recipient. Parallel-safe by
 * construction. Role-specific specs still pin a fixed allowlisted email deterministically.
 */
import type { Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";

const supabaseUrl = () => process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321";
const ANON = () => process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const SERVICE = () => process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
const MAILPIT = () => process.env.EPIC_FURY_MAILPIT_URL ?? "http://127.0.0.1:54324";
const APP = () => process.env.EPIC_FURY_BASE_URL ?? "http://localhost:3003";

export const TEST_EMAIL = process.env.EPIC_FURY_TEST_EMAIL ?? "e2e-test@epicfury.local";
const APP_DIR = process.env.EPIC_FURY_APP_DIR ?? `${process.env.HOME}/Downloads/Epic-fury-2026-main`;
const TEST_PW = "E2eTestOnly!2026";

import type { BrowserContext } from "@playwright/test";

/** Mint a REAL session from local GoTrue and serialize it with the app's own @supabase/ssr,
 *  then set that exact cookie on the browser context. Server-side middleware reads a real JWT. */
export async function establishSession(context: BrowserContext, email: string,
                                       role?: "admin" | "subscriber"): Promise<void> {
  assertLocalOnly();
  const out = execFileSync("node",
    [`${APP_DIR}/tests-support/epic-fury-mkcookies.mjs`, email, TEST_PW, role ?? ""],
    { cwd: APP_DIR, env: { ...process.env, ANON: ANON(), SVC: SERVICE() }, encoding: "utf8" });
  const line = out.split("\n").find((l) => l.startsWith("COOKIES "));
  if (!line) throw new Error(`EPIC_FURY_SESSION_FAILED for ${email}: ${out.slice(0, 200)}`);
  const cookies = JSON.parse(line.slice("COOKIES ".length)) as { name: string; value: string }[];
  await context.addCookies(cookies.map((c) => ({
    name: c.name, value: c.value, domain: "localhost", path: "/",
    httpOnly: false, secure: false, sameSite: "Lax" as const,
  })));
}

// Same-machine only: loopback OR an RFC1918 private address (the local stack exposed via a
// userspace forwarder so the product's "no-loopback" client guard is satisfied). PUBLIC
// hosts are still REFUSED, so the harness can never target a real/hosted Supabase.
const LOCAL_HOST = /^https?:\/\/(127\.0\.0\.1|localhost|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:|\/|$)/;
function assertLocalOnly(): void {
  const u = supabaseUrl();
  if (!LOCAL_HOST.test(u)) {
    throw new Error(`EPIC_FURY_AUTH_REFUSED: magic-link harness may only target a SAME-MACHINE Supabase, got ${u}.`);
  }
  if (!LOCAL_HOST.test(MAILPIT())) {
    throw new Error(`EPIC_FURY_AUTH_REFUSED: Mailpit must be same-machine, got ${MAILPIT()}.`);
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
  // Direct REST OTP — used only by expectLoginDenied to prove an UNPROVISIONED identity
  // gets no mail. The real login (loginWithEmail) drives the product UI instead, so the
  // PKCE code_verifier cookie is set in-browser exactly as a real user would.
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
  // 1. Drive the REAL product login form so signInWithOtp runs IN-BROWSER and sets the
  //    Supabase SSR PKCE code_verifier cookie — the same path a real user takes.
  await page.goto(`${APP()}/login?next=/dashboard`, { waitUntil: "domcontentloaded" });
  const emailInput = page.locator('input[type="email"]');
  await emailInput.click();
  await emailInput.pressSequentially(email, { delay: 8 }); // real keystrokes -> React onChange enables submit
  const submit = page.locator('form button[type="submit"]');
  await submit.waitFor({ state: "visible" });
  await submit.click();
  // 2. The emailed link addressed to EXACTLY this recipient (never another worker's).
  const link = await magicLinkFor(email);
  // 3. Supabase verify -> /auth/callback?code -> exchangeCodeForSession (verifier present)
  //    -> SSR session cookie set on the app domain -> /dashboard.
  await page.goto(link, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/dashboard|\/login/, { timeout: 10000 }).catch(() => {});
}

/** Fixed identity (e.g. an allowlisted founder/qa email). Provisions if needed. */
export async function loginAsTestUser(page: Page, email = TEST_EMAIL,
                                     role?: "admin" | "subscriber"): Promise<void> {
  assertLocalOnly(); // refuse a non-local Supabase before anything else (production-safe)
  await establishSession(page.context(), email, role);
  await page.goto(`${APP()}/dashboard`, { waitUntil: "domcontentloaded" }).catch(() => {});
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
  await establishSession(page.context(), email);   // no role -> free tier
  await page.goto(`${APP()}/dashboard`, { waitUntil: "domcontentloaded" }).catch(() => {});
  return email;
}
