import fs from "node:fs";

const html = fs.readFileSync("frontend/archive/unused_views.html", "utf8");
const appJs = fs.readFileSync("frontend/archive/unused_views.js", "utf8");

const blockers: string[] = [];

// 1. Check parent interface section
if (!html.includes('id="kimi-style-comic-swarm-interface"')) {
  blockers.push("Missing required parent ID: #kimi-style-comic-swarm-interface");
}

// 2. Check required child IDs
const requiredChildIds = [
  "kimi-comic-prompt-input",
  "kimi-comic-spinup-button",
  "kimi-comic-mission-core",
  "kimi-comic-agent-ring",
  "kimi-comic-agent-profile-deck",
  "kimi-comic-youtube-research-lane",
  "kimi-comic-video-candidate-grid",
  "kimi-comic-motion-canvas",
  "kimi-comic-asset-plane",
  "kimi-comic-work-feed",
  "kimi-comic-command-loop",
  "gordon-container-whisperer-panel"
];

for (const id of requiredChildIds) {
  if (!html.includes(`id="${id}"`)) {
    blockers.push(`Missing required child ID: #${id}`);
  }
}

// 3. Check required visible texts
const requiredTexts = [
  "Hoch Agent Swarm",
  "Kimi-Style Comic Swarm",
  "Spin Up Swarm",
  "Mission Core",
  "Agent Profiles",
  "YouTube Research Lane",
  "Video Candidates",
  "Asset Assignment Plane",
  "Gordon Container Whisperer",
  "Plan",
  "Research",
  "Execute",
  "Verify",
  "Report",
  "The container will tell us what hurts.",
  "If it is not evidenced, it did not happen.",
  "Ship only what can defend itself."
];

for (const text of requiredTexts) {
  if (!html.includes(text)) {
    blockers.push(`Missing required visible text: "${text}"`);
  }
}

// 4. Check app.js arrays
if (!appJs.includes("const hochComicAgents")) {
  blockers.push("Missing const hochComicAgents array in app.js");
}
if (!appJs.includes("const hochYoutubeResearchCandidates")) {
  blockers.push("Missing const hochYoutubeResearchCandidates array in app.js");
}

// 5. Check app.js functions
const requiredFunctions = [
  "renderKimiStyleComicSwarmInterface",
  "spinUpKimiStyleComicSwarm",
  "renderHochComicAgentProfiles",
  "renderYoutubeResearchLane",
  "animateYoutubeResearchCards",
  "animateComicAgentProfiles",
  "drawKimiStyleMotionLines",
  "assignResearchToAgents",
  "appendKimiComicWorkFeed",
  "updateKimiComicCommandLoop",
  "renderGordonContainerWhispererPanel"
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
fs.writeFileSync("artifacts/qa/kimi-style-comic-swarm-contract-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

if (blockers.length) {
  console.error("Kimi-Style Comic Swarm Contract FAILED!");
  process.exit(1);
} else {
  console.log("Kimi-Style Comic Swarm Contract PASSED!");
}
