import fs from "node:fs";
import path from "node:path";

const indexHtmlPath = "frontend/index.html";
const appJsPath = "frontend/app.js";
const mainPyPath = "backend/main.py";
const daemonPyPath = "backend/discovery_daemon.py";

const blockers: string[] = [];

// 1. Verify existence and class definition of the discovery daemon
if (!fs.existsSync(daemonPyPath)) {
  blockers.push(`Missing backend discovery daemon file: ${daemonPyPath}`);
} else {
  const content = fs.readFileSync(daemonPyPath, "utf8");
  if (!content.includes("class DiscoveryDaemon")) {
    blockers.push(`${daemonPyPath} must define 'class DiscoveryDaemon'.`);
  }
  if (!content.includes("event_bus.emit")) {
    blockers.push(`${daemonPyPath} must emit events via DetectionEventBus.`);
  }
}

// 2. Verify main.py endpoint and daemon registration
if (!fs.existsSync(mainPyPath)) {
  blockers.push(`Missing main.py backend routing: ${mainPyPath}`);
} else {
  const content = fs.readFileSync(mainPyPath, "utf8");
  if (!content.includes("/api/v1/discovery/ai-runtimes/rescan")) {
    blockers.push(`main.py must register the '/api/v1/discovery/ai-runtimes/rescan' route.`);
  }
  if (!content.includes("discovery_daemon.start()")) {
    blockers.push(`main.py must start the discovery_daemon on startup.`);
  }
}

// 3. Verify HTML contains rescan button and scan status span
if (!fs.existsSync(indexHtmlPath)) {
  blockers.push(`Missing active index.html: ${indexHtmlPath}`);
} else {
  const content = fs.readFileSync(indexHtmlPath, "utf8");
  if (!content.includes('id="btn-rescan-runtimes"')) {
    blockers.push(`index.html must contain an element with id "btn-rescan-runtimes".`);
  }
  if (!content.includes('id="scan-status"')) {
    blockers.push(`index.html must contain an element with id "scan-status".`);
  }
}

// 4. Verify app.js contains rescan button event listener initializer
if (!fs.existsSync(appJsPath)) {
  blockers.push(`Missing active app.js: ${appJsPath}`);
} else {
  const content = fs.readFileSync(appJsPath, "utf8");
  if (!content.includes("initRescanButton")) {
    blockers.push(`app.js must define and call 'initRescanButton'.`);
  }
  if (!content.includes("/api/v1/discovery/ai-runtimes/rescan")) {
    blockers.push(`app.js must fetch from '/api/v1/discovery/ai-runtimes/rescan'.`);
  }
}

const reportPath = "artifacts/qa/ai-runtime-discovery-scheduler-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  console.error("AI Runtime Discovery Scheduler Contract FAILED!");
  process.exit(1);
} else {
  console.log("AI Runtime Discovery Scheduler Contract PASSED!");
  process.exit(0);
}
