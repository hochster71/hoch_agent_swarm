import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

function runApprovalGateTests() {
  console.log("==================================================");
  console.log("APPROVAL GATE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const approvalGateFile = path.join(baseDir, 'backend/approval_gate.py');
  const mainFile = path.join(baseDir, 'backend/main.py');
  const queueFile = path.join(baseDir, 'artifacts/approvals/queue.json');
  const reportFile = path.join(baseDir, 'artifacts/qa/approval_gate/approval_gate_report.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify files exist
  assert(fs.existsSync(approvalGateFile), "Approval gate file exists: backend/approval_gate.py");
  assert(fs.existsSync(mainFile), "FastAPI main app file exists: backend/main.py");

  // 2. Verify API routes are registered in main.py
  if (fs.existsSync(mainFile)) {
    const mainContent = fs.readFileSync(mainFile, 'utf-8');
    assert(mainContent.includes('/api/v1/approvals/queue'), "Route /api/v1/approvals/queue exists in main.py");
    assert(mainContent.includes('/api/v1/approvals/request'), "Route /api/v1/approvals/request exists in main.py");
    assert(mainContent.includes('/api/v1/approvals/{approval_id}/decision'), "Route /api/v1/approvals/{approval_id}/decision exists in main.py");
    
    // Ensure no execution endpoints exist
    const hasExecutionEndpoint = mainContent.includes('/api/v1/prompts/execute') ||
                                 mainContent.includes('/api/v1/prompts/run') ||
                                 mainContent.includes('/api/v1/prompts/kickoff') ||
                                 mainContent.includes('/api/v1/prompts/evaluate/execute');
    assert(!hasExecutionEndpoint, "Safety check: No prompt execution endpoints exist");
  }

  // 3. Compile backend files to verify syntax
  try {
    execSync('python3 -m py_compile backend/main.py backend/approval_gate.py backend/live_runtime_aggregator.py', { cwd: baseDir });
    assert(true, "Python syntax and import validation successful");
  } catch (e: any) {
    assert(false, `Python compile/import failed: ${e.message}`);
  }

  // 4. Test request endpoint creation and decision recording using Python API directly
  const runPythonCode = (code: string): string => {
    return execSync('python3', { input: code, cwd: baseDir }).toString().trim();
  };

  // Clean queue before running tests to prevent collision
  if (fs.existsSync(queueFile)) {
    fs.unlinkSync(queueFile);
  }

  try {
    // A. Request endpoint creates approval object
    const createCode = `
import json
from backend.approval_gate import get_approval_gate
gate = get_approval_gate()
plan = {
    "mission_type": "CODING",
    "risk_level": "HIGH",
    "selected_prompt_ids": ["CODE-001"],
    "selected_prompt_titles": ["Principal Software Architect"],
    "human_approval_required": True,
    "blocked_actions": [],
    "fail_closed_triggers": []
}
res = gate.create_request("Deploy visual mockups to cluster", plan)
print(json.dumps(res))
`;
    const res = JSON.parse(runPythonCode(createCode));
    assert(res.approval_id !== undefined, "Approval request creation returns valid approval_id");
    assert(res.status === "PENDING", "Created approval status defaults to PENDING");
    assert(res.execution_allowed_after_approval === false, "Safety check: execution_allowed_after_approval is false");

    const appId = res.approval_id;

    // B. Queue endpoint returns pending approvals
    const queueCode = `
import json
from backend.approval_gate import get_approval_gate
gate = get_approval_gate()
print(json.dumps(gate.load_queue()))
`;
    const queue = JSON.parse(runPythonCode(queueCode));
    assert(queue.length > 0, "Queue lists the pending approval request");
    assert(queue[0].approval_id === appId, "Enqueued request matches the requested ID");

    // C. Decision endpoint records APPROVED/DENIED/DEFERRED with valid signature
    const approveCode = `
import json
import tempfile
import subprocess
from pathlib import Path
from backend.approval_gate import get_approval_gate
import backend.mission_control.founder_signer as signer

with tempfile.TemporaryDirectory() as td:
    key_path = Path(td) / "test_key"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-C", "founder@hoch-has", "-f", str(key_path)], check=True)
    pub = Path(td) / "test_key.pub"
    parts = pub.read_text().split()
    allowed_signers = Path(td) / "allowed_signers"
    allowed_signers.write_text(f'founder@hoch-has namespaces="has-approval" {parts[0]} {parts[1]}\\n')
    
    signer.ALLOWED_SIGNERS = allowed_signers
    
    gate = get_approval_gate()
    queue = gate.load_queue()
    target = [app for app in queue if app["approval_id"] == "${appId}"][0]
    
    target_for_sig = target.copy()
    target_for_sig["status"] = "APPROVED"
    target_for_sig["decision_at"] = "2026-07-02T21:00:00+00:00"
    target_for_sig["decision_note"] = "Approved for preview deployment"
    
    sig = signer.sign_approval(target_for_sig, key_path)
    
    res = gate.record_decision("${appId}", "APPROVED", "Approved for preview deployment", founder_signature=sig, founder_decision_at=target_for_sig["decision_at"])
    print(json.dumps(res))
`;
    const approvedObj = JSON.parse(runPythonCode(approveCode));
    assert(approvedObj.status === "APPROVED", "Decision recording sets status to APPROVED");
    assert(approvedObj.execution_allowed_after_approval === false, "Safety check: execution_allowed_after_approval remains false after APPROVED");
    assert(approvedObj.decision_note === "Approved for preview deployment", "Decision note is saved");

    // Verify decision evidence is written to disk
    const decisionFilePath = path.join(baseDir, `artifacts/approvals/decisions/decision_${appId}.json`);
    assert(fs.existsSync(decisionFilePath), `Individual decision JSON file written to ${decisionFilePath}`);

    // D. FAIL_CLOSED approval cannot be approved into execution
    const failClosedCreateCode = `
import json
from backend.approval_gate import get_approval_gate
gate = get_approval_gate()
plan = {
    "mission_type": "AMBIGUOUS",
    "risk_level": "FAIL_CLOSED",
    "selected_prompt_ids": [],
    "selected_prompt_titles": [],
    "human_approval_required": True,
    "blocked_actions": ["TASK_EXECUTION_BLOCKED"],
    "fail_closed_triggers": ["BYPASS_APPROVAL_ATTEMPTED"]
}
res = gate.create_request("Force bypass check", plan)
print(json.dumps(res))
`;
    const fcRes = JSON.parse(runPythonCode(failClosedCreateCode));
    const fcId = fcRes.approval_id;
    assert(fcRes.status === "FAIL_CLOSED", "Fail-closed plan request creates approval with status=FAIL_CLOSED");

    const fcApproveCode = `
import json
from backend.approval_gate import get_approval_gate
gate = get_approval_gate()
try:
    gate.record_decision("${fcId}", "APPROVED", "Try force approve")
    print("SUCCESS")
except Exception as e:
    print("FAILED: " + str(e))
`;
    const fcApproveResult = runPythonCode(fcApproveCode);
    assert(fcApproveResult.startsWith("FAILED"), "Safety check: FAIL_CLOSED approval cannot be approved into execution");

    // E. Telemetry contains all states
    const telemetryCode = `
import json
from backend.approval_gate import get_approval_gate
gate = get_approval_gate()
print(json.dumps(gate.get_telemetry()))
`;
    const tel = JSON.parse(runPythonCode(telemetryCode));
    assert(tel.state === "FAIL_CLOSED", "Telemetry detects FAIL_CLOSED status in enqueued requests");
    assert(tel.approved_count === 1, "Telemetry reports approved count correctly");
    assert(tel.execution_enabled === false, "Telemetry reports execution_enabled=false");

  } catch (e: any) {
    assert(false, `Subprocess API test execution failed: ${e.message}`);
  }

  // 5. Verify QA artifact approval_gate_report.json is written
  assert(fs.existsSync(reportFile), "QA artifact report exists: artifacts/qa/approval_gate/approval_gate_report.json");

  console.log("==================================================");
  if (failed) {
    console.error("APPROVAL GATE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("APPROVAL GATE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runApprovalGateTests();
