import * as fs from 'fs';
import * as path from 'path';

function runVisualContractTests() {
  console.log("==================================================");
  console.log("VISUAL CONTROL PLANE CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const docsDir = path.join(baseDir, 'docs/visual-control-plane');
  const configPath = path.join(baseDir, 'config/visual_control_plane.json');

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
    '00_visual_north_star.md',
    '01_design_system.md',
    '02_page_map.md',
    '03_component_inventory.md',
    '04_agent_visual_language.md',
    '05_dashboard_cards.md',
    '06_graphics_and_motion.md',
    '07_accessibility_and_dark_theme.md',
    '08_implementation_roadmap.md',
    '09_visual_qa_checklist.md',
    '10_prompt_to_generate_mockups.md'
  ];

  for (const doc of expectedDocs) {
    const docPath = path.join(docsDir, doc);
    assert(fs.existsSync(docPath), `Doc file exists: docs/visual-control-plane/${doc}`);
  }

  // 2. Verify config/visual_control_plane.json exists and is valid JSON
  assert(fs.existsSync(configPath), "Config file exists: config/visual_control_plane.json");

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
  assert(config.name === "HOCH Agent Swarm Visual Control Plane Config", "Config field 'name' is correct");
  assert(Array.isArray(config.routes) && config.routes.length > 0, "Config field 'routes' is non-empty");
  assert(Array.isArray(config.dashboard_cards) && config.dashboard_cards.length > 0, "Config field 'dashboard_cards' is non-empty");
  assert(config.agent_card_schema && Array.isArray(config.agent_card_schema.fields) && config.agent_card_schema.fields.length > 0, "Agent card fields are listed");

  // State Labels check
  assert(Array.isArray(config.state_labels) && config.state_labels.length > 0, "State labels exist in config");
  const expectedStates = ["LIVE", "DEGRADED", "PENDING", "SIMULATED", "STALE", "FAIL-CLOSED", "UNAVAILABLE", "UNKNOWN"];
  for (const state of expectedStates) {
    assert(config.state_labels.includes(state), `State label '${state}' exists in config`);
  }

  // Theme Tokens check
  const theme = config.theme_tokens || {};
  assert(theme.colors && theme.colors.bg_primary === "#030303", "Theme has correct primary background token");
  assert(theme.colors && theme.colors.text_primary === "#F5F7FA", "Theme has correct primary text token");

  // Accessibility rules check
  assert(Array.isArray(config.accessibility_rules) && config.accessibility_rules.length > 0, "Accessibility requirements exist in config");

  // Prompt library check
  assert(Array.isArray(config.prompt_library_source_files) && config.prompt_library_source_files.length > 0, "Prompt library files are referenced in config");

  // Verify that light-theme does not appear as a target in config
  assert(!JSON.stringify(config).toLowerCase().includes("light_theme") && !JSON.stringify(config).toLowerCase().includes("light-theme"), "No light-theme tokens exist in config");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL CONTROL PLANE CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL CONTROL PLANE CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runVisualContractTests();
