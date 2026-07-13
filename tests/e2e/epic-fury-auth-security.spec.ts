import { test, expect, request } from '@playwright/test';
import { loginAsTestUser, expectLoginDenied, TEST_EMAIL } from '../support/epic-fury-auth';

/**
 * REQ-CP-TEST security regression — proves the production authentication boundary is
 * fail-closed and that NO test-only mechanism can be enabled in production.
 *
 * FOUNDER CONTRACT: /api/auth/demo must NOT exist; the magic-link test harness must be
 * impossible against a production Supabase; entitlement must default-deny.
 */
const APP = 'http://localhost:3003';

test.describe('Epic Fury auth security regression', () => {
  test('1. /api/auth/demo returns 404 (the bypass is gone)', async () => {
    const ctx = await request.newContext();
    const r = await ctx.get(`${APP}/api/auth/demo?email=michael.b.hoch@gmail.com&role=admin`);
    expect(r.status()).toBe(404);
  });

  test('2. a test-auth flag cannot enable a bypass route', async () => {
    const ctx = await request.newContext({ extraHTTPHeaders: { 'x-test-auth': '1' } });
    const r = await ctx.get(`${APP}/api/auth/demo?email=michael.b.hoch@gmail.com&role=admin`);
    expect(r.status()).toBe(404); // no header resurrects the removed route
  });

  test('3. the magic-link harness REFUSES a non-local Supabase (production-safe)', async () => {
    // The guard reads SUPABASE_URL at call time. Point it at a production-looking host
    // and confirm the harness refuses to run -- proving it cannot be used against prod.
    const prev = process.env.NEXT_PUBLIC_SUPABASE_URL;
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://real-project.supabase.co';
    try {
      await expect(loginAsTestUser({ goto: async () => {} } as any))
        .rejects.toThrow(/EPIC_FURY_AUTH_REFUSED/);
    } finally {
      process.env.NEXT_PUBLIC_SUPABASE_URL = prev;
    }
  });

  test('4. test-environment authorized identity CAN log in (real flow)', async ({ page }) => {
    await loginAsTestUser(page, TEST_EMAIL);
    await page.goto(`${APP}/dashboard`);
    expect(page.url()).toContain('/dashboard');
  });

  test('5. an invalid identity is DENIED', async ({ page }) => {
    await expect(expectLoginDenied('nobody-unknown-' + Date.now() + '@epicfury.local'))
      .rejects.toThrow(/no magic link arrived|OTP request failed/i);
  });

  test('6. unauthenticated dashboard access is entitlement-fail-closed', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto(`${APP}/dashboard`);
    // fail-closed: the paid content is gated behind the upgrade wall for the anon user
    await expect(page.locator('text=Unlock Full Intelligence Access')).toBeVisible({ timeout: 15000 });
  });

  test('7. a plain test identity cannot reach admin-only surface', async ({ page }) => {
    await loginAsTestUser(page, TEST_EMAIL);            // NOT on the founder allowlist
    await page.goto(`${APP}/admin`);
    // the generic test identity is not admin -> must not see admin diagnostics
    await expect(page.locator('text=Internal Preview Mode')).toHaveCount(0);
  });
});
