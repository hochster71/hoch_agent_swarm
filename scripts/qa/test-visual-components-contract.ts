import * as fs from 'fs';
import * as path from 'path';

function runVisualComponentsTests() {
  console.log("==================================================");
  console.log("VISUAL COMPONENTS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const componentsHtmlFile = path.join(baseDir, 'mockups/visual-control-plane/components.html');
  const docFile = path.join(baseDir, 'docs/visual-control-plane/11_component_library.md');
  const stylesFile = path.join(baseDir, 'mockups/visual-control-plane/styles.css');

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
  assert(fs.existsSync(componentsHtmlFile), "components.html file exists");
  assert(fs.existsSync(docFile), "11_component_library.md doc file exists");
  assert(fs.existsSync(stylesFile), "styles.css file exists");

  const componentsHtmlContent = fs.existsSync(componentsHtmlFile) ? fs.readFileSync(componentsHtmlFile, 'utf-8') : '';
  const docContent = fs.existsSync(docFile) ? fs.readFileSync(docFile, 'utf-8') : '';
  const stylesContent = fs.existsSync(stylesFile) ? fs.readFileSync(stylesFile, 'utf-8') : '';

  // 2. All 14 component names appear in both components.html and 11_component_library.md
  const componentsList = [
    "ops-header",
    "status-pill",
    "telemetry-card",
    "agent-card",
    "approval-card",
    "evidence-card",
    "pipeline-stage",
    "node-map-card",
    "prompt-card",
    "risk-badge",
    "state-registry",
    "terminal-panel",
    "metric-strip",
    "section-rail"
  ];

  componentsList.forEach(comp => {
    assert(componentsHtmlContent.includes(comp), `components.html contains component '${comp}'`);
    assert(docContent.includes(comp), `11_component_library.md contains component '${comp}'`);
  });

  // 3. All 8 state labels appear in components.html
  const stateLabelsList = [
    "LIVE",
    "DEGRADED",
    "PENDING",
    "SIMULATED",
    "STALE",
    "FAIL-CLOSED",
    "UNAVAILABLE",
    "UNKNOWN"
  ];

  stateLabelsList.forEach(state => {
    assert(componentsHtmlContent.includes(state), `components.html contains state label '${state}'`);
  });

  // 4. styles.css contains reusable classes
  assert(stylesContent.includes('.card'), "styles.css contains class '.card'");
  assert(stylesContent.includes('.status-badge'), "styles.css contains class '.status-badge'");
  assert(stylesContent.includes('.agent-card'), "styles.css contains class '.agent-card'");
  assert(stylesContent.includes('.approval-card'), "styles.css contains class '.approval-card'");
  assert(stylesContent.includes('.evidence-card'), "styles.css contains class '.evidence-card'");
  assert(stylesContent.includes('.pipeline-stage'), "styles.css contains class '.pipeline-stage'");
  assert(stylesContent.includes('.node-map-card'), "styles.css contains class '.node-map-card'");
  assert(stylesContent.includes('.prompt-card'), "styles.css contains class '.prompt-card'");
  assert(stylesContent.includes('.risk-badge'), "styles.css contains class '.risk-badge'");
  assert(stylesContent.includes('.terminal-panel'), "styles.css contains class '.terminal-panel'");
  assert(stylesContent.includes('.metric-strip'), "styles.css contains class '.metric-strip'");
  assert(stylesContent.includes('.section-rail'), "styles.css contains class '.section-rail'");

  // 5. General quality checks
  assert(!stylesContent.includes('background-color: white') && !stylesContent.includes('background: white'), "Safety check: No light theme backgrounds set in styles.css");
  assert(stylesContent.includes('prefers-reduced-motion'), "styles.css contains prefers-reduced-motion override");
  assert(stylesContent.includes(':focus'), "styles.css contains keyboard focus outline styling");
  assert(docContent.toLowerCase().includes('evidence binding'), "11_component_library.md includes evidence binding language");
  assert(!componentsHtmlContent.includes('LIVE (Verified)') || componentsHtmlContent.includes('SIMULATED') || componentsHtmlContent.includes('SAMPLE'), "Component page preserves mock/simulation labeling");

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL COMPONENTS CONTRACT FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL COMPONENTS CONTRACT PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runVisualComponentsTests();
