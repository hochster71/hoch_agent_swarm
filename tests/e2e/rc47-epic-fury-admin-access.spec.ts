import { test, expect } from '@playwright/test';
import { loginAsTestUser, loginAsFreshUser } from '../support/epic-fury-auth';
import { getEntitlement } from '../../../epic-fury-build/epic-fury-2026/lib/entitlements';
import * as fs from 'fs';
import * as path from 'path';

// ─── Group 1: Unit Tests for Entitlement Helper ──────────────────────────────

test.describe('RC47 Unit Tests: Entitlement Helper', () => {
  
  test('1. Unauthenticated public user receives no access', () => {
    // Reset environments
    delete process.env.EPIC_FURY_INTERNAL_PREVIEW_ENABLED;
    delete process.env.EPIC_FURY_STRIPE_TEST_MODE;

    const res = getEntitlement(null);
    expect(res).toEqual({
      hasAccess: false,
      role: 'public',
      mode: null,
    });
  });

  test('2. Founder email allowlist gets founder_override access', () => {
    process.env.EPIC_FURY_ADMIN_EMAILS = 'michael.b.hoch@gmail.com, admin@test.com';
    
    const res = getEntitlement({ email: 'michael.b.hoch@gmail.com' });
    expect(res).toEqual({
      hasAccess: true,
      role: 'founder',
      mode: 'founder_override',
    });
  });

  test('3. QA email allowlist gets internal_preview access', () => {
    process.env.EPIC_FURY_QA_EMAILS = 'qa@example.com, test-qa@test.com';
    
    const res = getEntitlement({ email: 'qa@example.com' });
    expect(res).toEqual({
      hasAccess: true,
      role: 'qa',
      mode: 'internal_preview',
    });
  });

  test('4. Stripe paid customer gets paid_customer access', () => {
    const res = getEntitlement({
      email: 'customer@example.com',
      app_metadata: { role: 'subscriber' }
    });
    expect(res).toEqual({
      hasAccess: true,
      role: 'public',
      mode: 'paid_customer',
    });
  });

  test('5. Stripe test mode customer gets stripe_test access', () => {
    process.env.EPIC_FURY_STRIPE_TEST_MODE = 'true';
    
    const res = getEntitlement({
      email: 'test@example.com',
      app_metadata: { stripe_customer_id: 'cust_test_123' }
    });
    expect(res).toEqual({
      hasAccess: true,
      role: 'public',
      mode: 'stripe_test',
    });
  });

  test('6. Fail-closed production default behavior', () => {
    process.env.NODE_ENV = 'production';
    process.env.EPIC_FURY_INTERNAL_PREVIEW_ENABLED = 'true'; // Should be ignored in production for non-allowlist
    
    const res = getEntitlement({
      email: 'unknown@example.com'
    });
    expect(res.hasAccess).toBe(false);
    
    // Restore node_env
    process.env.NODE_ENV = 'test';
  });
});

// ─── Group 2: E2E Integration Tests (Epic Fury dashboard) ────────────────────

test.describe('RC47 E2E Integration: Epic Fury Access Gates', () => {
  
  test.beforeEach(async ({ context }) => {
    // Clear demo user cookie before each test
    await context.clearCookies();
  });

  test('1. Public unpaid user is blocked by upgrade gate', async ({ page }) => {
    await page.goto('http://localhost:3003/dashboard');
    
    // Upgrade gate prompt should be visible
    const upgradeLink = page.locator('a[href="/upgrade"]');
    await expect(upgradeLink).toBeVisible();
    await expect(page.locator('text=Unlock Full Intelligence Access')).toBeVisible();
  });

  // D1 (founder-ratified 2026-07-13): the "Internal Preview Mode" banner was REMOVED from
  // the product. The old cases 2-4 asserted that removed UI and are RETIRED_AS_OBSOLETE.
  // Replaced with the CURRENT entitlement contract. No banner. No weakened authorization.

  test('2. Founder-allowlisted identity authenticates and reaches the dashboard (not upgrade-gated)', async ({ page }) => {
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com', 'admin');   // real magic-link, allowlisted
    await page.goto('http://localhost:3003/dashboard');
    expect(page.url()).toContain('/dashboard');
    // an entitled identity is NOT shown the public upgrade wall
    await expect(page.locator('text=Unlock Full Intelligence Access')).toHaveCount(0);
  });

  test('3. QA-allowlisted identity authenticates and reaches the dashboard', async ({ page }) => {
    await loginAsTestUser(page, 'qa@example.com', 'subscriber');             // real magic-link, QA-scoped
    await page.goto('http://localhost:3003/dashboard');
    expect(page.url()).toContain('/dashboard');
  });

  test('4. A plain authenticated identity is NOT granted founder/admin privileges', async ({ page }) => {
    const email = await loginAsFreshUser(page, 'rc47-plain');  // unique, non-allowlisted
    await page.goto('http://localhost:3003/admin');
    // the entitlement helper must not grant admin to a non-allowlisted identity:
    // no admin control surface, no founder role text.
    await expect(page.locator('h1:has-text("Epic Fury Admin Control")')).toHaveCount(0);
    await expect(page.locator('text=founder').first()).toHaveCount(0);
    expect(email).not.toContain('michael.b.hoch');
  });
});
