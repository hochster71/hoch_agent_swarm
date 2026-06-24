import fs from "node:fs";
import { spawnSync } from "node:child_process";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";
const OUT_DIR = "artifacts/qa";

function runInDb(command: string): string {
  const res = spawnSync("python3", ["-c", command], {
    env: { ...process.env, PYTHONPATH: "." },
    encoding: "utf8"
  });
  if (res.status !== 0) {
    throw new Error(`Python failed: ${res.stderr}`);
  }
  return res.stdout.trim();
}

// Helper to evaluate a safety engine function directly from node
function evalSafetyFunc(funcName: string, arg: string): string {
  const cmd = `
from backend.remediation_safety import ${funcName}
print(${funcName}(r"""${arg}"""))
  `;
  return runInDb(cmd);
}

async function verifyAutonomyLevel(expectedLevel: string) {
  const res = await fetch(`${BASE_URL}/api/v1/readiness/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const payload = await res.json();
  const level = payload.data.autonomy_level;
  console.log(`Current Autonomy Level: ${level}`);
  if (level !== expectedLevel) {
    throw new Error(`Expected autonomy level ${expectedLevel}, got ${level}`);
  }
}

async function main() {
  console.log("==================================================");
  console.log("SLO-AWARE AUTONOMY & SQL AST RED-TEAM TEST SUITE");
  console.log("==================================================");

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const failures: string[] = [];

  // Define 20 static test cases for AST allowlist, side-effect guard, and deny-by-default
  const staticTests = [
    // 1. Safe update (Allowed)
    { patch: "UPDATE hochster_cluster_job_results SET status = 'pass' WHERE job_id = 'RT-001';", expectedRisk: "Low", ast: "True", side: "False" },
    // 2. Safe pragma timeout (Allowed)
    { patch: "PRAGMA busy_timeout = 30000;", expectedRisk: "Low", ast: "True", side: "False" },
    // 3. Safe pragma journal (Allowed)
    { patch: "PRAGMA journal_mode = WAL;", expectedRisk: "Low", ast: "True", side: "False" },
    // 4. Safe pragma synchronous (Allowed)
    { patch: "PRAGMA synchronous = NORMAL;", expectedRisk: "Low", ast: "True", side: "False" },
    // 5. Echo command (Allowed, but side-effect guard flags it)
    { patch: "ECHO 'hello';", expectedRisk: "Low", ast: "False", side: "True" },
    // 6. SQL injection with drop (Blocked)
    { patch: "UPDATE hochster_cluster_job_results SET status = 'pass'; DROP TABLE hochster_incidents;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 7. SQL injection with union (Blocked)
    { patch: "UPDATE hochster_cluster_job_results SET status = 'pass' UNION SELECT username FROM users;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 8. SQL injection with comments -- (Blocked)
    { patch: "UPDATE hochster_cluster_job_results SET status = 'pass' -- WHERE job_id = 'RT-001';", expectedRisk: "Critical", ast: "False", side: "True" },
    // 9. SQL injection with comments /* (Blocked)
    { patch: "UPDATE hochster_cluster_job_results SET status = 'pass' /* comment */;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 10. Dangerous SELECT statement (Blocked)
    { patch: "SELECT * FROM hochster_incidents;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 11. Dangerous INSERT statement (Blocked)
    { patch: "INSERT INTO hochster_incidents (incident_id) VALUES ('test');", expectedRisk: "Critical", ast: "False", side: "True" },
    // 12. Dangerous DELETE statement (Blocked)
    { patch: "DELETE FROM hochster_cluster_job_results;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 13. Dangerous ALTER statement (Blocked)
    { patch: "ALTER TABLE hochster_incidents ADD COLUMN test TEXT;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 14. Dangerous ATTACH statement (Blocked)
    { patch: "ATTACH DATABASE 'test.db' AS test;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 15. Subquery injection (Blocked)
    { patch: "UPDATE hochster_cluster_job_results SET status = (SELECT status FROM hochster_incidents LIMIT 1);", expectedRisk: "Critical", ast: "False", side: "True" },
    // 16. Out-of-bounds pragma value (Blocked)
    { patch: "PRAGMA busy_timeout = 999999;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 17. Unrecognized pragma (Blocked)
    { patch: "PRAGMA foreign_keys = ON;", expectedRisk: "Critical", ast: "False", side: "True" },
    // 18. Target wrong table (Blocked)
    { patch: "UPDATE other_table SET status = 'pass';", expectedRisk: "Critical", ast: "False", side: "True" },
    // 19. Target wrong column (Blocked)
    { patch: "UPDATE hochster_cluster_job_results SET instance = 'test' WHERE job_id = 'RT-001';", expectedRisk: "Critical", ast: "False", side: "True" },
    // 20. Dangerous filesystem shell execution (Blocked / Side-effect flag)
    { patch: "rm -rf /", expectedRisk: "Critical", ast: "False", side: "True" },
  ];

  console.log("\n--- RUNNING 20 STATIC SAFETY ENGINE ASSERTIONS ---");
  staticTests.forEach((t, index) => {
    const id = index + 1;
    try {
      const risk = evalSafetyFunc("classify_remediation_risk", t.patch);
      const astVal = evalSafetyFunc("is_sql_remediation_allowed", t.patch);
      const sideVal = evalSafetyFunc("has_external_side_effects", t.patch);

      console.log(`[Case #${id}] Patch: "${t.patch.slice(0, 50)}..."`);
      console.log(`         Risk: ${risk} (Expected: ${t.expectedRisk})`);
      console.log(`         SQL Allowed: ${astVal} (Expected: ${t.ast})`);
      console.log(`         Side Effects: ${sideVal} (Expected: ${t.side})`);

      if (risk !== t.expectedRisk) failures.push(`Case #${id} Risk mismatch: got ${risk}`);
      if (astVal !== t.ast) failures.push(`Case #${id} AST mismatch: got ${astVal}`);
      if (sideVal !== t.side) failures.push(`Case #${id} Side effects mismatch: got ${sideVal}`);
    } catch (err: any) {
      failures.push(`Case #${id} threw error: ${err.message}`);
    }
  });

  // End-to-end integration and throttle test cases (Cases 21-25)
  console.log("\n--- RUNNING 5 INTEGRATION & THROTTLING ASSERTIONS ---");
  try {
    // Clean up database state first
    runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM hochster_readiness_reports")
conn.execute("DELETE FROM hochster_incidents WHERE incident_id LIKE 'test_%'")
conn.execute("UPDATE hochster_cluster_job_results SET status = 'pass' WHERE job_id = 'RT-001';")
conn.commit()
conn.close()
    `);

    // Case 21: Healthy Budget (L4 Autonomy)
    console.log("\n[Case #21] Simulating 10 healthy readiness reports (Score 100)...");
    for (let i = 0; i < 10; i++) {
      runInDb(`
from backend.runtime_execution_store import persist_readiness_report
persist_readiness_report("rep_t21_" + str(${i}), 100, {}, "PASS", False, [])
      `);
    }
    const tickRes = await fetch(`${BASE_URL}/api/v1/readiness/diagnose`, { method: "POST" });
    if (!tickRes.ok) throw new Error("Failed to tick status");
    await verifyAutonomyLevel("L4");

    // Case 22: Low-Risk autonomous execution allowed under L4
    console.log("\n[Case #22] Triggering Low-risk patch under L4...");
    runInDb(`
from backend.runtime_execution_store import persist_incident
persist_incident(
    incident_id="test_t22_autonomy",
    category="Database Lock Risk",
    severity="Low",
    findings=["SQLite busy_timeout low"],
    remediation_patch="PRAGMA busy_timeout=30000;",
    rollback_plan="PRAGMA busy_timeout=0;",
    status="active",
    risk_level="Low",
    blast_radius=["database"],
    state="detected"
)
    `);
    let remRes = await fetch(`${BASE_URL}/api/v1/readiness/remediate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: "test_t22_autonomy" })
    });
    let remData = await remRes.json();
    console.log("Remediate response:", remData);
    if (remData.remediated_count !== 1) {
      failures.push("Case #22: Expected autonomous execution to succeed (remediated_count = 1)");
    }

    // Case 23: High incident severity blocks autonomous execution under L4
    console.log("\n[Case #23] Triggering High-severity Low-risk patch under L4 (Should require approval)...");
    runInDb(`
from backend.runtime_execution_store import persist_incident
persist_incident(
    incident_id="test_t23_severity",
    category="Database Lock Risk",
    severity="High",
    findings=["SQLite busy_timeout low"],
    remediation_patch="PRAGMA busy_timeout=30000;",
    rollback_plan="PRAGMA busy_timeout=0;",
    status="active",
    risk_level="Low",
    blast_radius=["database"],
    state="detected"
)
    `);
    remRes = await fetch(`${BASE_URL}/api/v1/readiness/remediate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: "test_t23_severity" })
    });
    remData = await remRes.json();
    console.log("Remediate response:", remData);
    const blockedBySev = remData.findings.some((f: string) => f.includes("Blocked") && f.includes("operator approval"));
    if (!blockedBySev) {
      failures.push("Case #23: Expected High-severity to block autonomous remediation");
    }

    // Case 24: Degraded Budget (L1/L2 Throttling)
    console.log("\n[Case #24] Simulating 10 degraded reports (Score 80) to consume error budget...");
    for (let i = 0; i < 10; i++) {
      runInDb(`
from backend.runtime_execution_store import persist_readiness_report
persist_readiness_report("rep_t24_" + str(${i}), 80, {}, "BLOCK", True, ["Anomalies"])
      `);
    }
    const tickRes2 = await fetch(`${BASE_URL}/api/v1/readiness/diagnose`, { method: "POST" });
    if (!tickRes2.ok) throw new Error("Failed to tick status");
    // Verify autonomy throttled to L1/L2
    await verifyAutonomyLevel("L1/L2");

    // Case 25: Low-Risk remediation blocked under L1/L2
    console.log("\n[Case #25] Triggering Low-risk patch under throttled L1/L2 (Should be blocked)...");
    runInDb(`
from backend.runtime_execution_store import persist_incident
persist_incident(
    incident_id="test_t25_throttle",
    category="Database Lock Risk",
    severity="Low",
    findings=["SQLite busy_timeout low"],
    remediation_patch="PRAGMA busy_timeout=30000;",
    rollback_plan="PRAGMA busy_timeout=0;",
    status="active",
    risk_level="Low",
    blast_radius=["database"],
    state="detected"
)
    `);
    remRes = await fetch(`${BASE_URL}/api/v1/readiness/remediate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: "test_t25_throttle" })
    });
    remData = await remRes.json();
    console.log("Remediate response:", remData);
    const blockedByThrottle = remData.findings.some((f: string) => f.includes("Blocked") && f.includes("Autonomy Level: L1/L2"));
    if (!blockedByThrottle) {
      failures.push("Case #25: Expected L1/L2 throttle to block autonomous remediation");
    }

    // Clean up
    runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM hochster_readiness_reports WHERE report_id LIKE 'rep_t2%'")
conn.execute("DELETE FROM hochster_incidents WHERE incident_id LIKE 'test_t2%'")
conn.commit()
conn.close()
    `);
    
    // Tidy up daemon tick scorecard
    await fetch(`${BASE_URL}/api/v1/readiness/diagnose`, { method: "POST" });

  } catch (err: any) {
    failures.push(`Integration tests threw error: ${err.message}`);
  }

  // Create report
  const report = {
    report_id: `qa_autonomy_budget_${Date.now()}`,
    status: failures.length === 0 ? "PASS" : "BLOCK",
    failures,
    timestamp: new Date().toISOString()
  };

  const outputPath = `${OUT_DIR}/autonomy-budget-audit.json`;
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2), "utf8");
  console.log(`\nWrote ${outputPath}`);
  console.log(`Autonomy Budget Audit status: ${report.status}`);

  if (report.status === "BLOCK") {
    console.error("\n [BLOCK] Autonomy budget validation failed!");
    console.error(failures);
    process.exit(1);
  } else {
    console.log("\n [PASS] Autonomy budget validation succeeded!");
    process.exit(0);
  }
}

main();
