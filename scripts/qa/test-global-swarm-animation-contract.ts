import fs from "node:fs";

const html = fs.readFileSync("frontend/index.html", "utf8");
const appJs = fs.readFileSync("frontend/app.js", "utf8");

const blockers: string[] = [];

// 1. Check parent interface section
if (!html.includes('id="hoch-global-swarm-runtime"')) {
  blockers.push("Missing required parent ID: #hoch-global-swarm-runtime");
}

// 2. Check required child IDs
const requiredChildIds = [
  "hoch-process-prompt-bar",
  "hoch-process-prompt-input",
  "hoch-process-launch-button",
  "hoch-swarm-process-rail",
  "hoch-global-motion-canvas",
  "hoch-global-agent-dock",
  "hoch-global-evidence-lights",
  "hoch-global-swarm-status",
  "led-readiness-autopilot",
  "led-hochster-runtime",
  "led-remediation-safety",
  "led-runtime-audit",
  "led-error-budget",
  "led-release-provenance",
  "led-swarm-control",
  "led-mission-intel",
  "led-timeline-replay"
];

for (const id of requiredChildIds) {
  if (!html.includes(`id="${id}"`)) {
    blockers.push(`Missing required child ID: #${id}`);
  }
}

// 3. Check required visible texts
const requiredTexts = [
  "HOCH SWARM PROCESS RUNTIME",
  "Launch Swarm",
  "STANDBY"
];

for (const text of requiredTexts) {
  if (!html.includes(text)) {
    blockers.push(`Missing required visible text: "${text}"`);
  }
}

// 4. Check app.js arrays
if (!appJs.includes("const hochAgentDepartments")) {
  blockers.push("Missing const hochAgentDepartments array in app.js");
}
if (!appJs.includes("const hochDefaultVisibleAgents")) {
  blockers.push("Missing const hochDefaultVisibleAgents array in app.js");
}

// 5. Check app.js functions
const requiredFunctions = [
  "initializeHochSwarmAnimationRuntime",
  "startHochSwarmProcessAnimation",
  "setHochSwarmStage",
  "lightHochSwarmCompletion",
  "animateHochAgentSpinup",
  "animateHochAssetAssignment",
  "updateHochModuleStatusLights",
  "renderHochSwarmProcessRail",
  "renderHochGlobalAgentDock",
  "renderHochEvidenceCompletionLights",
  "animateGordonDockerChecklist",
  "drawGlobalSwarmMotionLines",
  "resetHochSwarmAnimationRuntime"
];

for (const fn of requiredFunctions) {
  if (!appJs.includes(`function ${fn}`)) {
    blockers.push(`Missing function definition: ${fn}() in app.js`);
  }
}

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync("artifacts/qa/global-swarm-animation-contract-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

if (blockers.length) {
  console.error("Global Swarm Process Animation Contract FAILED!");
  process.exit(1);
} else {
  console.log("Global Swarm Process Animation Contract PASSED!");
}
