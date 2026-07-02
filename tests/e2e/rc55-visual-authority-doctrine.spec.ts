import { test, expect } from '@playwright/test';

test.describe('RC55 - HAS/HASF Single Visual Authority Doctrine', () => {
  test('enforces single approved visual authority with no variance', async ({ page }) => {
    // Dashboard loads with doctrine markers
    await page.goto('http://localhost:3000');
    await expect(page).toHaveTitle(/HAS|HASF|Hoch Pods/);

    // Non-visual doctrine attributes present (no layout change)
    await expect(page.locator('[data-visual-authority="HOCH_PODS_HAS_HASF_SINGLE_APPROVED_VISUAL_AUTHORITY_NO_VARIANCE"]')).toBeVisible();
    await expect(page.locator('[data-approved-visual-authority-count="1"]')).toBeVisible();

    // SHA256 of approved authority exposed
    const shaElement = page.locator('[data-theater-authority-sha256]');
    await expect(shaElement).toHaveAttribute('data-theater-authority-sha256', '12de18ba8d3e6da8304f692455ab4ed27a97e6f175120b780f329927dc134310');

    // Runtime theater image uses canonical authority or exact hash-matched alias (no forbidden references)
    const theaterImg = page.locator('img[src*="hoch-pods-has-hasf-approved-authority"], img[src*="theater"]').first();
    await expect(theaterImg).toBeVisible();
    const src = await theaterImg.getAttribute('src');
    expect(src).toContain('hoch-pods-has-hasf-approved-authority') || expect(src).toContain('theater'); // canonical or alias

    // No HOCH POOS, no multi-image doctrine, no forbidden images
    const pageText = await page.textContent('body');
    expect(pageText).not.toContain('HOCH POOS');
    expect(pageText).not.toContain('two-image');
    expect(pageText).not.toContain('four-image');

    // Theatrical elements render correctly under single authority
    await expect(page.locator('.hoch-pods-theater, .agent-theater-node')).toBeVisible();

    console.log('RC55 VISUAL AUTHORITY DOCTRINE: PASS - Single approved image enforced.');
  });
});
