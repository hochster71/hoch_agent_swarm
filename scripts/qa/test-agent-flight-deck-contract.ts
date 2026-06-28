import fs from "node:fs";
import path from "node:path";

const indexHtmlPath = "frontend/index.html";
const appJsPath = "frontend/app.js";
const stylesCssPath = "frontend/styles.css";

const blockers: string[] = [];

// 1. Verify existence of Flight Deck elements in index.html
if (!fs.existsSync(indexHtmlPath)) {
  blockers.push(`Missing index.html: ${indexHtmlPath}`);
} else {
  const content = fs.readFileSync(indexHtmlPath, "utf8");
  if (!content.includes('id="nav-agent-flight-deck"')) {
    blockers.push(`index.html must contain navigation link with id "nav-agent-flight-deck".`);
  }
  if (!content.includes('id="view-agent-flight-deck"')) {
    blockers.push(`index.html must contain view container with id "view-agent-flight-deck".`);
  }
  if (!content.includes('id="campaign-selector"')) {
    blockers.push(`index.html must contain select dropdown with id "campaign-selector".`);
  }
  if (!content.includes('id="lane-campaigns"')) {
    blockers.push(`index.html must contain campaign lane element with id "lane-campaigns".`);
  }
  if (!content.includes('id="lane-tasks"')) {
    blockers.push(`index.html must contain task lane element with id "lane-tasks".`);
  }
  if (!content.includes('id="lane-roster"')) {
    blockers.push(`index.html must contain roster lane element with id "lane-roster".`);
  }
  if (!content.includes('id="lane-gates"')) {
    blockers.push(`index.html must contain gates lane element with id "lane-gates".`);
  }
}

// 2. Verify existence of Flight Deck related CSS classes in styles.css
if (!fs.existsSync(stylesCssPath)) {
  blockers.push(`Missing styles.css: ${stylesCssPath}`);
} else {
  const content = fs.readFileSync(stylesCssPath, "utf8");
  if (!content.includes(".flight-deck-grid")) {
    blockers.push(`styles.css must contain the '.flight-deck-grid' layout selector.`);
  }
  if (!content.includes(".flight-lane")) {
    blockers.push(`styles.css must contain the '.flight-lane' selector.`);
  }
  if (!content.includes(".flight-card")) {
    blockers.push(`styles.css must contain the '.flight-card' selector.`);
  }
}

// 3. Verify JavaScript logic implementation in app.js
if (!fs.existsSync(appJsPath)) {
  blockers.push(`Missing app.js: ${appJsPath}`);
} else {
  const content = fs.readFileSync(appJsPath, "utf8");
  if (!content.includes("loadAgentFlightDeckView")) {
    blockers.push(`app.js must define the 'loadAgentFlightDeckView' loader function.`);
  }
  if (!content.includes("loadActiveCampaignTasks")) {
    blockers.push(`app.js must define 'loadActiveCampaignTasks'.`);
  }
}

const reportPath = "artifacts/qa/agent-flight-deck-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  console.error("Agent Flight Deck Contract FAILED!");
  process.exit(1);
} else {
  console.log("Agent Flight Deck Contract PASSED!");
  process.exit(0);
}
