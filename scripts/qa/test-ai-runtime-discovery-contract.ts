import fs from "node:fs";
import path from "node:path";

const indexHtmlPath = "frontend/index.html";
const appJsPath = "frontend/app.js";
const mainPyPath = "backend/main.py";
const aggregatorPyPath = "backend/live_runtime_aggregator.py";
const discoveryPyPath = "backend/live_runtime_discovery.py";

const blockers: string[] = [];

// 1. Verify existence of new files
if (!fs.existsSync(discoveryPyPath)) {
  blockers.push(`Missing backend discovery logic file: ${discoveryPyPath}`);
} else {
  const content = fs.readFileSync(discoveryPyPath, "utf8");
  if (!content.includes("stale_static_assets_rejected")) {
    blockers.push(`${discoveryPyPath} must contain a 'stale_static_assets_rejected' field.`);
  }
}

// 2. Verify main.py endpoint registration
if (!fs.existsSync(mainPyPath)) {
  blockers.push(`Missing main.py backend routing: ${mainPyPath}`);
} else {
  const content = fs.readFileSync(mainPyPath, "utf8");
  if (!content.includes("/api/v1/discovery/ai-runtimes")) {
    blockers.push(`main.py must register the '/api/v1/discovery/ai-runtimes' route.`);
  }
}

// 3. Verify aggregator updates
if (!fs.existsSync(aggregatorPyPath)) {
  blockers.push(`Missing live_runtime_aggregator.py: ${aggregatorPyPath}`);
} else {
  const content = fs.readFileSync(aggregatorPyPath, "utf8");
  if (!content.includes("/api/v1/discovery/ai-runtimes")) {
    blockers.push(`live_runtime_aggregator.py must use discovery endpoint instead of supervisor status.`);
  }
  if (!content.includes("stale_static_assets_rejected")) {
    blockers.push(`live_runtime_aggregator.py must reject stale static assets.`);
  }
}

// 4. Verify frontend app.js fetches and renders discovery
if (!fs.existsSync(appJsPath)) {
  blockers.push(`Missing frontend app.js: ${appJsPath}`);
} else {
  const content = fs.readFileSync(appJsPath, "utf8");
  if (!content.includes("/api/v1/discovery/ai-runtimes")) {
    blockers.push(`app.js must fetch from '/api/v1/discovery/ai-runtimes'.`);
  }
  if (content.includes("/api/v1/runtime/local-supervisor/status")) {
    blockers.push(`app.js must not fetch from '/api/v1/runtime/local-supervisor/status' for local models.`);
  }
}

// 5. Verify index.html contains local-models-grid container
if (!fs.existsSync(indexHtmlPath)) {
  blockers.push(`Missing active index.html: ${indexHtmlPath}`);
} else {
  const content = fs.readFileSync(indexHtmlPath, "utf8");
  if (!content.includes('id="local-models-grid"')) {
    blockers.push(`index.html must contain container element with id "local-models-grid".`);
  }
}

const reportPath = "artifacts/qa/ai-runtime-discovery-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  console.error("AI Runtime Discovery Contract FAILED!");
  process.exit(1);
} else {
  console.log("AI Runtime Discovery Contract PASSED!");
  process.exit(0);
}
