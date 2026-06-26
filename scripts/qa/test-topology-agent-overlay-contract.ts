import fs from "node:fs";
import path from "node:path";

const html = fs.readFileSync("frontend/archive/unused_views.html", "utf8");
const appJs = fs.readFileSync("frontend/archive/unused_views.js", "utf8");

const blockers: string[] = [];

// 1. Assert required new DOM IDs exist in frontend/index.html
const requiredIds = [
  "topology-agent-overlay-runtime",
  "topology-agent-prompt-input",
  "topology-agent-launch-button",
  "topology-agent-stage-rail",
  "topology-agent-completion-lights",
  "topology-agent-roster",
  "topology-agent-profile-modal",
  "topology-agent-modal-close",
  "topology-agent-modal-avatar",
  "topology-agent-modal-name",
  "topology-agent-modal-title",
  "topology-agent-modal-tag",
  "topology-agent-modal-description",
  "topology-agent-modal-catchphrase",
  "topology-agent-modal-skills",
  "topology-agent-modal-spinup",
  "topology-agent-modal-assign",
  "topology-agent-motion-canvas"
];

for (const id of requiredIds) {
  if (!html.includes(`id="${id}"`)) {
    blockers.push(`Missing DOM ID in index.html: #${id}`);
  }
}

// 2. Assert required visible text exists in frontend/index.html
const requiredTexts = [
  "Launch Expert Swarm",
  "Select expert agents",
  "Active Agent Dossier",
  "Green means verified",
  "Amber means needs approval",
  "Red means blocked"
];

for (const text of requiredTexts) {
  if (!html.includes(text)) {
    blockers.push(`Missing required text in index.html: "${text}"`);
  }
}

// 3. Assert frontend/app.js contains hochPixelStickAgents
if (!appJs.includes("const hochPixelStickAgents")) {
  blockers.push("Missing hochPixelStickAgents array in app.js");
}

// 4. Assert frontend/app.js contains all nine default agent names and funny tags
const defaultAgents = [
  { name: "Boss Noodle", tag: "MISSION WRANGLER" },
  { name: "Dr. Signal", tag: "TRUTH HUNTER" },
  { name: "Prof. Blueprint", tag: "SYSTEM CARTOONIST" },
  { name: "Eng. Patch", tag: "PATCH MONK" },
  { name: "Ms. Checkmark", tag: "BUG BOUNCER" },
  { name: "Capt. Guardrail", tag: "GUARDRAIL GOBLIN" },
  { name: "Gordon Vector", tag: "CONTAINER WHISPERER" },
  { name: "Prof. Ledger", tag: "RECEIPT WIZARD" },
  { name: "Eng. Rocket", tag: "SHIP JUDGE" }
];

for (const agent of defaultAgents) {
  if (!appJs.includes(agent.name)) {
    blockers.push(`Missing agent name in app.js: "${agent.name}"`);
  }
  if (!appJs.includes(agent.tag)) {
    blockers.push(`Missing agent tag in app.js: "${agent.tag}"`);
  }
}

// 5. Assert app.js contains all required function declarations
const requiredFunctions = [
  "bindTopologyAgentOverlay",
  "renderTopologyAgentRoster",
  "renderTopologyPixelAvatar",
  "openTopologyAgentProfile",
  "closeTopologyAgentProfile",
  "launchTopologyExpertSwarm",
  "animateTopologyStageRail",
  "lightTopologyCompletion",
  "animateTopologyAgentChip",
  "drawTopologyAgentMotion",
  "glowTopologyAssetCards",
  "animateGordonContainerChecklist"
];

for (const fn of requiredFunctions) {
  if (!appJs.includes(`function ${fn}`)) {
    blockers.push(`Missing function definition in app.js: ${fn}()`);
  }
}

// 6. Security & anti-pattern checks
if (html.includes("cdn.tailwindcss.com")) {
  blockers.push("Anti-pattern detected: index.html contains cdn.tailwindcss.com reference");
}
if (html.includes("/src/main.tsx")) {
  blockers.push("Anti-pattern detected: index.html contains React candidate /src/main.tsx reference");
}
if (html.includes("react-hochster-root")) {
  blockers.push("Anti-pattern detected: index.html contains react-hochster-root placeholder");
}
if (appJs.includes("googleusercontent")) {
  blockers.push("Security block: app.js contains external Google User Content URLs");
}

// 7. Check local tailwind.css compilation output existence
if (!fs.existsSync("frontend/dist/tailwind.css")) {
  blockers.push("Build failure: frontend/dist/tailwind.css does not exist");
}

// Create report object
const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers
};

const outputDir = "artifacts/qa";
fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(
  path.join(outputDir, "topology-agent-overlay-contract-report.json"),
  JSON.stringify(report, null, 2)
);

console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) {
  console.error("Topology Agent Overlay static contract FAILED!");
  process.exit(1);
} else {
  console.log("Topology Agent Overlay static contract PASSED!");
}
