import fs from "node:fs";
import path from "node:path";

interface ContractResult {
  generated_at: string;
  status: "PASS" | "FAIL";
  blockers: string[];
}

function runContractTest() {
  console.log("==================================================");
  console.log("STARTING OPERATOR GOVERNANCE COCKPIT CONTRACT TEST");
  console.log("==================================================");

  const blockers: string[] = [];

  const mainPyPath = "backend/main.py";
  if (!fs.existsSync(mainPyPath)) {
    blockers.push(`Missing backend/main.py`);
  } else {
    const mainPy = fs.readFileSync(mainPyPath, "utf8");
    if (!mainPy.includes("/api/v1/governance/summary")) {
      blockers.push("backend/main.py missing /api/v1/governance/summary endpoint");
    }
    if (!mainPy.includes("TEST_MODE =")) {
      blockers.push("backend/main.py missing TEST_MODE definition");
    }
    if (!mainPy.includes("[TEST-ONLY]")) {
      blockers.push("backend/main.py missing test-only log string");
    }
  }

  const htmlPath = "frontend/index.html";
  if (!fs.existsSync(htmlPath)) {
    blockers.push(`Missing frontend/index.html`);
  } else {
    const html = fs.readFileSync(htmlPath, "utf8");

    // Check DOM IDs
    const requiredIds = [
      "nav-governance",
      "view-governance",
      "gov-pending-list",
      "gov-pending-count",
      "gov-blockers-list",
      "gov-blockers-status",
      "gov-active-channel",
      "gov-signing-waiver",
      "gov-tag-alignment",
      "gov-test-bypass-active",
      "gov-capability-tbody",
      "gov-replay-tbody",
      "gov-ledger-tbody",
      "crewai-ingestion-bridge-panel",
      "btn-trigger-crewai-ingest",
      "crewai-ingest-status-msg",
      "crewai-plans-tbody",
      "crewai-runs-tbody"
    ];
    for (const id of requiredIds) {
      if (!html.includes(`id="${id}"`)) {
        blockers.push(`frontend/index.html missing DOM ID: ${id}`);
      }
    }

    // Check visible text
    const requiredTexts = [
      "Operator Governance Command Center",
      "PENDING APPROVAL GATES",
      "FORMAL RELEASE BLOCKERS",
      "ACTIVE POLICIES & WAIVERS",
      "CAPABILITY ENFORCEMENT DECISIONS",
      "REPLAY-PROTECTION INTEGRITY EVIDENCE",
      "HISTORICAL OPERATOR DECISION LEDGER",
      "CREWAI EXECUTION ARTIFACT INGESTION BRIDGE"
    ];
    for (const text of requiredTexts) {
      if (!html.includes(text)) {
        blockers.push(`frontend/index.html missing required text: "${text}"`);
      }
    }
  }

  const appJsPath = "frontend/app.js";
  if (!fs.existsSync(appJsPath)) {
    blockers.push(`Missing frontend/app.js`);
  } else {
    const appJs = fs.readFileSync(appJsPath, "utf8");
    if (!appJs.includes("governance: { nav: document.getElementById(\"nav-governance\")")) {
      blockers.push("frontend/app.js does not map nav-governance");
    }
    if (!appJs.includes("fetchAndRenderGovernanceSummary")) {
      blockers.push("frontend/app.js does not define fetchAndRenderGovernanceSummary");
    }
    if (!appJs.includes("window.fetchAndRenderGovernanceSummary")) {
      blockers.push("frontend/app.js does not expose window.fetchAndRenderGovernanceSummary");
    }
    if (!appJs.includes("initCrewaiIngestionBridge")) {
      blockers.push("frontend/app.js does not define initCrewaiIngestionBridge");
    }
    if (!appJs.includes("window.initCrewaiIngestionBridge")) {
      blockers.push("frontend/app.js does not expose window.initCrewaiIngestionBridge");
    }
  }

  const report: ContractResult = {
    generated_at: new Date().toISOString(),
    status: blockers.length === 0 ? "PASS" : "FAIL",
    blockers
  };

  const reportDir = "artifacts/qa";
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(
    path.join(reportDir, "operator-governance-contract-report.json"),
    JSON.stringify(report, null, 2)
  );

  console.log(`Operator Governance Cockpit Contract Test completed with status: ${report.status}`);
  if (report.status === "FAIL") {
    console.error("Blockers found:", report.blockers);
    process.exit(1);
  } else {
    console.log("All operator governance cockpit contract checks passed successfully!");
    process.exit(0);
  }
}

runContractTest();
