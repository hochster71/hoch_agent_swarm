import fs from "node:fs";
import path from "node:path";

const html = fs.readFileSync("frontend/index.html", "utf8");
const stylesCss = fs.readFileSync("frontend/styles.css", "utf8");
const appJs = fs.readFileSync("frontend/app.js", "utf8");

const blockers: string[] = [];

// 1. Verify HTML element existence
if (!html.includes('id="koi-pond-layer"')) {
  blockers.push("Missing required DOM element: #koi-pond-layer in index.html");
}

// 2. Verify styles.css rules
const requiredSelectors = [
  "#koi-pond-layer",
  ".koi-fish",
  ".koi-ripple",
  ".koi-orbit"
];

for (const selector of requiredSelectors) {
  if (!stylesCss.includes(selector)) {
    blockers.push(`Missing CSS selector: ${selector} in styles.css`);
  }
}

// 3. Verify prefers-reduced-motion rule in CSS
if (!stylesCss.includes("prefers-reduced-motion: reduce")) {
  blockers.push("Missing prefers-reduced-motion media query in styles.css");
}

// 4. Verify app.js logic
if (!appJs.includes("function initializeKoiAnimation")) {
  blockers.push("Missing function definition: initializeKoiAnimation() in app.js");
}

const reportPath = "artifacts/qa/koi-animation-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (blockers.length) {
  console.error("Koi Animation Layer Contract FAILED!");
  process.exit(1);
} else {
  console.log("Koi Animation Layer Contract PASSED!");
  process.exit(0);
}
