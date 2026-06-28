import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';

function runEvidenceCollectorTests() {
  console.log("==================================================");
  console.log("EVIDENCE COLLECTOR CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const evidenceCollectorFile = path.join(baseDir, 'backend/evidence_collector.py');
  const mainFile = path.join(baseDir, 'backend/main.py');
  const reportFile = path.join(baseDir, 'artifacts/qa/evidence_collector/evidence_collector_report.json');
  const evidenceDir = path.join(baseDir, 'artifacts/evidence/missions');

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
  assert(fs.existsSync(evidenceCollectorFile), "Evidence collector file exists: backend/evidence_collector.py");
  assert(fs.existsSync(mainFile), "FastAPI main app file exists: backend/main.py");
  assert(fs.existsSync(reportFile), "Report file exists: artifacts/qa/evidence_collector/evidence_collector_report.json");

  // 2. Verify API routes are registered in main.py
  if (fs.existsSync(mainFile)) {
    const mainContent = fs.readFileSync(mainFile, 'utf-8');
    assert(mainContent.includes('/api/v1/evidence/mission'), "Route /api/v1/evidence/mission exists in main.py");
    assert(mainContent.includes('/api/v1/evidence/missions'), "Route /api/v1/evidence/missions exists in main.py");
    
    // Ensure no execution endpoints exist
    const hasExecutionEndpoint = mainContent.includes('/api/v1/prompts/execute') ||
                                 mainContent.includes('/api/v1/prompts/run') ||
                                 mainContent.includes('/api/v1/prompts/kickoff');
    assert(!hasExecutionEndpoint, "Safety check: No prompt execution endpoints exist");
  }

  // 3. Compile backend files to verify syntax
  try {
    execSync('python3 -m py_compile backend/main.py backend/evidence_collector.py backend/live_runtime_aggregator.py', { cwd: baseDir });
    assert(true, "Python syntax and import validation successful");
  } catch (e: any) {
    assert(false, `Python compile/import failed: ${e.message}`);
  }

  // 4. Test logic invariants using Python execution directly
  const runPythonCode = (code: string): string => {
    return execSync('python3', { input: code, cwd: baseDir }).toString().trim();
  };

  try {
    // A. Create a valid GO mission with validation and evidence
    const codeGo = `
import json
from backend.evidence_collector import EvidenceCollector
collector = EvidenceCollector()
payload = {
    "task_description": "Validate design schema conformance",
    "route_plan": {
        "mission_type": "AUDIT",
        "risk_level": "LOW",
        "selected_prompt_ids": ["AUD-001"],
        "selected_prompt_titles": ["Lead Auditor"],
        "human_approval_required": False
    },
    "validation_tests": ["schema_conformance_test"],
    "evidence_artifacts": ["design_spec_audit.json"]
}
res = collector.create_mission_package(payload)
print(json.dumps(res))
`;
    const resGo = JSON.parse(runPythonCode(codeGo));
    assert(resGo.mission_id !== undefined, "Mission package returns a valid mission_id");
    assert(resGo.release_decision === "GO", "Low-risk mission with validation and evidence yields GO");
    assert(resGo.execution_allowed === false, "Safety check: execution_allowed is false");
    assert(resGo.integrity.sha256 !== "", "Mission package contains a valid SHA-256 integrity hash");

    const missionFolder = path.join(evidenceDir, resGo.mission_id);
    assert(fs.existsSync(missionFolder), "Mission folder is created locally");
    assert(fs.existsSync(path.join(missionFolder, "mission.json")), "mission.json exists in mission folder");
    assert(fs.existsSync(path.join(missionFolder, "selected_prompts.json")), "selected_prompts.json exists");
    assert(fs.existsSync(path.join(missionFolder, "assumptions.md")), "assumptions.md exists");
    assert(fs.existsSync(path.join(missionFolder, "risks.md")), "risks.md exists");
    assert(fs.existsSync(path.join(missionFolder, "validation.md")), "validation.md exists");
    assert(fs.existsSync(path.join(missionFolder, "evidence_manifest.json")), "evidence_manifest.json exists");

    // B. Block GO without validation tests and evidence artifacts
    const codeNoGo = `
import json
from backend.evidence_collector import EvidenceCollector
collector = EvidenceCollector()
payload = {
    "task_description": "Validate design schema conformance",
    "route_plan": {
        "mission_type": "AUDIT",
        "risk_level": "LOW",
        "selected_prompt_ids": ["AUD-001"],
        "selected_prompt_titles": ["Lead Auditor"],
        "human_approval_required": False
    },
    "validation_tests": [],
    "evidence_artifacts": []
}
res = collector.create_mission_package(payload)
print(json.dumps(res))
`;
    const resNoGo = JSON.parse(runPythonCode(codeNoGo));
    assert(resNoGo.release_decision === "NO_GO", "Go is blocked without validation tests/evidence (resolves to NO_GO)");

    // C. FAIL_CLOSED cannot become GO
    const codeFailClosed = `
import json
from backend.evidence_collector import EvidenceCollector
collector = EvidenceCollector()
payload = {
    "task_description": "Critical bypass attempt",
    "route_plan": {
        "mission_type": "BYPASS",
        "risk_level": "FAIL_CLOSED",
        "selected_prompt_ids": ["AUD-001"],
        "selected_prompt_titles": ["Lead Auditor"],
        "human_approval_required": True,
        "fail_closed_triggers": ["bypass_detected"]
    },
    "validation_tests": ["test"],
    "evidence_artifacts": ["ev"]
}
res = collector.create_mission_package(payload)
print(json.dumps(res))
`;
    const resFailClosed = JSON.parse(runPythonCode(codeFailClosed));
    assert(resFailClosed.release_decision === "FAIL_CLOSED", "Bypass/FAIL_CLOSED risk level forces FAIL_CLOSED release decision");

    // D. Missing selected prompts triggers FAIL_CLOSED
    const codeMissingPrompts = `
import json
from backend.evidence_collector import EvidenceCollector
collector = EvidenceCollector()
payload = {
    "task_description": "Task without prompts",
    "route_plan": {
        "mission_type": "AUDIT",
        "risk_level": "LOW",
        "selected_prompt_ids": [],
        "selected_prompt_titles": [],
        "human_approval_required": False
    },
    "validation_tests": ["test"],
    "evidence_artifacts": ["ev"]
}
res = collector.create_mission_package(payload)
print(json.dumps(res))
`;
    const resMissingPrompts = JSON.parse(runPythonCode(codeMissingPrompts));
    assert(resMissingPrompts.release_decision === "FAIL_CLOSED", "Missing selected prompts triggers FAIL_CLOSED");

    // E. Approval-required mission without approval cannot be GO
    const codeNoApproval = `
import json
from backend.evidence_collector import EvidenceCollector
collector = EvidenceCollector()
payload = {
    "task_description": "Deploy to App Store",
    "route_plan": {
        "mission_type": "DEPLOY",
        "risk_level": "HIGH",
        "selected_prompt_ids": ["REL-001"],
        "selected_prompt_titles": ["Release Agent"],
        "human_approval_required": True
    },
    "approval_status": "PENDING",
    "validation_tests": ["test"],
    "evidence_artifacts": ["ev"]
}
res = collector.create_mission_package(payload)
print(json.dumps(res))
`;
    const resNoApproval = JSON.parse(runPythonCode(codeNoApproval));
    assert(resNoApproval.release_decision !== "GO", "Approval-required mission without approved status cannot be GO");

    // F. List and Detail APIs work
    const codeList = `
import json
from backend.evidence_collector import EvidenceCollector
collector = EvidenceCollector()
missions = collector.list_missions()
detail = collector.get_mission("${resGo.mission_id}")
print(json.dumps({"list_len": len(missions), "found_detail": detail is not None}))
`;
    const resList = JSON.parse(runPythonCode(codeList));
    assert(resList.list_len > 0, "List endpoint lists all created missions");
    assert(resList.found_detail === true, "Detail retrieval returns the requested mission payload");

  } catch (e: any) {
    assert(false, `Invariants execution test encountered error: ${e.message}`);
  }

  console.log("==================================================");
  if (failed) {
    console.error("EVIDENCE COLLECTOR CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("EVIDENCE COLLECTOR CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runEvidenceCollectorTests();
