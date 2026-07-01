/**
 * tests/e2e/rc26-relay-routing.spec.ts
 * ======================================
 * RC26: Relay Routing Integration — Playwright test suite
 *
 * Validates that the local backend correctly proxies and reports
 * the HAS-WORKER-RELAY-001 relay worker status.
 *
 * Hard constraints validated:
 *   - /api/v1/relay/health always returns worker_status field
 *   - worker_status is ONLY "ONLINE" or "UNKNOWN" — never "PASS", "ok", or synthesised
 *   - /api/v1/relay/registry returns workers array with HAS-WORKER-RELAY-001
 *   - /api/v1/relay/status always has port_public_exposed: false
 *   - Relay unreachable → worker_status === "UNKNOWN" (not an error)
 *   - Public port 50.116.41.183:3012 must be unreachable
 *   - Accountability endpoint returns HTTP 200
 *
 * Run:
 *   E2E_BASE_URL=http://localhost:8000 npx playwright test tests/e2e/rc26-relay-routing.spec.ts
 *
 * Note: Tests 1-7 target the LOCAL BACKEND (default http://localhost:8000).
 *       Test 8 targets the public VPS IP directly to verify port is closed.
 *       If Tailscale is connected, relay tests may show ONLINE; otherwise UNKNOWN.
 *       UNKNOWN is a valid and expected state per HOCH-200 constraints.
 */

import { test, expect, request } from "@playwright/test";

declare const process: { env: Record<string, string | undefined> };

const BACKEND_BASE = process.env.E2E_BASE_URL || "http://localhost:8000";
const PUBLIC_VPS   = "http://50.116.41.183:3012";
const WORKER_ID    = "HAS-WORKER-RELAY-001";

// ─── /api/v1/relay/health ─────────────────────────────────────────────────────

test.describe("RC26 /api/v1/relay/health", () => {

  test("relay health endpoint returns HTTP 200", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/health");
    expect(resp.status()).toBe(200);
    await ctx.dispose();
  });

  test("relay health response always contains worker_status field", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/health");
    const body = await resp.json();
    expect(body).toHaveProperty("worker_status");
    await ctx.dispose();
  });

  test("worker_status is ONLINE or UNKNOWN — never any other value", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/health");
    const body = await resp.json();
    const status: string = body.worker_status;
    // Hard gate: only these two values are permitted
    expect(["ONLINE", "UNKNOWN"]).toContain(status);
    // Hard negative: PASS, ok, TRUE, 1 must never appear
    expect(status).not.toMatch(/pass/i);
    expect(status).not.toMatch(/^ok$/i);
    expect(status).not.toMatch(/^true$/i);
    expect(status).not.toBe("1");
    await ctx.dispose();
  });

  test("relay health reachable field is a boolean", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/health");
    const body = await resp.json();
    expect(typeof body.reachable).toBe("boolean");
    await ctx.dispose();
  });

});

// ─── /api/v1/relay/registry ──────────────────────────────────────────────────

test.describe("RC26 /api/v1/relay/registry", () => {

  test("relay registry endpoint returns HTTP 200", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/registry");
    expect(resp.status()).toBe(200);
    await ctx.dispose();
  });

  test("relay registry always contains workers array", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/registry");
    const body = await resp.json();
    expect(body).toHaveProperty("workers");
    expect(Array.isArray(body.workers)).toBe(true);
    await ctx.dispose();
  });

  test("HAS-WORKER-RELAY-001 appears in registry when relay is reachable", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/registry");
    const body = await resp.json();
    // If relay is reachable, the worker must be present
    if (body.reachable === true) {
      const workerIds = (body.workers as Array<{ id: string }>).map((w) => w.id);
      expect(workerIds).toContain(WORKER_ID);
    } else {
      // When unreachable, workers array must be empty (not fabricated)
      expect(body.workers).toHaveLength(0);
    }
    await ctx.dispose();
  });

});

// ─── /api/v1/relay/status ────────────────────────────────────────────────────

test.describe("RC26 /api/v1/relay/status", () => {

  test("relay status endpoint returns HTTP 200", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/status");
    expect(resp.status()).toBe(200);
    await ctx.dispose();
  });

  test("relay status port_public_exposed is always false", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/status");
    const body = await resp.json();
    // Immutable HOCH-200 constraint — must never be true
    expect(body.port_public_exposed).toBe(false);
    await ctx.dispose();
  });

  test("relay status worker_status is ONLINE or UNKNOWN only", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/status");
    const body = await resp.json();
    expect(body).toHaveProperty("worker_status");
    expect(["ONLINE", "UNKNOWN"]).toContain(body.worker_status);
    await ctx.dispose();
  });

  test("relay status worker_id is HAS-WORKER-RELAY-001", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/relay/status");
    const body = await resp.json();
    expect(body.worker_id).toBe(WORKER_ID);
    await ctx.dispose();
  });

});

// ─── Accountability endpoint ──────────────────────────────────────────────────

test.describe("RC26 accountability endpoint", () => {

  test("accountability agents endpoint returns HTTP 200", async () => {
    const ctx = await request.newContext({ baseURL: BACKEND_BASE });
    const resp = await ctx.get("/api/v1/accountability/agents");
    expect(resp.status()).toBe(200);
    await ctx.dispose();
  });

});

// ─── Public port closure gate ────────────────────────────────────────────────

test.describe("RC26 public port 3012 closure", () => {

  test("public VPS port 50.116.41.183:3012 must be unreachable (HOCH-200 constraint)", async () => {
    // This test verifies the hard HOCH-200 constraint: port 3012 must NOT be publicly reachable.
    // We expect a connection failure. If it succeeds (HTTP 200), the constraint is violated.
    const ctx = await request.newContext({ baseURL: PUBLIC_VPS });
    let reachable = false;
    try {
      const resp = await ctx.get("/health", { timeout: 4000 });
      // If we get any 2xx response, the port is exposed — constraint violated
      if (resp.status() >= 200 && resp.status() < 300) {
        reachable = true;
      }
    } catch {
      // Connection refused or timeout — expected and correct
      reachable = false;
    }
    expect(reachable).toBe(false);
    await ctx.dispose();
  });

});
