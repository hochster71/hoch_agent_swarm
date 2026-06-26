import fs from "node:fs";
import path from "node:path";

const doctrinePath = "docs/mission/live_runtime_instrument_doctrine.md";
const featureMapPath = "config/live_runtime_feature_map.json";
const indexHtmlPath = "frontend/index.html";
const appJsPath = "frontend/app.js";

const FORBIDDEN_TOKENS = [
  "HEALTHY 100%",
  "10 ASSETS ACTIVE",
  "SYNC: OK",
  "1.2ms",
  "Boss Noodle",
  "Dr. Signal",
  "Prof. Blueprint",
  "Eng. Patch",
  "Ms. Checkmark",
  "Capt. Guardrail",
  "Gordon Vector",
  "Prof. Ledger",
  "Eng. Rocket",
  "Kimi-Style Comic Swarm Demo",
  "Open Swarm Comic",
  "Launch Expert Swarm",
  "YouTube Research Lane",
  "Video Candidates",
  "Asset Assignment Plane",
  "SWARM ACTIVE WORKSTREAM FEED",
  "Agent Profiles",
  "Catchphrases of Swarm",
  "Docker Diagnostic Checklist",
  "CLUSTER INTEL BRIEF",
  "TERMINAL LOGS",
  "43 agents operational",
  "Mean cluster CPU load",
  "ZTA posture: ENFORCED",
  "CDAO RAI traceability: ACTIVE",
  "ConMon: STREAMING",
  "Tac-C2 Kernel Hub",
  "RMF ConMon policy rules validated"
];

const blockers: string[] = [];

// 1. Verify doctrine
if (!fs.existsSync(doctrinePath)) {
  blockers.push(`Missing live runtime instrument doctrine: ${doctrinePath}`);
}

// 2. Verify feature map
if (!fs.existsSync(featureMapPath)) {
  blockers.push(`Missing live feature map configuration: ${featureMapPath}`);
}

// 3. Scan active HTML
if (!fs.existsSync(indexHtmlPath)) {
  blockers.push(`Missing active index.html: ${indexHtmlPath}`);
} else {
  const indexHtml = fs.readFileSync(indexHtmlPath, "utf8").toLowerCase();
  for (const token of FORBIDDEN_TOKENS) {
    if (indexHtml.includes(token.toLowerCase())) {
      blockers.push(`Active index.html contains forbidden static token: "${token}"`);
    }
  }
}

// 4. Scan active JS
if (!fs.existsSync(appJsPath)) {
  blockers.push(`Missing active app.js: ${appJsPath}`);
} else {
  const appJs = fs.readFileSync(appJsPath, "utf8").toLowerCase();
  for (const token of FORBIDDEN_TOKENS) {
    if (appJs.includes(token.toLowerCase())) {
      blockers.push(`Active app.js contains forbidden static token: "${token}"`);
    }
  }
}

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync("artifacts/qa/live-runtime-instrument-contract-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  console.error("Live Runtime Instrument Contract FAILED!");
  process.exit(1);
} else {
  console.log("Live Runtime Instrument Contract PASSED!");
  process.exit(0);
}
