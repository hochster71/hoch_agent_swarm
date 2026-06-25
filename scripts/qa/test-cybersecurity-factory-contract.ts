import * as fs from "fs";
import * as path from "path";

const indexHtmlPath = path.resolve(__dirname, "../../frontend/index.html");
const appJsPath = path.resolve(__dirname, "../../frontend/app.js");
const tailwindCssPath = path.resolve(__dirname, "../../frontend/dist/tailwind.css");
const reportPath = path.resolve(__dirname, "../../artifacts/qa/cybersecurity-factory-contract-report.json");

interface ValidationResult {
  passed: boolean;
  blockers: string[];
}

function runContractValidation(): ValidationResult {
  const blockers: string[] = [];

  // Read index.html
  if (!fs.existsSync(indexHtmlPath)) {
    blockers.push("Missing frontend/index.html");
    return { passed: false, blockers };
  }
  const indexHtml = fs.readFileSync(indexHtmlPath, "utf8");

  // Read app.js
  if (!fs.existsSync(appJsPath)) {
    blockers.push("Missing frontend/app.js");
    return { passed: false, blockers };
  }
  const appJs = fs.readFileSync(appJsPath, "utf8");

  // Assert index.html contains Cybersecurity Factory
  if (!indexHtml.includes("Cybersecurity Factory")) {
    blockers.push("index.html does not contain navigation label 'Cybersecurity Factory'");
  }

  // Assert index.html contains view-cybersecurity-factory
  if (!indexHtml.includes("view-cybersecurity-factory")) {
    blockers.push("index.html does not contain container 'view-cybersecurity-factory'");
  }

  // Assert index.html contains all required DOM IDs
  const requiredIds = [
    "cybersecurity-factory-view",
    "factory-mission-core",
    "humanity-usefulness-gate",
    "factory-swarm-pipeline",
    "factory-research-panel",
    "factory-north-star-planner",
    "factory-pert-analysis",
    "factory-cybersecurity-pipeline",
    "factory-e2e-evidence-board",
    "factory-store-delivery-matrix",
    "factory-application-portfolio",
    "factory-post-launch-monitor",
    "factory-agent-roster"
  ];
  for (const id of requiredIds) {
    if (!indexHtml.includes(`id="${id}"`) && !indexHtml.includes(`id='${id}'`)) {
      blockers.push(`index.html is missing required DOM ID: ${id}`);
    }
  }

  // Assert index.html contains all required visible text
  const requiredTexts = [
    "Cybersecurity Factory",
    "Hoch Application Software Factory",
    "Humanity Usefulness Gate",
    "Research",
    "North Star Planning",
    "PERT&#8203;&#65;nalysis",
    "Product Design",
    "Secure Development",
    "Cybersecurity Review",
    "QA / E2E",
    "Privacy / Store Compliance",
    "App Store Delivery",
    "Post-Launch Monitoring",
    "For Humanity",
    "useful knowledge",
    "useful process",
    "PASS",
    "BLOCK",
    "Apple App Store",
    "Google Play",
    "Microsoft Store",
    "Chrome Web Store",
    "GitHub Release",
    "Docker Registry",
    "Web / PWA"
  ];
  for (const text of requiredTexts) {
    if (!indexHtml.includes(text)) {
      blockers.push(`index.html is missing required visible text: ${text}`);
    }
  }

  // Assert index.html does not contain cdn.tailwindcss.com
  if (indexHtml.includes("cdn.tailwindcss.com")) {
    blockers.push("Forbidden dependency: index.html contains cdn.tailwindcss.com reference");
  }

  // Assert index.html does not contain /src/main.tsx
  if (indexHtml.includes("/src/main.tsx")) {
    blockers.push("Forbidden reference: index.html references /src/main.tsx");
  }

  // Assert index.html does not contain react-hochster-root
  if (indexHtml.includes("react-hochster-root")) {
    blockers.push("Forbidden reference: index.html contains react-hochster-root");
  }

  // Assert app.js contains arrays
  const requiredArrays = [
    "hochApplicationFactoryStages",
    "humanityUsefulnessCriteria",
    "applicationStoreTargets",
    "hochApplicationFactoryAgents"
  ];
  for (const arr of requiredArrays) {
    if (!appJs.includes(arr)) {
      blockers.push(`app.js does not define variable/array: ${arr}`);
    }
  }

  // Assert app.js contains required functions
  const requiredFunctions = [
    "renderCybersecurityFactoryView",
    "renderHumanityUsefulnessGate",
    "renderApplicationFactoryPipeline",
    "renderFactoryAgentRoster",
    "runFactoryHumanityGate",
    "launchApplicationFactorySwarm",
    "animateFactoryPipelineStage",
    "lightFactoryGateResult",
    "renderFactoryPertAnalysis",
    "renderFactoryStoreDeliveryMatrix",
    "renderFactoryCybersecurityPipeline",
    "renderFactoryE2EEvidenceBoard"
  ];
  for (const func of requiredFunctions) {
    if (!appJs.includes(func)) {
      blockers.push(`app.js is missing function definition: ${func}`);
    }
  }

  // Assert app.js contains all factory agent names
  const requiredAgents = [
    "Factory Foreman Fizz",
    "Humanity Hank",
    "North Star Nora",
    "PERT Percy",
    "Research Raccoon",
    "Design Doodle Dee",
    "Architect Atlas",
    "Cyber Cobra",
    "Secrets Squirrel",
    "Dependency Dingo",
    "E2E Ellie",
    "Storefront Stan",
    "Review Rita"
  ];
  for (const agent of requiredAgents) {
    if (!appJs.includes(agent)) {
      blockers.push(`app.js does not contain factory agent: ${agent}`);
    }
  }

  // Assert dist/tailwind.css exists
  if (!fs.existsSync(tailwindCssPath)) {
    blockers.push(`Missing production Tailwind stylesheet at ${tailwindCssPath}`);
  }

  return {
    passed: blockers.length === 0,
    blockers
  };
}

const result = runContractValidation();

// Ensure artifacts/qa directory exists
const artifactsQaDir = path.dirname(reportPath);
if (!fs.existsSync(artifactsQaDir)) {
  fs.mkdirSync(artifactsQaDir, { recursive: true });
}

fs.writeFileSync(
  reportPath,
  JSON.stringify(
    {
      timestamp: new Date().toISOString(),
      passed: result.passed,
      blockers: result.blockers
    },
    null,
    2
  ),
  "utf8"
);

console.log(`=== Cybersecurity Factory Contract Validation ===`);
console.log(`Status: ${result.passed ? "PASS" : "FAIL"}`);
if (!result.passed) {
  console.error("Blockers encountered:");
  for (const b of result.blockers) {
    console.error(` - ${b}`);
  }
  process.exit(1);
} else {
  console.log("All static contract validations passed successfully!");
  process.exit(0);
}
