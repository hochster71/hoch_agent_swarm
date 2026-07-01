import { test, expect } from '@playwright/test';

test.describe('RC41 Worker Telemetry Accuracy E2E Tests', () => {
  test('1. Verify /api/pert/data returns correct worker telemetry-wrapped metrics', async ({ request }) => {
    const response = await request.get('http://127.0.0.1:8765/api/pert/data');
    expect(response.ok()).toBe(true);

    const data = await response.json();
    expect(data.tailnet_workers).toBeDefined();
    expect(data.tailnet_workers.length).toBeGreaterThan(0);

    const schemaKeys = ["value", "source", "last_updated", "freshness", "confidence", "fallback_state"];

    // Check each worker's telemetry fields
    for (const w of data.tailnet_workers) {
      const fields = [
        "worker_id", "role", "online_status", "last_heartbeat", 
        "last_job_time", "last_probe_time", "last_evidence_file", 
        "data_source", "freshness", "confidence", "unknown_reason", 
        "not_applicable_reason"
      ];

      for (const f of fields) {
        // Assert raw string field
        expect(w[f]).toBeDefined();
        expect(typeof w[f]).toBe('string');
        
        // Assert telemetry-wrapped field
        const tf = f + "_telemetry";
        expect(w[tf]).toBeDefined();
        expect(typeof w[tf]).toBe('object');
        for (const key of schemaKeys) {
          expect(w[tf][key]).toBeDefined();
        }
      }
    }

    // Assert iPhone specific semantics
    const phone = data.tailnet_workers.find(w => w.machine === 'iphone-15-pro-max');
    expect(phone).toBeDefined();
    expect(phone.role).toBe('operator_mobile_monitor');
    expect(phone.last_job_time).toBe('N/A — monitor-only');
    expect(phone.last_probe_time).toBe('N/A — no CLI support on iOS / monitor-only');
    expect(phone.not_applicable_reason).toBe('no CLI support on iOS / monitor-only');

    // Assert hoch-relay-001 specific semantics
    const relay = data.tailnet_workers.find(w => w.machine === 'hoch-relay-001');
    expect(relay).toBeDefined();
    expect(relay.role).toBe('relay_worker');
    expect(relay.last_job_time).toContain('UNKNOWN — no dispatch evidence yet');
  });

  test('2. Verify Worker Utilization Ledger renders correctly in UI', async ({ page }) => {
    await page.goto('http://127.0.0.1:8765/');
    
    // Validate Worker Utilization Ledger panel is visible
    const ledgerPanel = page.locator('#worker-utilization-ledger-panel');
    await expect(ledgerPanel).toBeVisible();

    // Verify worker rows are rendered
    const rows = ledgerPanel.locator('#ledger-tbody tr');
    await expect(rows).toHaveCount(3);

    // Verify iPhone row contents
    const phoneRow = rows.filter({ hasText: 'iphone-15-pro-max' });
    await expect(phoneRow).toBeVisible();
    await expect(phoneRow).toContainText('operator_mobile_monitor');
    await expect(phoneRow).toContainText('N/A — monitor-only');
    await expect(phoneRow).toContainText('N/A — no CLI support on iOS / monitor-only');

    // Verify hoch-relay-001 row contents
    const relayRow = rows.filter({ hasText: 'hoch-relay-001' });
    await expect(relayRow).toBeVisible();
    await expect(relayRow).toContainText('relay_worker');
    await expect(relayRow).toContainText('UNKNOWN — no dispatch evidence yet');
  });
});
