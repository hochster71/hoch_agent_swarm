import fs from "node:fs";
import { spawnSync } from "node:child_process";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";
const OUT_DIR = "artifacts/qa";

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Helper to execute Python functions to query or update database via subprocess
function runInDb(command: string): string {
  const res = spawnSync("python3", ["-c", command], {
    env: { ...process.env, PYTHONPATH: "." },
    encoding: "utf8"
  });
  if (res.error) {
    console.error(`Subprocess error: ${res.error.message}`);
    throw res.error;
  }
  if (res.status !== 0) {
    console.error(`Python script failed with code ${res.status}`);
    console.error(`Stderr: ${res.stderr}`);
    throw new Error(`Python failed: ${res.stderr}`);
  }
  return res.stdout.trim();
}

async function verifyScore(expectedScore: number) {
  const res = await fetch(`${BASE_URL}/api/v1/readiness/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const payload = await res.json();
  const score = payload.data.readiness_score;
  console.log(`Current readiness score: ${score}`);
  if (score !== expectedScore) {
    throw new Error(`Expected score ${expectedScore}, got ${score}`);
  }
}

async function main() {
  console.log("==================================================");
  console.log("REMEDIATION SAFETY GATES RED-TEAM TEST SUITE");
  console.log("==================================================");

  fs.mkdirSync(OUT_DIR, { recursive: true });

  const failures: string[] = [];

  try {
    // 0. Ensure database initialized and initial score is 100
    console.log("\n--- PRE-TEST INTEGRITY CHECK ---");
    // Clean up any stale test incidents and restore RT-001 status to pass
    runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM hochster_incidents WHERE incident_id LIKE 'test_%'")
conn.execute("UPDATE hochster_cluster_job_results SET status = 'pass' WHERE job_id = 'RT-001';")
conn.execute("PRAGMA busy_timeout=30000;")
conn.commit()
conn.close()
    `);
    
    // Trigger tick to ensure scorecard is 100/100
    const diagRes = await fetch(`${BASE_URL}/api/v1/readiness/diagnose`, { method: "POST" });
    if (!diagRes.ok) throw new Error("Failed to trigger diagnosis tick");
    await verifyScore(100);

    // 1. TEST CASE 1: Low-risk remediation executes successfully
    console.log("\n--- TEST CASE 1: Low-Risk Remediation Success ---");
    runInDb(`
from backend.runtime_execution_store import persist_incident
persist_incident(
    incident_id="test_low_risk_success",
    category="Database Lock Risk",
    severity="Low",
    findings=["SQLite busy_timeout is below 30000ms"],
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
      body: JSON.stringify({ incident_id: "test_low_risk_success" })
    });
    if (!remRes.ok) throw new Error("Failed call to /remediate");
    let remData = await remRes.json();
    console.log("Remediate response:", JSON.stringify(remData, null, 2));

    if (remData.remediated_count !== 1) {
      failures.push("TC1: Expected remediated_count = 1");
    }

    // Verify incident state in database
    const stateTC1 = runInDb(`
import sqlite3, json
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT state, status FROM hochster_incidents WHERE incident_id = 'test_low_risk_success'").fetchone()
conn.close()
print(json.dumps(dict(row)))
    `);
    console.log("TC1 incident state in DB:", stateTC1);
    const stateObj1 = JSON.parse(stateTC1);
    if (stateObj1.state !== "remediated" || stateObj1.status !== "remediated") {
      failures.push(`TC1: Expected state=remediated, status=remediated. Got: ${stateTC1}`);
    }

    // 2. TEST CASE 2: High-risk remediation blocked by policy
    console.log("\n--- TEST CASE 2: High-Risk Remediation Blocked by Policy ---");
    runInDb(`
from backend.runtime_execution_store import persist_incident
persist_incident(
    incident_id="test_high_risk_blocked",
    category="Worker Degradation",
    severity="High",
    findings=["Worker node offline or degraded"],
    remediation_patch="python3 -m scripts.qa.restart_worker",
    rollback_plan="echo 'rollback worker restart'",
    status="active",
    risk_level="Medium",
    blast_radius=["worker"],
    state="detected"
)
    `);

    remRes = await fetch(`${BASE_URL}/api/v1/readiness/remediate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: "test_high_risk_blocked" })
    });
    if (!remRes.ok) throw new Error("Failed call to /remediate");
    remData = await remRes.json();
    console.log("Remediate response:", JSON.stringify(remData, null, 2));

    const isBlocked = remData.findings.some((f: string) => f.includes("Blocked") && f.includes("requires explicit approval"));
    if (!isBlocked) {
      failures.push("TC2: Expected remediation to be blocked by policy");
    }

    // Verify incident state transitioned to "proposed"
    const stateTC2 = runInDb(`
import sqlite3, json
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT state, status FROM hochster_incidents WHERE incident_id = 'test_high_risk_blocked'").fetchone()
conn.close()
print(json.dumps(dict(row)))
    `);
    console.log("TC2 incident state in DB:", stateTC2);
    const stateObj2 = JSON.parse(stateTC2);
    if (stateObj2.state !== "proposed" || stateObj2.status !== "active") {
      failures.push(`TC2: Expected state=proposed, status=active. Got: ${stateTC2}`);
    }

    // 3. TEST CASE 3: Auto-rollback on score degradation
    console.log("\n--- TEST CASE 3: Auto-Rollback on Score Degradation ---");
    runInDb(`
from backend.runtime_execution_store import persist_incident
persist_incident(
    incident_id="test_auto_rollback",
    category="Telemetry Drift",
    severity="Low",
    findings=["HOCHSTER jobs blocked: 1"],
    remediation_patch="UPDATE hochster_cluster_job_results SET status = 'block' WHERE job_id = 'RT-001';",
    rollback_plan="UPDATE hochster_cluster_job_results SET status = 'pass' WHERE job_id = 'RT-001';",
    status="active",
    risk_level="Low",
    blast_radius=["telemetry"],
    state="detected"
)
    `);

    remRes = await fetch(`${BASE_URL}/api/v1/readiness/remediate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: "test_auto_rollback" })
    });
    if (!remRes.ok) throw new Error("Failed call to /remediate");
    remData = await remRes.json();
    console.log("Remediate response:", JSON.stringify(remData, null, 2));

    const hasRollbackWarning = remData.findings.some((f: string) => f.includes("degraded") && f.includes("Triggering auto-rollback"));
    if (!hasRollbackWarning) {
      failures.push("TC3: Expected auto-rollback warning in findings");
    }

    // Verify database has been rolled back and incident is active with state="rolled_back"
    const stateTC3 = runInDb(`
import sqlite3, json
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT state, status FROM hochster_incidents WHERE incident_id = 'test_auto_rollback'").fetchone()
conn.close()
print(json.dumps(dict(row)))
    `);
    console.log("TC3 incident state in DB:", stateTC3);
    const stateObj3 = JSON.parse(stateTC3);
    if (stateObj3.state !== "rolled_back" || stateObj3.status !== "active") {
      failures.push(`TC3: Expected state=rolled_back, status=active. Got: ${stateTC3}`);
    }

    // Verify job status has been restored to pass
    const statusTC3 = runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
status = conn.execute("SELECT status FROM hochster_cluster_job_results WHERE job_id = 'RT-001'").fetchone()[0]
conn.close()
print(status)
    `);
    console.log("Job status after rollback:", statusTC3);
    if (statusTC3 !== "pass") {
      failures.push(`TC3: Expected job status = pass, got ${statusTC3}`);
    }

    // Verify the score remains 100 after the rollback restored the state
    await verifyScore(100);

    // 4. TEST CASE 4: Manual Rollback
    console.log("\n--- TEST CASE 4: Manual Rollback Endpoint ---");
    // Manually run a bad patch to degrade the DB state again (outside of remediator flow)
    runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.execute("UPDATE hochster_cluster_job_results SET status = 'block' WHERE job_id = 'RT-001';")
conn.commit()
conn.close()
    `);
    
    // Verify score has degraded
    const diagRes2 = await fetch(`${BASE_URL}/api/v1/readiness/diagnose`, { method: "POST" });
    if (!diagRes2.ok) throw new Error("Failed to trigger diagnosis tick");
    await verifyScore(85);

    // Run manual rollback
    const rbRes = await fetch(`${BASE_URL}/api/v1/readiness/rollback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ incident_id: "test_auto_rollback" })
    });
    if (!rbRes.ok) throw new Error("Failed call to /rollback");
    const rbData = await rbRes.json();
    console.log("Rollback response:", JSON.stringify(rbData, null, 2));

    // Verify DB restored to pass
    const statusTC4 = runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
status = conn.execute("SELECT status FROM hochster_cluster_job_results WHERE job_id = 'RT-001'").fetchone()[0]
conn.close()
print(status)
    `);
    console.log("Job status after manual rollback:", statusTC4);
    if (statusTC4 !== "pass") {
      failures.push(`TC4: Expected job status = pass, got ${statusTC4}`);
    }

    // Verify score restored to 100
    await verifyScore(100);

    // Clean up
    runInDb(`
import sqlite3
from backend.hochster_cluster import DB_PATH
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM hochster_incidents WHERE incident_id LIKE 'test_%'")
conn.commit()
conn.close()
    `);
    console.log("\n--- Cleaned up test incidents. ---");

  } catch (err: any) {
    failures.push(`Unhandled error: ${err.message}`);
  }

  // Create report
  const report = {
    report_id: `qa_remediation_safety_${Date.now()}`,
    status: failures.length === 0 ? "PASS" : "BLOCK",
    failures,
    timestamp: new Date().toISOString()
  };

  const outputPath = `${OUT_DIR}/remediation-safety-audit.json`;
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2), "utf8");
  console.log(`\nWrote ${outputPath}`);
  console.log(`Remediation Safety Audit status: ${report.status}`);

  if (report.status === "BLOCK") {
    console.error("\n [BLOCK] Remediation safety validation failed!");
    console.error(failures);
    process.exit(1);
  } else {
    console.log("\n [PASS] Remediation safety validation succeeded!");
    process.exit(0);
  }
}

main();
