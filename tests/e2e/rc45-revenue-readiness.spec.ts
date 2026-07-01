import { test, expect } from '@playwright/test';

test.describe('RC45 Revenue Readiness E2E Tests', () => {
  test('1. Verify Revenue Readiness panel and project cards render correctly', async ({ page }) => {
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    
    // Navigate to PERT Command Center
    await page.goto('http://127.0.0.1:8765/');
    
    // Validate Revenue Readiness panel is visible
    const panel = page.locator('#revenue-readiness-panel');
    await expect(panel).toBeVisible();

    // Validate that the freshness badge is visible and populated
    const freshnessBadge = page.locator('#revenue-readiness-freshness-badge');
    await expect(freshnessBadge).toBeVisible();
    const freshnessText = await freshnessBadge.innerText();
    expect(['FRESH', 'STALE', 'DEGRADED', 'UNKNOWN']).toContain(freshnessText.trim());

    // Validate at least 5 project cards render
    const cards = page.locator('.project-card');
    await expect(cards).toHaveCount(6);

    // Validate Epic Fury 2026 card elements and score formatting
    const epicFuryCard = page.locator('#project-card-epic-fury-2026');
    await expect(epicFuryCard).toBeVisible();
    
    const scoreBadge = epicFuryCard.locator('.project-score-badge');
    await expect(scoreBadge).toBeVisible();
    const scoreText = await scoreBadge.innerText();
    
    // Assert score is integer with exactly one percent sign (e.g. "100%") and no double percent sign (e.g. "100%%")
    expect(scoreText.trim()).toMatch(/^\d+%$/);
    expect(scoreText.trim()).not.toContain('%%');

    // Click Epic Fury card to expand details drawer
    await epicFuryCard.click();
    
    // Verify details drawer shows up
    const drawer = page.locator('[id^="project-details-drawer-"]');
    await expect(drawer).toBeVisible();

    // Verify detail breakdown elements
    const targetText = await drawer.innerText();
    expect(targetText).toContain('Epic Fury 2026 Detail Breakdown');
    expect(targetText).toContain('Vercel / Cloud Run');
    expect(targetText).toContain('Licensing / Commission Splits');
  });

  test('2. Verify CyberQRG-AI card displays active blockers and evidence links', async ({ page }) => {
    await page.goto('http://127.0.0.1:8765/');
    
    // Click CyberQRG-AI card
    const cyberqrgCard = page.locator('#project-card-cyberqrg-ai');
    await expect(cyberqrgCard).toBeVisible();
    await cyberqrgCard.click();

    // Details drawer must render blockers and actions
    const drawer = page.locator('[id^="project-details-drawer-"]');
    await expect(drawer).toBeVisible();
    
    const detailText = await drawer.innerText();
    expect(detailText).toContain('CyberQRG-AI Detail Breakdown');
    expect(detailText).toContain('❌'); // Should show blocker list item with cross emoji
    expect(detailText).toContain('Deployment descriptor');
  });
});
