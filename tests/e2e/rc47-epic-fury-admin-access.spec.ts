import { test, expect } from '@playwright/test';
import { loginAsTestUser } from '../support/epic-fury-auth';
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

  test('2. Founder can access dashboard and view internal preview banner', async ({ page }) => {
    // Real magic-link auth as the FOUNDER-allowlisted identity (no demo bypass).
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com');
    await page.goto('http://localhost:3003/dashboard');
    
    // Check that internal preview banner is visible with correct source
    const banner = page.locator('#internal-access-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('Internal Preview Mode');
    await expect(banner).toContainText('Source: founder_override');
  });

  test('3. QA user can access dashboard and view internal preview banner', async ({ page }) => {
    // Real magic-link auth as the QA-allowlisted identity (no demo bypass).
    await loginAsTestUser(page, 'qa@example.com');
    await page.goto('http://localhost:3003/dashboard');
    
    const banner = page.locator('#internal-access-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('Source: internal_preview');
  });

  test('4. Admin control panel (/admin) renders diagnostics safely', async ({ page }) => {
    // Real magic-link auth as the founder/admin-allowlisted identity.
    await loginAsTestUser(page, 'michael.b.hoch@gmail.com');
    await page.goto('http://localhost:3003/dashboard');
    
    // Navigate to /admin
    await page.goto('http://localhost:3003/admin');
    
    // Verify headings
    await expect(page.locator('h1:has-text("Epic Fury Admin Control")')).toBeVisible();
    await expect(page.locator('h2:has-text("Environment Diagnostics")')).toBeVisible();
    await expect(page.locator('h2:has-text("Authenticated User Session")')).toBeVisible();
    
    // Verify user details
    await expect(page.locator('text=michael.b.hoch@gmail.com').first()).toBeVisible();
    await expect(page.locator('text=founder').first()).toBeVisible();
    
    // Verify Stripe credentials are not exposed
    const stripeText = await page.locator('text=Stripe API Status').locator('xpath=../p').innerText();
    expect(stripeText).not.toContain('sk_');
  });
});
