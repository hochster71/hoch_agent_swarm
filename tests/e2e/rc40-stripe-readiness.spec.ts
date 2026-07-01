import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('RC40 Stripe Sandbox Readiness E2E tests', () => {
  const envPath = path.join(__dirname, '../../.env.stripe.sandbox');

  test.afterEach(async () => {
    // Clean up mock file after each test to maintain clean workspace
    if (fs.existsSync(envPath)) {
      fs.unlinkSync(envPath);
    }
  });

  test('validates Stripe Sandbox MISSING, INVALID, and PRESENT flow', async ({ page }) => {
    // Ensure mock file starts as clean/missing
    if (fs.existsSync(envPath)) {
      fs.unlinkSync(envPath);
    }

    // 1. Validate MISSING state
    await page.goto('http://127.0.0.1:8765/');
    const stripeStateEl = page.locator('#stripe-sandbox-state');
    await expect(stripeStateEl).toBeVisible();
    await expect(stripeStateEl).toContainText('MISSING');
    
    // Capped at 50.0% of evidence coverage (100% * 0.5)
    const monetizationScoreEl = page.locator('#monetization-score');
    await expect(monetizationScoreEl).toContainText('50%');

    // 2. Validate PRESENT state
    fs.writeFileSync(envPath, `
STRIPE_MODE=sandbox
STRIPE_ACCOUNT_EMAIL=michael.b.hoch@gmail.com
STRIPE_PUBLISHABLE_KEY=pk_test_mockpublishablekey123
STRIPE_SECRET_KEY=sk_test_mocksecretkey456
    `.trim());

    // Wait for reload
    await page.reload();
    await expect(stripeStateEl).toContainText('PRESENT');
    // Not capped anymore: should show 100.0%
    await expect(monetizationScoreEl).toContainText('100%');

    // 3. Validate INVALID state (live key blocking check)
    fs.writeFileSync(envPath, `
STRIPE_MODE=sandbox
STRIPE_ACCOUNT_EMAIL=michael.b.hoch@gmail.com
STRIPE_PUBLISHABLE_KEY=pk_live_mocklivepublishablekey123
STRIPE_SECRET_KEY=sk_live_mocklivesecretkey456
    `.trim());

    await page.reload();
    await expect(stripeStateEl).toContainText('INVALID');
    // Capped at 50.0% again
    await expect(monetizationScoreEl).toContainText('50%');
  });
});
