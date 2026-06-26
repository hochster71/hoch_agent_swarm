import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";

const DB_PATH = path.resolve(__dirname, "../../backend/swarm_ledger.db");
const MAIN_PY_PATH = path.resolve(__dirname, "../../backend/main.py");
const HTML_PATH = path.resolve(__dirname, "../../frontend/index.html");
const APP_JS_PATH = path.resolve(__dirname, "../../frontend/app.js");

interface ColumnInfo {
  cid: number;
  name: string;
  type: string;
  notnull: number;
  dflt_value: any;
  pk: number;
}

function runContractTest() {
  console.log("==================================================");
  console.log("STARTING EVIDENCE GRAPH CONTRACT AUDIT");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];

  // 1. Verify SQLite ledger DB file and evidence_graph_links table
  if (!fs.existsSync(DB_PATH)) {
    errors.push(`SQLite database file not found at ${DB_PATH}`);
  } else {
    findings.push(`Verified SQLite ledger DB file exists at: ${DB_PATH}`);
    try {
      const output = execSync(`sqlite3 "${DB_PATH}" "PRAGMA table_info(evidence_graph_links);"`, { encoding: "utf-8" });
      const columns: ColumnInfo[] = [];
      const lines = output.trim().split("\n");
      for (const line of lines) {
        if (!line.trim()) continue;
        const parts = line.split("|");
        if (parts.length >= 6) {
          columns.push({
            cid: parseInt(parts[0]),
            name: parts[1],
            type: parts[2],
            notnull: parseInt(parts[3]),
            dflt_value: parts[4],
            pk: parseInt(parts[5])
          });
        }
      }

      if (columns.length === 0) {
        errors.push("Table evidence_graph_links does not exist or is empty");
      } else {
        findings.push("Table evidence_graph_links exists");
        const colNames = columns.map(c => c.name);
        const expected = [
          "link_id",
          "source_graph_id",
          "target_graph_id",
          "relation_type",
          "created_at"
        ];
        expected.forEach(col => {
          if (!colNames.includes(col)) {
            errors.push(`evidence_graph_links missing expected column: ${col}`);
          } else {
            findings.push(`evidence_graph_links has column: ${col}`);
          }
        });
      }
    } catch (err: any) {
      errors.push(`Table evidence_graph_links check failed: ${err.message}`);
    }
  }

  // 2. Verify backend/main.py API routes
  if (!fs.existsSync(MAIN_PY_PATH)) {
    errors.push(`backend/main.py not found at ${MAIN_PY_PATH}`);
  } else {
    findings.push(`Verified backend/main.py exists`);
    const mainPyContent = fs.readFileSync(MAIN_PY_PATH, "utf-8");

    const expectedRoutes = [
      "/api/v1/evidence/graph",
      "/api/v1/evidence/graph/trace",
      "/api/v1/evidence/graph/link"
    ];

    expectedRoutes.forEach(route => {
      if (!mainPyContent.includes(route)) {
        errors.push(`backend/main.py does not contain route declaration: ${route}`);
      } else {
        findings.push(`backend/main.py contains route: ${route}`);
      }
    });

    if (!mainPyContent.includes("build_evidence_graph")) {
      errors.push(`backend/main.py does not import/reference build_evidence_graph`);
    } else {
      findings.push(`backend/main.py imports/references build_evidence_graph`);
    }
  }

  // 3. Verify HTML Panel structure in index.html
  if (!fs.existsSync(HTML_PATH)) {
    errors.push(`frontend/index.html not found at ${HTML_PATH}`);
  } else {
    findings.push(`Verified frontend/index.html exists`);
    const htmlContent = fs.readFileSync(HTML_PATH, "utf-8");

    const expectedHtmlIds = [
      "evidence-chain-view-panel",
      "btn-refresh-evidence-graph",
      "evidence-trace-start-select",
      "btn-trigger-evidence-trace",
      "evidence-flow-container",
      "evidence-node-inspector-content",
      "btn-save-manual-link",
      "evidence-graph-node-count",
      "evidence-graph-edge-count",
      "evidence-graph-hidden-count",
      "evidence-graph-load-more-button",
      "evidence-graph-compact-toggle",
      "evidence-graph-large-warning",
      "evidence-graph-empty-state"
    ];

    expectedHtmlIds.forEach(id => {
      if (!htmlContent.includes(`id="${id}"`) && !htmlContent.includes(`id='${id}'`)) {
        errors.push(`frontend/index.html missing HTML element with id: ${id}`);
      } else {
        findings.push(`frontend/index.html has element with id: ${id}`);
      }
    });
  }

  // 4. Verify JS Handlers in app.js
  if (!fs.existsSync(APP_JS_PATH)) {
    errors.push(`frontend/app.js not found at ${APP_JS_PATH}`);
  } else {
    findings.push(`Verified frontend/app.js exists`);
    const appJsContent = fs.readFileSync(APP_JS_PATH, "utf-8");

    const expectedJsSnippets = [
      "api/v1/evidence/graph",
      "btn-refresh-evidence-graph",
      "evidence-trace-start-select",
      "api/v1/evidence/graph/trace",
      "api/v1/evidence/graph/link",
      "visibleNodesLimit",
      "visibleEdgesLimit",
      "evidence-graph-load-more-button",
      "evidence-graph-compact-toggle",
      "DocumentFragment"
    ];

    expectedJsSnippets.forEach(snippet => {
      if (!appJsContent.includes(snippet)) {
        errors.push(`frontend/app.js missing evidence graph snippet: ${snippet}`);
      } else {
        findings.push(`frontend/app.js contains snippet: ${snippet}`);
      }
    });
  }

  writeReport(errors, findings);
}

function writeReport(errors: string[], findings: string[]) {
  const status = errors.length === 0 ? "PASS" : "FAIL";
  const report = {
    generated_at: new Date().toISOString(),
    status,
    errors,
    findings
  };

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/evidence-graph-contract-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`Evidence Graph Contract Audit completed with status: ${status}`);
  if (errors.length > 0) {
    console.error("Errors found during audit:", errors);
    process.exit(1);
  } else {
    console.log("All Evidence Graph contract checks passed!");
    process.exit(0);
  }
}

runContractTest();
