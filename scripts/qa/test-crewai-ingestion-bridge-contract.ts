import * as fs from "fs";
import * as path from "path";
import { execSync } from "child_process";

const DB_PATH = path.resolve(__dirname, "../../backend/swarm_ledger.db");
const MAIN_PY_PATH = path.resolve(__dirname, "../../backend/main.py");

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
  console.log("STARTING CREWAI INGESTION BRIDGE CONTRACT AUDIT");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];

  // 1. Verify SQLite ledger DB file and crewai_ingested_artifacts table
  if (!fs.existsSync(DB_PATH)) {
    errors.push(`SQLite database file not found at ${DB_PATH}`);
  } else {
    findings.push(`Verified SQLite ledger DB file exists at: ${DB_PATH}`);
    try {
      const output = execSync(`sqlite3 "${DB_PATH}" "PRAGMA table_info(crewai_ingested_artifacts);"`, { encoding: "utf-8" });
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
        errors.push("Table crewai_ingested_artifacts does not exist or is empty");
      } else {
        findings.push("Table crewai_ingested_artifacts exists");
        const colNames = columns.map(c => c.name);
        const expected = [
          "id",
          "source_path",
          "hash",
          "created_at",
          "artifact_type",
          "run_context_json",
          "ingested_at"
        ];
        expected.forEach(col => {
          if (!colNames.includes(col)) {
            errors.push(`crewai_ingested_artifacts missing expected column: ${col}`);
          } else {
            findings.push(`crewai_ingested_artifacts has column: ${col}`);
          }
        });
      }
    } catch (err: any) {
      errors.push(`Table crewai_ingested_artifacts check failed: ${err.message}`);
    }
  }

  // 2. Verify backend/main.py API routes
  if (!fs.existsSync(MAIN_PY_PATH)) {
    errors.push(`backend/main.py not found at ${MAIN_PY_PATH}`);
  } else {
    findings.push(`Verified backend/main.py exists`);
    const mainPyContent = fs.readFileSync(MAIN_PY_PATH, "utf-8");

    const expectedRoutes = [
      "/api/v1/ingest/crewai",
      "/api/v1/ingest/crewai/artifacts"
    ];

    expectedRoutes.forEach(route => {
      if (!mainPyContent.includes(route)) {
        errors.push(`backend/main.py does not contain route declaration: ${route}`);
      } else {
        findings.push(`backend/main.py contains route: ${route}`);
      }
    });

    if (!mainPyContent.includes("crewai_ingested_artifacts")) {
      errors.push(`backend/main.py does not reference crewai_ingested_artifacts database table`);
    } else {
      findings.push(`backend/main.py references crewai_ingested_artifacts`);
    }
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

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/crewai-ingestion-bridge-contract-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`CrewAI Ingestion Bridge Contract Audit completed with status: ${status}`);
  if (errors.length > 0) {
    console.error("Errors found during audit:", errors);
    process.exit(1);
  } else {
    console.log("All CrewAI Ingestion Bridge contract checks passed!");
    process.exit(0);
  }
}

runContractTest();
