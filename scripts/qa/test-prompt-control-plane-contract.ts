import * as fs from 'fs';
import * as path from 'path';

function runContractTests() {
  console.log("==================================================");
  console.log("PROMPT CONTROL PLANE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docsDir = path.join(baseDir, 'docs/prompt-control-plane');
  const configPath = path.join(baseDir, 'config/prompt_control_plane.json');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify docs files exist
  const expectedDocs = [
    '00_goal.md',
    '01_universal_agent_execution_contract.md',
    '02_prompt_router_policy.md',
    '03_human_approval_policy.md',
    '04_evidence_policy.md',
    '05_conmon_plan.md',
    '06_metrics.md',
    '07_prompt_audit_backlog.md',
    '08_production_roadmap.md',
    '09_cybersecurity_by_design.md',
    '10_ephemeral_pipeline_doctrine.md'
  ];

  for (const doc of expectedDocs) {
    const docPath = path.join(docsDir, doc);
    assert(fs.existsSync(docPath), `Doc file exists: docs/prompt-control-plane/${doc}`);
  }

  // 2. Verify config/prompt_control_plane.json exists and is valid JSON
  assert(fs.existsSync(configPath), "Config file exists: config/prompt_control_plane.json");

  let config: any = {};
  if (fs.existsSync(configPath)) {
    try {
      config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
      assert(true, "Config parses cleanly as JSON");
    } catch (e: any) {
      assert(false, `Config fails to parse as JSON: ${e.message}`);
    }
  }

  // 3. Verify specific config fields
  assert(config.name === "HOCH Agent Swarm Prompt Control Plane", "Config field 'name' is correct");
  assert(typeof config.version === 'string', "Config field 'version' exists");
  assert(config.production_status === "phase_1_governance_seed", "Config field 'production_status' is correct");
  assert(config.release_decision === "CONDITIONAL_GO_DOCUMENTATION_AND_CONFIG_ONLY", "Config field 'release_decision' is correct");
  assert(config.north_star_metric === "Validated Positive Production Outcomes Per Week", "Config field 'north_star_metric' is correct");

  assert(Array.isArray(config.domains) && config.domains.length > 0, "Config field 'domains' is non-empty");
  assert(Array.isArray(config.control_plane_nodes) && config.control_plane_nodes.length > 0, "Config field 'control_plane_nodes' is non-empty");
  assert(Array.isArray(config.source_prompt_library_files) && config.source_prompt_library_files.length > 0, "Config field 'source_prompt_library_files' is non-empty");
  assert(Array.isArray(config.allowed_autonomous_actions) && config.allowed_autonomous_actions.length > 0, "Config field 'allowed_autonomous_actions' is non-empty");
  assert(Array.isArray(config.human_approval_required_actions) && config.human_approval_required_actions.length > 0, "Config field 'human_approval_required_actions' is non-empty");
  assert(Array.isArray(config.prohibited_actions) && config.prohibited_actions.length > 0, "Config field 'prohibited_actions' is non-empty");
  assert(Array.isArray(config.fail_closed_triggers) && config.fail_closed_triggers.length > 0, "Config field 'fail_closed_triggers' is non-empty");
  assert(Array.isArray(config.prompt_routing_rules) && config.prompt_routing_rules.length > 0, "Config field 'prompt_routing_rules' is non-empty");
  assert(Array.isArray(config.evidence_required) && config.evidence_required.length > 0, "Config field 'evidence_required' is non-empty");

  // Conmon Cadence checks
  const cadence = config.conmon_cadence || {};
  assert(Array.isArray(cadence.daily) && cadence.daily.length > 0, "Daily ConMon tasks are non-empty");
  assert(Array.isArray(cadence.weekly) && cadence.weekly.length > 0, "Weekly ConMon tasks are non-empty");
  assert(Array.isArray(cadence.monthly) && cadence.monthly.length > 0, "Monthly ConMon tasks are non-empty");
  assert(Array.isArray(cadence.quarterly) && cadence.quarterly.length > 0, "Quarterly ConMon tasks are non-empty");

  // Key Metrics check
  const metrics = config.key_metrics || {};
  assert(Object.keys(metrics).length > 0, "Key metrics are non-empty");

  // Production Phases checks
  const phases = config.production_phases || [];
  assert(phases.length >= 10, `Production phases has at least 10 entries (found ${phases.length})`);

  // Cybersecurity frameworks check
  const frameworks = config.cybersecurity_frameworks || [];
  assert(frameworks.includes("NIST SSDF"), "Frameworks include NIST SSDF");
  assert(frameworks.includes("NIST AI RMF"), "Frameworks include NIST AI RMF");
  assert(frameworks.includes("OWASP LLM Top 10"), "Frameworks include OWASP LLM Top 10");
  assert(frameworks.includes("SLSA"), "Frameworks include SLSA");

  // Dashboard cards check
  assert(Array.isArray(config.dashboard_cards) && config.dashboard_cards.length > 0, "Dashboard cards are listed in config");

  // 4. Verify text content references in documentation files
  const contractPath = path.join(docsDir, '01_universal_agent_execution_contract.md');
  if (fs.existsSync(contractPath)) {
    const content = fs.readFileSync(contractPath, 'utf-8');
    assert(content.includes("Universal Agent Execution Contract") || content.includes("Universal Contract Wrapper"), "Universal Agent Execution Contract appears in docs");
    assert(content.includes("Michael Hoch") || content.includes("human confirmation"), "Michael Hoch approval gate appears in docs");
    assert(content.includes("fail-closed"), "fail-closed language appears in docs");
  }

  const designPath = path.join(docsDir, '09_cybersecurity_by_design.md');
  if (fs.existsSync(designPath)) {
    const content = fs.readFileSync(designPath, 'utf-8');
    assert(content.includes("Prompt Injection") || content.includes("injection"), "prompt injection appears in docs");
  }

  const evidencePath = path.join(docsDir, '04_evidence_policy.md');
  if (fs.existsSync(evidencePath)) {
    const content = fs.readFileSync(evidencePath, 'utf-8');
    assert(content.includes("evidence_manifest.json"), "evidence manifest appears in docs");
  }

  console.log("==================================================");
  if (failed) {
    console.error("PROMPT CONTROL PLANE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("PROMPT CONTROL PLANE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runContractTests();
