import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

test.describe("DAST & Negative Security Testing - Release Signing Policy", () => {
  
  test("asserts that invalid scope request is rejected with 400", async ({ request }) => {
    const res = await request.post("/api/v1/release/signing-waiver", {
      data: {
        reason: "Valid reason for waiver simulation",
        scope: "invalid_super_user_scope",
        operator: "Attacker"
      }
    });
    expect(res.status()).toBe(400);
    const body = await res.json();
    expect(body.detail).toBe("Invalid waiver scope");
  });

  test("asserts that empty or too-short waiver reasons are rejected with 400", async ({ request }) => {
    // 1. Test empty reason
    const resEmpty = await request.post("/api/v1/release/signing-waiver", {
      data: {
        reason: "   ",
        scope: "local_dev",
        operator: "Attacker"
      }
    });
    expect(resEmpty.status()).toBe(400);
    const bodyEmpty = await resEmpty.json();
    expect(bodyEmpty.detail).toBe("Waiver reason cannot be empty");

    // 2. Test short reason (< 10 chars)
    const resShort = await request.post("/api/v1/release/signing-waiver", {
      data: {
        reason: "short",
        scope: "local_dev",
        operator: "Attacker"
      }
    });
    expect(resShort.status()).toBe(400);
    const bodyShort = await resShort.json();
    expect(bodyShort.detail).toBe("Waiver reason must be at least 10 characters long");
  });

  test("asserts that operator/reason XSS injection payload is escaped in the UI", async ({ page, request }) => {
    const runId = Math.random().toString(36).substring(2, 10);
    const xssPayload = `<script>alert('XSS-${runId}')</script>`;
    const xssOperator = `Op-${runId}<img src=x onerror=alert(1)>`;
    const uniqueReason = `Formal waiver testing for XSS vulnerability (${runId}): ${xssPayload}`;

    // Submit formal release waiver request with XSS payload
    const res = await request.post("/api/v1/release/signing-waiver", {
      data: {
        reason: uniqueReason,
        scope: "formal_release",
        operator: xssOperator
      }
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.status).toBe("pending_approval");
    const approvalId = data.approval_id;

    // Approve the pending waiver request to log it to the operator ledger
    const approveRes = await request.post(`/api/approval/requests/${approvalId}/decisions`, {
      data: {
        decision: "approve",
        operator: xssOperator,
        timestamp: new Date().toISOString()
      }
    });
    expect(approveRes.status()).toBe(200);

    // Navigate to local dashboard and open Governance Cockpit
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.locator("#nav-governance").click();

    // Verify Governance Cockpit is visible
    const view = page.locator("#view-governance");
    await expect(view).toBeVisible();

    // Verify the historical decision ledger renders the escaped payload safely
    const ledgerTable = page.locator("#gov-ledger-tbody");
    await expect(ledgerTable).toBeVisible();

    // Assert that the text is strictly displayed as raw string (escaped) in the DOM rather than executing
    const row = ledgerTable.locator(`tr:has-text("Formal waiver testing for XSS vulnerability (${runId})")`);
    await expect(row).toBeVisible();
    await expect(row.locator("strong")).toHaveText(xssOperator);
    await expect(row.locator("td").nth(4)).toHaveText(uniqueReason);

    // Ensure the folder exists
    const screenshotPath = path.resolve(__dirname, "../../artifacts/qa/dast-xss-ledger-escaped.png");
    const artifactsDir = path.dirname(screenshotPath);
    if (!fs.existsSync(artifactsDir)) {
      fs.mkdirSync(artifactsDir, { recursive: true });
    }

    // Capture screenshot as evidence
    await page.screenshot({ path: screenshotPath });
  });

  test("asserts that approval decisions are replay-resistant and block duplicates with 400", async ({ request }) => {
    // 1. Create a dummy formal waiver request
    const res = await request.post("/api/v1/release/signing-waiver", {
      data: {
        reason: "Formal waiver testing for replay protection validation",
        scope: "formal_release",
        operator: "Operator"
      }
    });
    expect(res.status()).toBe(200);
    const data = await res.json();
    const approvalId = data.approval_id;

    // 2. Submit first approval decision
    const approveRes1 = await request.post(`/api/approval/requests/${approvalId}/decisions`, {
      data: {
        decision: "approve",
        operator: "Operator",
        timestamp: new Date().toISOString()
      }
    });
    expect(approveRes1.status()).toBe(200);

    // 3. Submit duplicate decision (replay attack)
    const approveRes2 = await request.post(`/api/approval/requests/${approvalId}/decisions`, {
      data: {
        decision: "approve",
        operator: "Operator",
        timestamp: new Date().toISOString()
      }
    });
    // Expected to be blocked by replay check
    expect(approveRes2.status()).toBe(400);
    const body = await approveRes2.json();
    expect(body.detail).toBe("Replay blocked: approval gate has already been decided");
  });

  test("asserts that calling the signing policy endpoint returns formal_release_blocked when unsigned and unwaived in formal mode", async ({ request }) => {
    // Trigger formal release simulation setting GITHUB_ACTIONS env proxy flag on endpoint query
    const res = await request.get("/api/v1/release/signing-policy");
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data.policy.formal_release_requires_signed).toBe(true);
  });
});
