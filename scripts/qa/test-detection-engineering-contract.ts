import fs from "node:fs";
import path from "node:path";

const blockers: string[] = [];

// 1. Verify backend/detection_events.py exists
if (!fs.existsSync("backend/detection_events.py")) {
  blockers.push("Missing backend/detection_events.py");
}

// 2. Verify main.py has API endpoints for detections
if (fs.existsSync("backend/main.py")) {
  const mainPy = fs.readFileSync("backend/main.py", "utf8");
  const requiredEndpoints = [
    "/api/v1/detections/events",
    "/api/v1/detections/rules",
    "/api/v1/detections/health"
  ];
  for (const ep of requiredEndpoints) {
    if (!mainPy.includes(ep)) {
      blockers.push(`Missing API endpoint in main.py: ${ep}`);
    }
  }
} else {
  blockers.push("Missing backend/main.py");
}

// 3. Verify Splunk rules exist
const splunkRules = [
  "delta_tier_privilege_escalation.spl",
  "approval_replay_or_bruteforce.spl",
  "test_approval_misuse.spl",
  "google_frontier_policy_block.spl",
  "local_model_outage_surge.spl"
];
for (const file of splunkRules) {
  if (!fs.existsSync(path.join("detections/splunk", file))) {
    blockers.push(`Missing Splunk rule: detections/splunk/${file}`);
  }
}

// 4. Verify Sigma rules exist
const sigmaRules = [
  "delta_tier_privilege_escalation.yml",
  "approval_replay_or_bruteforce.yml",
  "test_approval_misuse.yml",
  "google_frontier_policy_block.yml",
  "local_model_outage_surge.yml"
];
for (const file of sigmaRules) {
  if (!fs.existsSync(path.join("detections/sigma", file))) {
    blockers.push(`Missing Sigma rule: detections/sigma/${file}`);
  }
}

// 5. Verify Elastic rules exist
const elasticRules = [
  "fail_closed_blocks.kql",
  "rationale_evasion.kql",
  "google_frontier_block.kql"
];
for (const file of elasticRules) {
  if (!fs.existsSync(path.join("detections/elastic", file))) {
    blockers.push(`Missing Elastic rule: detections/elastic/${file}`);
  }
}

// 6. Verify LogQL rules exist
const logqlRules = [
  "fail_closed_blocks.logql",
  "local_model_outage_surge.logql"
];
for (const file of logqlRules) {
  if (!fs.existsSync(path.join("detections/logql", file))) {
    blockers.push(`Missing LogQL rule: detections/logql/${file}`);
  }
}

// 7. Verify response playbooks exist
const playbooks = [
  "delta_tier_privilege_escalation.md",
  "approval_replay_or_bruteforce.md",
  "rationale_evasion.md",
  "google_frontier_policy_block.md",
  "local_model_outage_surge.md"
];
for (const file of playbooks) {
  if (!fs.existsSync(path.join("detections/playbooks", file))) {
    blockers.push(`Missing playbook: detections/playbooks/${file}`);
  }
}

// 8. Verify fixtures exist
const fixtures = [
  "delta_tier_privilege_escalation.jsonl",
  "approval_replay_or_bruteforce.jsonl",
  "test_approval_misuse.jsonl",
  "google_frontier_policy_block.jsonl",
  "local_model_outage_surge.jsonl"
];
for (const file of fixtures) {
  if (!fs.existsSync(path.join("detections/fixtures", file))) {
    blockers.push(`Missing fixture: detections/fixtures/${file}`);
  }
}

const reportPath = "artifacts/qa/detection-engineering-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length) {
  console.error("Detection Engineering Contract FAILED!");
  process.exit(1);
} else {
  console.log("Detection Engineering Contract PASSED!");
  process.exit(0);
}
