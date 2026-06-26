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
    if (!mainPy.includes("/api/v1/release/simulate-decision")) {
      blockers.push("backend/main.py missing /api/v1/release/simulate-decision endpoint");
    }
    if (!mainPy.includes("/api/v1/release/authority/request")) {
      blockers.push("backend/main.py missing /api/v1/release/authority/request endpoint");
    }
    if (!mainPy.includes("/api/v1/release/promote")) {
      blockers.push("backend/main.py missing /api/v1/release/promote endpoint");
    }
    if (!mainPy.includes("/api/v1/release/execution-plan/generate")) {
      blockers.push("backend/main.py missing /api/v1/release/execution-plan/generate endpoint");
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
      "crewai-runs-tbody",
      "release-decision-room-panel",
      "decision-room-candidate-select",
      "btn-decision-simulate-approve",
      "btn-decision-simulate-reject",
      "btn-export-decision-memo",
      "decision-room-details-grid",
      "dec-status-packet",
      "dec-status-preview",
      "dec-status-dry-run",
      "dec-status-attestation",
      "dec-check-signing",
      "dec-check-channel",
      "dec-check-gates",
      "dec-check-readiness",
      "dec-blockers-warning-list",
      "dec-graph-total-nodes",
      "dec-graph-missing-nodes",
      "dec-graph-integrity",
      "release-authority-gate-panel",
      "gov-authority-badge",
      "gov-authority-status",
      "gov-authority-token-details",
      "gov-active-token-val",
      "gov-token-countdown",
      "btn-request-authority",
      "btn-execute-real-promotion",
      "authority-request-modal",
      "modal-authority-candidate-id",
      "chk-confirm-authority-scope",
      "btn-modal-cancel-authority",
      "btn-modal-grant-authority",
      "release-execution-plan-panel",
      "btn-generate-execution-plan",
      "execution-plan-details",
      "execution-plan-steps-tbody",
      "btn-export-plan-markdown",
      "btn-export-plan-json"
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
      "CREWAI EXECUTION ARTIFACT INGESTION BRIDGE",
      "OPERATOR RELEASE DECISION ROOM",
      "RELEASE PROMOTION PIPELINE STATUS",
      "COMPLIANCE & GOVERNANCE CHECKS",
      "DETECTED BLOCKERS & MISSING EVIDENCE",
      "EVIDENCE GRAPH COMPLETENESS",
      "FORMAL RELEASE AUTHORITY GATE",
      "RESTRICTED PRODUCTION ACTIONS",
      "CONFIRM RELEASE AUTHORITY REQUEST",
      "FORMAL RELEASE EXECUTION DRY-RUN PLANNER",
      "ORDERED EXECUTION PROTOCOL"
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
    if (!appJs.includes("initReleaseDecisionRoom")) {
      blockers.push("frontend/app.js does not define initReleaseDecisionRoom");
    }
    if (!appJs.includes("window.initReleaseDecisionRoom")) {
      blockers.push("frontend/app.js does not expose window.initReleaseDecisionRoom");
    }
    if (!appJs.includes("updateReleaseAuthorityUI")) {
      blockers.push("frontend/app.js does not define updateReleaseAuthorityUI");
    }
    if (!appJs.includes("startAuthorityCountdown")) {
      blockers.push("frontend/app.js does not define startAuthorityCountdown");
    }
    if (!appJs.includes("generateExecutionPlan")) {
      blockers.push("frontend/app.js does not define generateExecutionPlan");
    }
    if (!appJs.includes("exportPlanMarkdown")) {
      blockers.push("frontend/app.js does not define exportPlanMarkdown");
    }
    if (!appJs.includes("exportPlanJson")) {
      blockers.push("frontend/app.js does not define exportPlanJson");
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
