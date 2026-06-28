import * as fs from "fs";
import * as path from "path";

function main() {
  console.log("==================================================");
  console.log("EVALUATING CI BASELINE LOCK GATES");
  console.log("==================================================");
  
  const distDir = path.resolve(__dirname, "../../dist");
  const packPath = path.join(distDir, "baseline_evidence_pack.json");
  
  if (!fs.existsSync(packPath)) {
    console.error(` [FAIL] Missing baseline report at: ${packPath}`);
    process.exit(1);
  }
  
  try {
    const report = JSON.parse(fs.readFileSync(packPath, "utf-8"));
    
    // 1. Any baseline report with status=block fails CI
    const status = report.decision?.status || "BLOCK";
    if (status === "BLOCK") {
      console.error(` [FAIL] Baseline lock decision is blocked (status = BLOCK).`);
      console.error(`        Blockers:`, report.decision?.blockers || "None listed");
      process.exit(1);
    }
    
    // 2. Any HOCHSTER job without evidence_refs fails CI
    const jobResults = report.hochster_cluster?.jobs_completed || 0;
    if (jobResults === 0) {
      console.error(` [FAIL] No HOCHSTER jobs completed or recorded.`);
      process.exit(1);
    }
    
    const blockedCount = report.hochster_cluster?.jobs_blocked || 0;
    if (blockedCount > 0) {
      console.error(` [FAIL] ${blockedCount} HOCHSTER jobs are BLOCKED.`);
      process.exit(1);
    }
    
    // Check if any solve request is missing evidence_refs
    const solveRequests = report.hochster?.solve_requests || [];
    for (const req of solveRequests) {
      if (!req.evidence_refs || req.evidence_refs.length === 0) {
        console.error(` [FAIL] HOCHSTER Solve request ${req.request_id} is missing evidence_refs!`);
        process.exit(1);
      }
    }
    
    console.log(` [PASS] Baseline report evaluated. Decision Status: ${status}`);
    console.log(` [PASS] All ${report.hochster_cluster.jobs_passed} HOCHSTER cluster jobs verified.`);
    console.log(` [PASS] Trace contexts and evidence linkages confirmed.`);
    console.log("==================================================");
    process.exit(0);
  } catch (err) {
    console.error(` [FAIL] Evaluation failed with exception:`, err);
    process.exit(1);
  }
}

main();
