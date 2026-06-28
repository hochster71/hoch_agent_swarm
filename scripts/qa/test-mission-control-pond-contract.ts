import fs from "node:fs";
import path from "node:path";

const indexHtmlPath = "frontend/index.html";
const appJsPath = "frontend/app.js";
const stylesCssPath = "frontend/styles.css";

const blockers: string[] = [];

// 1. Verify existence of the koi pond container in index.html
if (!fs.existsSync(indexHtmlPath)) {
  blockers.push(`Missing index.html: ${indexHtmlPath}`);
} else {
  const content = fs.readFileSync(indexHtmlPath, "utf8");
  if (!content.includes('id="koi-pond-layer"')) {
    blockers.push(`index.html must contain an element with id "koi-pond-layer".`);
  }
}

// 2. Verify existence of Koi-related CSS styles and state-coloring rules in styles.css
if (!fs.existsSync(stylesCssPath)) {
  blockers.push(`Missing styles.css: ${stylesCssPath}`);
} else {
  const content = fs.readFileSync(stylesCssPath, "utf8");
  if (!content.includes(".koi-fish")) {
    blockers.push(`styles.css must contain the '.koi-fish' class definition.`);
  }
  if (!content.includes(".state-live")) {
    blockers.push(`styles.css must contain '.state-live' state color styling.`);
  }
  if (!content.includes(".state-broken")) {
    blockers.push(`styles.css must contain '.state-broken' state color styling.`);
  }
  if (!content.includes(".swim-paused")) {
    blockers.push(`styles.css must contain '.swim-paused' class for pause state.`);
  }
}

// 3. Verify JavaScript implements initializeKoiAnimation and the updateKoiPond logic
if (!fs.existsSync(appJsPath)) {
  blockers.push(`Missing app.js: ${appJsPath}`);
} else {
  const content = fs.readFileSync(appJsPath, "utf8");
  if (!content.includes("initializeKoiAnimation")) {
    blockers.push(`app.js must define and call 'initializeKoiAnimation'.`);
  }
  if (!content.includes("updateKoiPond")) {
    blockers.push(`app.js must define and call 'updateKoiPond'.`);
  }
  if (!content.includes("triggerKoiRipple")) {
    blockers.push(`app.js must define 'triggerKoiRipple'.`);
  }
  if (!content.includes("getDeterministicOrbit")) {
    blockers.push(`app.js must implement 'getDeterministicOrbit' for dynamic entity mapping.`);
  }
  if (!content.includes("activeEntities")) {
    blockers.push(`app.js must derive fish from dynamic activeEntities list.`);
  }
}

const reportPath = "artifacts/qa/mission-control-pond-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  console.error("Mission Control Pond Contract FAILED!");
  process.exit(1);
} else {
  console.log("Mission Control Pond Contract PASSED!");
  process.exit(0);
}
