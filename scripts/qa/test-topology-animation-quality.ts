import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  page.on("console", msg => console.log(`BROWSER CONSOLE: ${msg.text()}`));
  page.on("pageerror", err => console.error(`BROWSER ERROR: ${err.message}`));
  
  const blockers: string[] = [];
  
  try {
    console.log("Navigating to dashboard...");
    await page.goto("http://localhost:8000/", { waitUntil: "networkidle" });
    
    // Debug: print current node cards before launch
    const preIds = await page.evaluate(() => {
      const cards = document.querySelectorAll("[id^='node-card-']");
      return Array.from(cards).map(c => c.id);
    });
    console.log("Pre-launch node card IDs present in DOM:", preIds);
    
    const tbodyHtml = await page.locator("#deployments-tbody").innerHTML();
    console.log("Pre-launch deployments-tbody innerHTML size:", tbodyHtml.length);
    
    // Fill prompt and click launch
    console.log("Launching Expert Swarm...");
    await page.fill("#topology-agent-prompt-input", "Research YouTube Docker debugging videos and verify release readiness.");
    await page.click("#topology-agent-launch-button");
    
    // Wait for the Complete stage to become complete (green)
    console.log("Waiting for swarm execution to complete...");
    const completeStage = page.locator('.topology-stage-step[data-stage="Complete"].is-complete');
    await completeStage.waitFor({ state: "visible", timeout: 15000 });
    
    // Debug: print node cards after launch
    const postIds = await page.evaluate(() => {
      const cards = document.querySelectorAll("[id^='node-card-']");
      return Array.from(cards).map(c => c.id);
    });
    console.log("Post-launch node card IDs present in DOM:", postIds);
    
    // Check if any card has the topology-asset-glow class
    const glowingClasses = await page.evaluate(() => {
      const cards = document.querySelectorAll(".topology-asset-glow");
      return Array.from(cards).map(c => c.id);
    });
    console.log("Post-launch glowing card IDs:", glowingClasses);
    
    // 1. Assert topology-agent-chip.is-complete exists
    const completedChips = await page.locator(".topology-agent-chip.is-complete").count();
    console.log(`Found ${completedChips} completed agent chips.`);
    if (completedChips === 0) {
      blockers.push("No topology-agent-chip.is-complete classes found after execution");
    }
    
    // 2. Assert topology-stage-step.is-complete exists
    const completedStages = await page.locator(".topology-stage-step.is-complete").count();
    console.log(`Found ${completedStages} completed stages.`);
    if (completedStages === 0) {
      blockers.push("No topology-stage-step.is-complete classes found after execution");
    }
    
    // 3. Assert topology-asset-glow exists
    const glowingAssets = await page.locator(".topology-asset-glow").count();
    console.log(`Found ${glowingAssets} glowing assets.`);
    if (glowingAssets === 0) {
      blockers.push("No topology-asset-glow classes found during/after execution");
    }
    
    // 4. Assert topology-agent-led.is-green exists
    const greenLeds = await page.locator(".topology-agent-led.is-green").count();
    console.log(`Found ${greenLeds} green completion LEDs.`);
    if (greenLeds === 0) {
      blockers.push("No topology-agent-led.is-green classes found after execution");
    }
  } catch (error: any) {
    blockers.push(`Execution error: ${error.message}`);
  } finally {
    await browser.close();
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
