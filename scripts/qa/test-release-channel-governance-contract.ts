import fs from "node:fs";
import path from "node:path";

interface ContractResult {
  generated_at: string;
  status: "PASS" | "FAIL";
  blockers: string[];
}

function runContractTest() {
  console.log("==================================================");
  console.log("STARTING RELEASE CHANNEL GOVERNANCE CONTRACT TEST");
  console.log("==================================================");

  const blockers: string[] = [];

  const mainPyPath = "backend/main.py";
  if (!fs.existsSync(mainPyPath)) {
    blockers.push(`Missing backend/main.py`);
  } else {
    const mainPy = fs.readFileSync(mainPyPath, "utf8");
    if (!mainPy.includes("/api/v1/release/channel-governance")) {
      blockers.push("backend/main.py missing /api/v1/release/channel-governance endpoint");
    }
    if (!mainPy.includes("/api/v1/release/channel-decision")) {
      blockers.push("backend/main.py missing /api/v1/release/channel-decision endpoint");
    }
    if (!mainPy.includes("formal_requires_tag_at_head")) {
      blockers.push("backend/main.py missing formal_requires_tag_at_head variable");
    }
    if (!mainPy.includes("tag_move_requires_operator_approval")) {
      blockers.push("backend/main.py missing tag_move_requires_operator_approval variable");
    }
    if (!mainPy.includes("STALE_TAG")) {
      blockers.push("backend/main.py missing STALE_TAG string");
    }
    if (!mainPy.includes("FORMAL_RELEASE_BLOCKED") && !mainPy.includes("formal_release_blocked")) {
      blockers.push("backend/main.py missing FORMAL_RELEASE_BLOCKED / formal_release_blocked finalization status");
    }
  }

  const manifestGeneratorPath = "scripts/supply-chain/generate-release-manifest.ts";
  if (!fs.existsSync(manifestGeneratorPath)) {
    blockers.push(`Missing generate-release-manifest.ts`);
  } else {
    const manifestGen = fs.readFileSync(manifestGeneratorPath, "utf8");
    if (!manifestGen.includes("release_channel")) {
      blockers.push("generate-release-manifest.ts does not reference release_channel");
    }
    if (!manifestGen.includes("release_tag_points_at_head")) {
      blockers.push("generate-release-manifest.ts does not reference release_tag_points_at_head");
    }
  }

  const verifyScriptPath = "scripts/supply-chain/verify-release-artifacts.ts";
  if (!fs.existsSync(verifyScriptPath)) {
    blockers.push(`Missing verify-release-artifacts.ts`);
  } else {
    const verifyScript = fs.readFileSync(verifyScriptPath, "utf8");
    if (!verifyScript.includes("tag_status")) {
      blockers.push("verify-release-artifacts.ts does not reference tag_status");
    }
    if (!verifyScript.includes("formal_release_blockers")) {
      blockers.push("verify-release-artifacts.ts does not reference formal_release_blockers");
    }
  }

  const htmlPath = "frontend/archive/unused_views.html";
  if (!fs.existsSync(htmlPath)) {
    blockers.push(`Missing frontend/archive/unused_views.html`);
  } else {
    const html = fs.readFileSync(htmlPath, "utf8");
    
    // Check forbidden items
    if (html.includes("cdn.tailwindcss.com")) {
      blockers.push("frontend/index.html references forbidden cdn.tailwindcss.com");
    }
    if (html.includes("/src/main.tsx")) {
      blockers.push("frontend/index.html references forbidden /src/main.tsx");
    }

    // Check required DOM IDs
    const requiredIds = [
      "release-channel-governance-panel",
      "release-channel-current",
      "release-channel-policy-status",
      "release-tag-current",
      "release-tag-status",
      "release-tag-head-sha",
      "release-tag-target-sha",
      "release-tag-alignment-status",
      "release-formal-finalization-status",
      "release-channel-action-list",
      "release-channel-decision-form",
      "release-channel-request-button"
    ];
    for (const id of requiredIds) {
      if (!html.includes(`id="${id}"`)) {
        blockers.push(`frontend/index.html missing DOM ID: ${id}`);
      }
    }

    // Check required visible text
    const requiredTexts = [
      "Release Channel Governance",
      "Current Channel",
      "Release Tag",
      "Tag Alignment",
      "Tag Points at HEAD",
      "Stale Tag",
      "No Release Tag",
      "Formal Release Blocked",
      "Formal Release Ready",
      "Local Dev",
      "Candidate",
      "Formal",
      "Request Candidate Release",
      "Request Formal Release Approval",
      "Request Tag Alignment Approval",
      "No tag movement without operator approval"
    ];
    for (const text of requiredTexts) {
      if (!html.includes(text)) {
        blockers.push(`frontend/index.html missing required text: "${text}"`);
      }
    }
  }

  const appJsPath = "frontend/archive/unused_views.js";
  if (!fs.existsSync(appJsPath)) {
    blockers.push(`Missing frontend/archive/unused_views.js`);
  } else {
    const appJs = fs.readFileSync(appJsPath, "utf8");
    if (!appJs.includes("/api/v1/release/channel-governance")) {
      blockers.push("frontend/app.js does not fetch /api/v1/release/channel-governance");
    }
    if (!appJs.includes("release_tag_status") && !appJs.includes("tag_status")) {
      blockers.push("frontend/app.js does not render release_tag_status / tag_status");
    }
    if (!appJs.includes("formal_release_finalization_status") && !appJs.includes("release_finalization_status")) {
      blockers.push("frontend/app.js does not render formal_release_finalization_status / release_finalization_status");
    }
  }

  // Check built tailwind.css exists
  const distCssPath = "frontend/dist/tailwind.css";
  if (!fs.existsSync(distCssPath)) {
    blockers.push("frontend/dist/tailwind.css does not exist");
  }

  const report: ContractResult = {
    generated_at: new Date().toISOString(),
    status: blockers.length === 0 ? "PASS" : "BLOCK",
    blockers
  };

  const reportDir = "artifacts/qa";
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(
    path.join(reportDir, "release-channel-governance-contract-report.json"),
    JSON.stringify(report, null, 2)
  );

  console.log(`Release Channel Governance Contract Test completed with status: ${report.status}`);
  if (report.status === "BLOCK") {
    console.error("Blockers found:", report.blockers);
    process.exit(1);
  } else {
    console.log("All release channel governance contract checks passed successfully!");
    process.exit(0);
  }
}

runContractTest();
