import fs from "node:fs";
import path from "node:path";

const html = fs.readFileSync("frontend/index.html", "utf8");
const appJs = fs.readFileSync("frontend/app.js", "utf8");

const blockers: string[] = [];

// 1. Verify HTML element existence for Live Runtime Pond Panel
const requiredHtmlIds = [
  'id="live-runtime-pond-panel"',
  'id="koi-runtime-canvas"',
  'id="runtime-process-feed"',
  'id="koi-runtime-legend"'
];

for (const id of requiredHtmlIds) {
  if (!html.includes(id)) {
    blockers.push(`Missing required HTML ID: ${id} in index.html`);
  }
}

// 2. Verify app.js telemetry logic and API interactions
const requiredJsSnippets = [
  "loadRuntimeAnimationState",
  "renderRuntimeProcessFeed",
  "/api/v1/runtime/process/animation-state"
];

for (const snippet of requiredJsSnippets) {
  if (!appJs.includes(snippet)) {
    blockers.push(`Missing JS logic/reference: ${snippet} in app.js`);
  }
}

const reportPath = "artifacts/qa/live-runtime-koi-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length) {
  console.error("Live Runtime Process Pond Contract FAILED!");
  process.exit(1);
} else {
  console.log("Live Runtime Process Pond Contract PASSED!");
  process.exit(0);
}
