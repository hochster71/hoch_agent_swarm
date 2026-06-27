import * as fs from 'fs';
import * as path from 'path';

function runMockupTests() {
  console.log("==================================================");
  console.log("VISUAL CONTROL PLANE MOCKUPS CONTRACT VALIDATION");
  console.log("==================================================");

  const baseDir = path.resolve(__dirname, '../../');
  const mockupsDir = path.join(baseDir, 'mockups/visual-control-plane');
  const stylesPath = path.join(mockupsDir, 'styles.css');

  let failed = false;

  const assert = (condition: boolean, message: string) => {
    if (!condition) {
      console.error(`[FAIL] ${message}`);
      failed = true;
    } else {
      console.log(`[PASS] ${message}`);
    }
  };

  // 1. Verify directory and styles.css exist
  assert(fs.existsSync(mockupsDir), "Mockups directory exists: mockups/visual-control-plane");
  assert(fs.existsSync(stylesPath), "Styles file exists: mockups/visual-control-plane/styles.css");

  // 2. Verify all required HTML files exist
  const expectedHtmlFiles = [
    'index.html',
    'control-plane.html',
    'assets.html',
    'models.html',
    'prompts.html',
    'agents.html',
    'cyber.html',
    'evidence.html',
    'approvals.html',
    'factory.html',
    'factory-apps.html',
    'factory-build-lanes.html',
    'factory-release.html',
    'life.html',
    'life-home.html',
    'life-family.html',
    'life-hobbies.html',
    'life-humanity.html'
  ];

  for (const file of expectedHtmlFiles) {
    const filePath = path.join(mockupsDir, file);
    assert(fs.existsSync(filePath), `HTML file exists: mockups/visual-control-plane/${file}`);
  }

  // 3. Scan all HTML files for stylesheet inclusion and other constraints
  let allContent = '';
  for (const file of expectedHtmlFiles) {
    const filePath = path.join(mockupsDir, file);
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf-8');
      allContent += ' ' + content;

      assert(content.includes('href="styles.css"') || content.includes("href='styles.css'"), `${file} includes styles.css link`);
      assert(!content.toLowerCase().includes('light-theme') && !content.toLowerCase().includes('light_theme'), `${file} has no light theme requirements`);

      // Verify no "100% complete" text exists unless accompanied by SAMPLE or SIMULATED
      if (content.includes("100% complete") || content.includes("100% Complete")) {
        const matchesSampleOrSimulated = content.includes("SAMPLE") || content.includes("SIMULATED");
        assert(matchesSampleOrSimulated, `${file} contains '100% complete' only with a SAMPLE/SIMULATED label`);
      }
    }
  }

  // 4. Verify all required state labels are present in the mockups corpus
  const requiredStates = [
    'LIVE',
    'DEGRADED',
    'PENDING',
    'SIMULATED',
    'STALE',
    'FAIL-CLOSED',
    'UNAVAILABLE',
    'UNKNOWN'
  ];

  for (const state of requiredStates) {
    assert(allContent.includes(state), `State label '${state}' appears across mockups`);
  }

  // 5. Verify agent card requirements in agents.html
  const agentsPath = path.join(mockupsDir, 'agents.html');
  if (fs.existsSync(agentsPath)) {
    const content = fs.readFileSync(agentsPath, 'utf-8');
    assert(content.includes('Prompt ID'), "Agent card includes Prompt ID field");
    assert(content.includes('Risk Level'), "Agent card includes Risk Level field");
    assert(content.includes('Approval Required'), "Agent card includes Approval Required field");
    assert(content.includes('Evidence Status'), "Agent card includes Evidence Status field");
    assert(content.includes('Loop Phase'), "Agent card includes Loop Phase field");
  }

  // 6. Verify approvals page requirements in approvals.html
  const approvalsPath = path.join(mockupsDir, 'approvals.html');
  if (fs.existsSync(approvalsPath)) {
    const content = fs.readFileSync(approvalsPath, 'utf-8');
    assert(content.includes('Michael Hoch Approval Gate'), "Approvals page includes Michael Hoch approval gate");
  }

  // 7. Verify cyber page requirements in cyber.html
  const cyberPath = path.join(mockupsDir, 'cyber.html');
  if (fs.existsSync(cyberPath)) {
    const content = fs.readFileSync(cyberPath, 'utf-8');
    assert(content.includes('prompt injection') || content.includes('Prompt Injection'), "Cyber page includes prompt injection text");
    assert(content.includes('fail-closed') || content.includes('Fail-closed'), "Cyber page includes fail-closed text");
  }

  // 8. Verify factory page requirements in factory.html
  const factoryPath = path.join(mockupsDir, 'factory.html');
  if (fs.existsSync(factoryPath)) {
    const content = fs.readFileSync(factoryPath, 'utf-8');
    const pipelineWords = ["Idea", "Goal", "Requirements", "Research", "Architecture", "UX", "Build", "Security", "QA", "Evidence", "Human Approval", "Release", "ConMon"];
    let containsPipeline = true;
    for (const word of pipelineWords) {
      if (!content.includes(word)) {
        containsPipeline = false;
        break;
      }
    }
    assert(containsPipeline, "Factory page includes full Idea-to-ConMon pipeline");
  }

  // 9. Verify styles.css contains reduced motion media query
  if (fs.existsSync(stylesPath)) {
    const content = fs.readFileSync(stylesPath, 'utf-8');
    assert(content.includes('prefers-reduced-motion'), "styles.css contains prefers-reduced-motion query");
  }

  console.log("==================================================");
  if (failed) {
    console.error("VISUAL CONTROL PLANE MOCKUPS VALIDATION FAILED");
    process.exit(1);
  } else {
    console.log("VISUAL CONTROL PLANE MOCKUPS VALIDATION PASSED SUCCESSFULLY");
    process.exit(0);
  }
}

runMockupTests();
