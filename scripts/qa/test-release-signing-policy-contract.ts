import * as fs from "fs";
import * as path from "path";

async function runSigningPolicyContractTest() {
  console.log("==================================================");
  console.log("STARTING RELEASE SIGNING POLICY GATE CONTRACT TEST");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];

  const mainPyPath = path.resolve(__dirname, "../../backend/main.py");
  const manifestGenPath = path.resolve(__dirname, "../../scripts/supply-chain/generate-release-manifest.ts");
  const verifyScriptPath = path.resolve(__dirname, "../../scripts/supply-chain/verify-release-artifacts.ts");
  const indexHtmlPath = path.resolve(__dirname, "../../frontend/index.html");
  const appJsPath = path.resolve(__dirname, "../../frontend/app.js");
  const tailwindDistCss = path.resolve(__dirname, "../../frontend/dist/tailwind.css");

  // 1. Verify backend/main.py endpoints
  if (!fs.existsSync(mainPyPath)) {
    errors.push(`Missing backend/main.py at: ${mainPyPath}`);
  } else {
    const mainContent = fs.readFileSync(mainPyPath, "utf-8");
    if (mainContent.includes("/api/v1/release/signing-policy")) {
      findings.push("Found GET /api/v1/release/signing-policy endpoint in main.py");
    } else {
      errors.push("Missing GET /api/v1/release/signing-policy endpoint in main.py");
    }
    if (mainContent.includes("/api/v1/release/signing-waiver")) {
      findings.push("Found POST /api/v1/release/signing-waiver endpoint in main.py");
    } else {
      errors.push("Missing POST /api/v1/release/signing-waiver endpoint in main.py");
    }
  }

  // 2. Verify release manifest generator contains the required keys
  if (!fs.existsSync(manifestGenPath)) {
    errors.push(`Missing manifest generator at: ${manifestGenPath}`);
  } else {
    const genContent = fs.readFileSync(manifestGenPath, "utf-8");
    const requiredKeys = [
      "signing_policy_status",
      "signing_required_for_formal_release",
      "signing_provider",
      "signature_status",
      "signed_artifacts_count",
      "unsigned_artifacts_count",
      "signing_waiver_status",
      "signing_waiver_decision_id",
      "release_finalization_status"
    ];
    requiredKeys.forEach((key) => {
      if (genContent.includes(key)) {
        findings.push(`Found required signing manifest key: ${key}`);
      } else {
        errors.push(`Missing required signing manifest key in generator: ${key}`);
      }
    });
  }

  // 3. Verify verification report generator includes PASS/WARN/BLOCK signing policy logic
  if (!fs.existsSync(verifyScriptPath)) {
    errors.push(`Missing verify-release-artifacts script at: ${verifyScriptPath}`);
  } else {
    const verifyContent = fs.readFileSync(verifyScriptPath, "utf-8");
    if (verifyContent.includes("blockers.push") && verifyContent.includes("unsigned") && (verifyContent.includes("isFormalRelease") || verifyContent.includes("isCI"))) {
      findings.push("Found PASS/WARN/BLOCK logic in verify-release-artifacts.ts");
    } else {
      errors.push("Missing PASS/WARN/BLOCK release finalization logic in verify-release-artifacts.ts");
    }
  }

  // 4. Verify frontend/index.html DOM IDs and visible text
  if (!fs.existsSync(indexHtmlPath)) {
    errors.push(`Missing frontend/index.html at: ${indexHtmlPath}`);
  } else {
    const indexContent = fs.readFileSync(indexHtmlPath, "utf-8");
    
    // Assert no cdn.tailwindcss.com
    if (indexContent.includes("cdn.tailwindcss.com")) {
      errors.push("Forbidden Tailwind CDN (cdn.tailwindcss.com) reference found in index.html");
    } else {
      findings.push("No Tailwind CDN reference in index.html");
    }

    // Assert no /src/main.tsx
    if (indexContent.includes("/src/main.tsx")) {
      errors.push("Forbidden /src/main.tsx reference found in index.html");
    } else {
      findings.push("No /src/main.tsx reference in index.html");
    }

    // Assert required DOM IDs
    const requiredIds = [
      "release-signing-policy-panel",
      "release-signature-status",
      "release-signing-policy-status",
      "release-finalization-status",
      "release-signing-provider",
      "release-signing-waiver-status",
      "release-signing-required-indicator",
      "release-signing-action-list"
    ];
    requiredIds.forEach((id) => {
      if (indexContent.includes(`id="${id}"`)) {
        findings.push(`Found required DOM ID: ${id}`);
      } else {
        errors.push(`Missing required DOM ID: ${id}`);
      }
    });

    // Assert required visible text
    const requiredTexts = [
      "Release Signing Policy",
      "Signature Status",
      "Signing Required for Formal Release",
      "Local Dev Allows Unsigned Evidence",
      "Formal Release Blocks Unsigned Artifacts",
      "Signing Pending",
      "Signed",
      "Waived With Operator Approval",
      "Formal Release Blocked",
      "Continue Local Dev",
      "Request Signing",
      "Request Operator Waiver"
    ];
    requiredTexts.forEach((text) => {
      if (indexContent.includes(text)) {
        findings.push(`Found required visible text: ${text}`);
      } else {
        errors.push(`Missing required visible text: ${text}`);
      }
    });
  }

  // 5. Verify frontend/app.js fetches /api/v1/release/signing-policy and renders properties
  if (!fs.existsSync(appJsPath)) {
    errors.push(`Missing frontend/app.js at: ${appJsPath}`);
  } else {
    const appContent = fs.readFileSync(appJsPath, "utf-8");
    if (appContent.includes("/api/v1/release/signing-policy")) {
      findings.push("Found fetch for /api/v1/release/signing-policy in app.js");
    } else {
      errors.push("Missing fetch for /api/v1/release/signing-policy in app.js");
    }
    if (appContent.includes("release-signature-status") || appContent.includes("signature_status")) {
      findings.push("Found signature status rendering logic in app.js");
    } else {
      errors.push("Missing signature status rendering logic in app.js");
    }
    if (appContent.includes("release-finalization-status") || appContent.includes("release_finalization_status")) {
      findings.push("Found finalization status rendering logic in app.js");
    } else {
      errors.push("Missing finalization status rendering logic in app.js");
    }
  }

  // 6. Verify tailwind dist CSS exists
  if (!fs.existsSync(tailwindDistCss)) {
    errors.push(`Missing compiled tailwind CSS at: ${tailwindDistCss}`);
  } else {
    findings.push("Verified frontend/dist/tailwind.css exists");
  }

  // 7. Write report
  const status = errors.length === 0 ? "PASS" : "FAIL";
  const report = {
    generated_at: new Date().toISOString(),
    status,
    errors,
    findings
  };

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/release-signing-policy-contract-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`Release Signing Policy Contract Test completed with status: ${status}`);

  if (errors.length > 0) {
    console.error("Contract errors found:", errors);
    process.exit(1);
  } else {
    console.log("All release signing policy contract checks passed successfully!");
    process.exit(0);
  }
}

runSigningPolicyContractTest();
