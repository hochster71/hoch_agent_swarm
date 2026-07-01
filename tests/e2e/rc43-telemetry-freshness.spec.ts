import { test, expect } from '@playwright/test';

test.describe('RC43 Telemetry Freshness E2E Tests', () => {
  const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';

  test('1. Verify /api/pert/data returns correct freshness authority schema', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/pert/data`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('freshness_authority');
    const fa = data.freshness_authority;

    expect(fa).toHaveProperty('dashboard_render_time');
    expect(fa).toHaveProperty('global_last_full_verification_time');
    expect(fa).toHaveProperty('worker_last_probe_time');
    expect(fa).toHaveProperty('worker_last_dispatch_time');
    expect(fa).toHaveProperty('device_last_seen_time');
    expect(fa).toHaveProperty('evidence_ledger_last_scan_time');
    expect(fa).toHaveProperty('playwright_scoped_spec_last_run_time');
    expect(fa).toHaveProperty('playwright_full_suite_last_run_time');

    expect(fa).toHaveProperty('panels');
    const panels = fa.panels;
    expect(panels).toHaveProperty('executive_readiness');
    expect(panels).toHaveProperty('runtime_status');
    expect(panels).toHaveProperty('worker_metrics');
    expect(panels).toHaveProperty('worker_utilization_ledger');
  });

  test('2. Verify Dashboard UI separates render vs verification timestamps', async ({ page }) => {
    await page.goto(baseURL);
    
    // Check render time element
    const renderTimestamp = page.locator('#dashboard-render-timestamp');
    await expect(renderTimestamp).not.toHaveText('UNKNOWN');
    const renderText = await renderTimestamp.innerText();

    // Check verification time element
    const verifiedTimestamp = page.locator('#verified-timestamp');
    await expect(verifiedTimestamp).not.toHaveText('UNKNOWN');
    const verifiedText = await verifiedTimestamp.innerText();

    expect(renderText).not.toBe(verifiedText);
  });

  test('3. Verify iPhone monitor-only counts and offline freshness', async ({ page }) => {
    await page.goto(baseURL);

    // Verify monitor-only count in compute gap panel
    const monitorOnlyGap = page.locator('#gap-monitor-only');
    await expect(monitorOnlyGap).toBeVisible();
    await expect(monitorOnlyGap).toHaveText('1');

    // Verify monitor-only count in Swarm Scheduler panel
    const monitorOnlySched = page.locator('#worker-monitor');
    await expect(monitorOnlySched).toBeVisible();
    await expect(monitorOnlySched).toHaveText('1');

    // Locate iphone row in worker table and check freshness is not 0.0s
    const iphoneRow = page.locator('#ledger-tbody tr:has-text("iphone-15-pro-max")');
    await expect(iphoneRow).toBeVisible();
    
    // Find the freshness cell in that row
    const freshnessText = await iphoneRow.locator('td').nth(11).innerText();
    // Since iPhone is offline and heartbeat is fixed, it must be stale/not 0.0s
    expect(freshnessText).not.toBe('0.0s');
  });

  test('4. Verify Executive Readiness degrades when fake telemetry violations occur', async ({ page, request }) => {
    // If fake status violations exist, Executive Readiness panel should show degraded border
    const response = await request.get(`${baseURL}/api/pert/data`);
    const data = await response.json();
    const violations = data.guardrails?.fake_status_violations?.value || 0;

    await page.goto(baseURL);

    if (violations > 0) {
      const execPanel = page.locator('#executive-readiness-panel');
      const borderStyle = await execPanel.getAttribute('style');
      expect(borderStyle).toContain('var(--accent-red)');
      
      const execBadge = page.locator('#executive-freshness-badge');
      await expect(execBadge).toHaveText('DEGRADED');
    }
  });
});
