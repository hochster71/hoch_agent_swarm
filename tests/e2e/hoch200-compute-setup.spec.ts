/**
 * tests/e2e/hoch200-compute-setup.spec.ts
 * =========================================
 * HOCH-200 Relay Stack E2E Tests
 *
 * Target: http://100.87.18.15:3012 (Tailscale-internal)
 * Run:    E2E_BASE_URL=http://100.87.18.15:3012 npx playwright test tests/e2e/hoch200-compute-setup.spec.ts
 *
 * Hard constraints validated:
 *   - Port 3012 is NOT publicly reachable
 *   - Dashboard loads over Tailscale
 *   - HAS-WORKER-RELAY-001 appears as ONLINE
 *   - /health returns {"status":"ok"}
 *   - Worker registry JSON is well-formed
 */

import { test, expect, request } from "@playwright/test";

// Allow process.env without @types/node in a bare tsconfig environment
declare const process: { env: Record<string, string | undefined> };

const TAILSCALE_BASE = process.env.E2E_BASE_URL || "http://100.87.18.15:3012";
const PUBLIC_BASE    = "http://50.116.41.183:3012";
const WORKER_ID      = "HAS-WORKER-RELAY-001";

// ─── Dashboard UI ────────────────────────────────────────────────────────────

test.describe("HOCH-200 Dashboard UI", () => {
  test.use({ baseURL: TAILSCALE_BASE });

  test("dashboard loads over Tailscale with HTTP 200", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);
  });

  test("dashboard has correct title", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/HOCH-200 Relay/i);
  });

  test("dashboard shows relay node identifier", async ({ page }) => {
    await page.goto("/");
    const body = await page.content();
    expect(body).toMatch(/hoch-relay-001/i);
  });

  test("dashboard shows Tailscale IP in header or body", async ({ page }) => {
    await page.goto("/");
    const body = await page.content();
    expect(body).toContain("100.87.18.15");
  });

  test("worker id HAS-WORKER-RELAY-001 is present on dashboard", async ({ page }) => {
    await page.goto("/");
    const body = await page.content();
    expect(body).toContain(WORKER_ID);
  });

  test("dashboard renders gate banner element", async ({ page }) => {
    await page.goto("/");
    // Wait for JS to execute
    await page.waitForTimeout(2000);
    const banner = page.locator("#gate-banner");
    await expect(banner).toBeVisible();
  });

  test("dashboard renders worker status stat card", async ({ page }) => {
    await page.goto("/");
    const workerStatEl = page.locator("#stat-worker-status");
    await expect(workerStatEl).toBeVisible();
  });

  test("port exposure card shows PRIVATE (not public)", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(2000);
    const portEl = page.locator("#stat-port-exposure");
    await expect(portEl).toBeVisible();
    const text = await portEl.textContent();
    // Must NOT say PUBLIC
    expect(text).not.toMatch(/public/i);
  });
});

// ─── Health Endpoint ──────────────────────────────────────────────────────────

test.describe("HOCH-200 /health endpoint", () => {
  test("/health returns HTTP 200", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/health`);
    expect(r.status()).toBe(200);
  });

  test("/health returns JSON with status=ok", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/health`);
    const body = await r.json();
    expect(body.status).toBe("ok");
  });

  test("/health includes worker field = HAS-WORKER-RELAY-001", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/health`);
    const body = await r.json();
    expect(body.worker).toBe(WORKER_ID);
  });

  test("/health includes ts (timestamp) field", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/health`);
    const body = await r.json();
    expect(body.ts).toBeDefined();
    expect(typeof body.ts).toBe("string");
    expect(body.ts.length).toBeGreaterThan(10);
  });

  test("/health returns worker_status=ONLINE", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/health`);
    const body = await r.json();
    // Worker must be ONLINE; anything else (including UNKNOWN) is a failure
    expect(body.worker_status).toBe("ONLINE");
  });
});

// ─── API Status ───────────────────────────────────────────────────────────────

test.describe("HOCH-200 /api/status endpoint", () => {
  test("/api/status returns HTTP 200", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/status`);
    expect(r.status()).toBe(200);
  });

  test("/api/status epic field = HOCH-200", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/status`);
    const body = await r.json();
    expect(body.epic).toBe("HOCH-200");
  });

  test("/api/status port_public_exposed = false", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/status`);
    const body = await r.json();
    expect(body.port_public_exposed).toBe(false);
  });

  test("/api/status tailscale_ip = 100.87.18.15", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/status`);
    const body = await r.json();
    expect(body.tailscale_ip).toBe("100.87.18.15");
  });

  test("/api/status relay_node = hoch-relay-001", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/status`);
    const body = await r.json();
    expect(body.relay_node).toBe("hoch-relay-001");
  });
});

// ─── Worker Registry ──────────────────────────────────────────────────────────

test.describe("HOCH-200 /api/registry endpoint", () => {
  test("/api/registry returns HTTP 200", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/registry`);
    expect(r.status()).toBe(200);
  });

  test("/api/registry contains workers array", async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/registry`);
    const body = await r.json();
    expect(Array.isArray(body.workers)).toBe(true);
    expect(body.workers.length).toBeGreaterThan(0);
  });

  test(`/api/registry contains ${WORKER_ID}`, async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/registry`);
    const body = await r.json();
    const worker = body.workers.find((w: { id: string }) => w.id === WORKER_ID);
    expect(worker).toBeDefined();
  });

  test(`${WORKER_ID} status is ONLINE`, async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/registry`);
    const body = await r.json();
    const worker = body.workers.find((w: { id: string }) => w.id === WORKER_ID);
    expect(worker?.status).toBe("ONLINE");
    // Must NOT be UNKNOWN
    expect(worker?.status).not.toBe("UNKNOWN");
  });

  test(`${WORKER_ID} has tailscale_ip = 100.87.18.15`, async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/registry`);
    const body = await r.json();
    const worker = body.workers.find((w: { id: string }) => w.id === WORKER_ID);
    expect(worker?.tailscale_ip).toBe("100.87.18.15");
  });

  test(`${WORKER_ID} relay_port_public = false`, async ({ request }) => {
    const r = await request.get(`${TAILSCALE_BASE}/api/registry`);
    const body = await r.json();
    const worker = body.workers.find(
      (w: { id: string; relay_port_public?: boolean }) => w.id === WORKER_ID
    );
    // relay_port_public must be false (or undefined is also acceptable if absent)
    if (worker?.relay_port_public !== undefined) {
      expect(worker.relay_port_public).toBe(false);
    }
  });
});

// ─── Heartbeat ────────────────────────────────────────────────────────────────

test.describe("HOCH-200 /api/heartbeat endpoint", () => {
  test("/api/heartbeat accepts POST and returns accepted=true", async ({ request }) => {
    const r = await request.post(`${TAILSCALE_BASE}/api/heartbeat`, {
      data: { source: "e2e-test", ts: new Date().toISOString() }
    });
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.accepted).toBe(true);
    expect(body.ts).toBeDefined();
  });
});

// ─── Security: Port NOT publicly reachable ───────────────────────────────────

test.describe("HOCH-200 Security — Port 3012 not public", () => {
  test("port 3012 is NOT reachable via public IP (negative test)", async ({ request }) => {
    /**
     * HARD CONSTRAINT: Port 3012 must NOT be accessible at the public IP.
     * This test expects a network failure (connection refused / timeout).
     * If it PASSES the request (gets any HTTP response), the constraint is violated.
     */
    let reachable = false;
    try {
      const r = await request.get(`${PUBLIC_BASE}/health`, {
        timeout: 6_000  // 6s timeout — UFW should drop the packet
      });
      if (r.status() < 600) {
        // Got an HTTP response = port is reachable = SECURITY VIOLATION
        reachable = true;
      }
    } catch {
      // Network error (ECONNREFUSED, ETIMEDOUT) = port is blocked = PASS
      reachable = false;
    }

    expect(reachable, [
      `SECURITY VIOLATION: Port 3012 responded on public IP ${PUBLIC_BASE}!`,
      "Port 3012 must ONLY be accessible via Tailscale (100.87.18.15).",
      "Fix: verify UFW has no ALLOW rule for 3012 and docker-compose binds to 100.87.18.15 only.",
    ].join("\n")).toBe(false);
  });
});
