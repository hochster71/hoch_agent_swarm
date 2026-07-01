import fs from "node:fs";
import path from "node:path";

function main() {
  const htmlPath = "frontend/archive/unused_views.html";
  const jsPath = "frontend/archive/unused_views.js";
  const cssPath = "frontend/styles.css";

  const blockers: string[] = [];

  // 1. Verify files exist
  if (!fs.existsSync(htmlPath)) {
    blockers.push(`Quarantine archive HTML not found: ${htmlPath}`);
  }
  if (!fs.existsSync(jsPath)) {
    blockers.push(`Quarantine archive JS not found: ${jsPath}`);
  }
  if (!fs.existsSync(cssPath)) {
    blockers.push(`CSS file not found: ${cssPath}`);
  }

  if (blockers.length === 0) {
    const html = fs.readFileSync(htmlPath, "utf8");
    const js = fs.readFileSync(jsPath, "utf8");
    const css = fs.readFileSync(cssPath, "utf8");

    // 2. Assert required DOM elements exist in the quarantine archive
    const requiredIds = [
      "topology-agent-overlay-runtime",
      "topology-agent-prompt-input",
      "topology-agent-launch-button",
      "topology-agent-stage-rail",
      "topology-agent-completion-lights",
      "topology-agent-roster",
      "topology-agent-motion-canvas"
    ];

    for (const id of requiredIds) {
      if (!html.includes(`id="${id}"`)) {
        blockers.push(`Missing DOM ID in unused_views.html: #${id}`);
      }
    }

    // 3. Assert topology functions are defined in unused_views.js
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
      if (!js.includes(`function ${fn}`)) {
        blockers.push(`Missing function definition in unused_views.js: ${fn}()`);
      }
    }

    // 4. Assert key topology CSS classes exist in styles.css
    const requiredClasses = [
      ".topology-agent-chip",
      ".topology-stage-step",
      ".topology-agent-led",
      ".topology-asset-glow"
    ];

    for (const cls of requiredClasses) {
      if (!css.includes(cls)) {
        blockers.push(`Missing CSS class in styles.css: ${cls}`);
      }
    }
  }

  const report = {
    generated_at: new Date().toISOString(),
    status: blockers.length === 0 ? "PASS" : "BLOCK",
    blockers
  };

  const outputDir = "artifacts/qa";
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(
    path.join(outputDir, "topology-animation-quality-report.json"),
    JSON.stringify(report, null, 2)
  );

  console.log(JSON.stringify(report, null, 2));

  if (blockers.length > 0) {
    console.error("Topology Animation Quality Contract FAILED!");
    process.exit(1);
  } else {
    console.log("Topology Animation Quality Contract PASSED!");
    process.exit(0);
  }
}

main();
