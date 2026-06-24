import fs from "node:fs";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";
const OUT_DIR = "artifacts/qa";

async function main() {
  console.log("==================================================");
  console.log("HOCHSTER RUNTIME EVIDENCE AUDIT VERIFICATION");
  console.log("==================================================");

  fs.mkdirSync(OUT_DIR, { recursive: true });
  
  try {
    const res = await fetch(`${BASE_URL}/api/v1/audit/runtime/execution`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const audit = await res.json();
    
    console.log("Runtime Execution Audit payload received:");
    console.log(JSON.stringify(audit, null, 2));

    const blockers = audit.blockers || [];
    
    // Additional sanity checks
    if (audit.tool_calls_checked > 0) {
      if (audit.tool_calls_with_trace < audit.tool_calls_checked) {
        blockers.push(`Not all tool calls are trace-linked: ${audit.tool_calls_with_trace}/${audit.tool_calls_checked}`);
      }
      if (audit.tool_calls_with_evidence < audit.tool_calls_checked) {
        blockers.push(`Not all tool calls have evidence: ${audit.tool_calls_with_evidence}/${audit.tool_calls_checked}`);
      }
    }
    
    if (audit.solved_without_validation > 0) {
      blockers.push(`Solve requests resolved without validation: ${audit.solved_without_validation}`);
    }
    
    if (audit.approval_bypass_findings?.length > 0) {
      blockers.push(`Approval gate bypasses detected: ${JSON.stringify(audit.approval_bypass_findings)}`);
    }

    const report = {
      timestamp: new Date().toISOString(),
      status: blockers.length === 0 ? "PASS" : "BLOCK",
      blockers,
      metrics: {
        tool_calls_checked: audit.tool_calls_checked,
        tool_calls_with_trace: audit.tool_calls_with_trace,
        tool_calls_with_evidence: audit.tool_calls_with_evidence,
        redactions_applied: audit.redactions_applied,
        solved_without_validation: audit.solved_without_validation,
        approval_required_actions: audit.approval_required_actions,
      }
    };

    fs.writeFileSync(`${OUT_DIR}/hochster-runtime-evidence-report.json`, JSON.stringify(report, null, 2), "utf8");
    console.log(`\nWrote ${OUT_DIR}/hochster-runtime-evidence-report.json`);
    console.log(`Audit status: ${report.status}`);

    if (report.status === "BLOCK") {
      console.error("\n [BLOCK] Runtime evidence verification failed!");
      process.exit(1);
    } else {
      console.log("\n [PASS] Runtime evidence verification succeeded!");
      process.exit(0);
    }
  } catch (err) {
    console.error("\n [FAIL] Audit verification request failed:", err);
    process.exit(1);
  }
}

main();
