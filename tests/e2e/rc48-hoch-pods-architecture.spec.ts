import { test, expect } from '@playwright/test';

test.describe('RC48 HOCH PODS Architecture and Theater E2E Tests', () => {
  const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:8765';

  test('1. Verify /api/pert/data returns correct HOCH PODS registry and runtime state schema', async ({ request }) => {
    const response = await request.get(`${baseURL}/api/pert/data`);
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('hoch_pods_registry');
    expect(data).toHaveProperty('hoch_pods_runtime_state');
    expect(data).toHaveProperty('freshness_authority');

    const registry = data.hoch_pods_registry;
    const runtimeState = data.hoch_pods_runtime_state;

    // Check we have all 7 pods in the registry
    expect(registry.length).toBe(7);
    const expectedPodIds = ['pod-cyber', 'pod-qa', 'pod-builder', 'pod-revenue', 'pod-audit', 'pod-research', 'pod-deploy'];
    expectedPodIds.forEach(id => {
      const pod = registry.find(p => p.pod_id === id);
      expect(pod).toBeDefined();
      expect(pod).toHaveProperty('name');
      expect(pod).toHaveProperty('domain');
      expect(pod).toHaveProperty('control_families');
    });

    // Check runtime states
    expect(runtimeState.length).toBe(7);
    runtimeState.forEach(state => {
      expect(state).toHaveProperty('pod_id');
      expect(state).toHaveProperty('state');
      expect(state).toHaveProperty('mission');
      expect(state).toHaveProperty('policy_status');
    });

    // Check panel freshness is registered
    const fa = data.freshness_authority;
    expect(fa).toHaveProperty('panels');
    expect(fa.panels).toHaveProperty('hoch_pods_theater');
  });

  test('2. Verify Dashboard UI renders 7 pod cards and has hover tooltips', async ({ page }) => {
    await page.goto(baseURL);

    // Verify theater panel is visible
    const theaterPanel = page.locator('#hoch-pods-theater-panel');
    await expect(theaterPanel).toBeVisible();

    // Verify freshness badge is rendered and not UNKNOWN
    const freshnessBadge = page.locator('#hoch-pods-freshness-badge');
    await expect(freshnessBadge).toBeVisible();
    await expect(freshnessBadge).not.toHaveText('UNKNOWN');

    // Verify we have 7 pod cards
    const podCards = page.locator('.pods-grid .pod-card');
    await expect(podCards).toHaveCount(7);

    // Verify hover popup / tooltip elements exist in each pod card
    const firstPodCard = podCards.first();
    const tooltip = firstPodCard.locator('.pod-tooltip');
    await expect(tooltip).toBeAttached(); // should exist in DOM

    // Check specific pod (e.g. Cyber Pod)
    const cyberPod = page.locator('#pod-card-pod-cyber');
    await expect(cyberPod).toBeVisible();
    await expect(cyberPod.locator('.pod-title')).toHaveText('Cyber Pod');
  });

  test('3. Verify Compliant Topology contains 7 zones', async ({ page }) => {
    await page.goto(baseURL);

    // Verify topology panel is visible
    const topologyPanel = page.locator('#hoch-pods-topology-panel');
    await expect(topologyPanel).toBeVisible();

    // Verify all 7 trust zones are present in the topology view
    const zones = [
      'Operator Zone',
      'Management Zone',
      'Model Zone',
      'Pod Runtime Zone',
      'Tool Execution Zone',
      'Evidence Zone',
      'Optional Remote Zone'
    ];

    for (const zone of zones) {
      await expect(topologyPanel.locator(`text=${zone}`)).toBeVisible();
    }
  });
});
