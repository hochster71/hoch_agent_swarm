import fs from "node:fs";
import { navOperationalContracts } from "./nav-contract";

const html = fs.readFileSync("frontend/archive/unused_views.html", "utf8");
const app = fs.readFileSync("frontend/archive/unused_views.js", "utf8");

const requiredLabels = navOperationalContracts.map((item) => item.label);
const forbiddenLabels = [
  "PERT Analysis",
  "Security Audit",
];

const blockers: string[] = [];

for (const label of requiredLabels) {
  if (!html.includes(label)) {
    blockers.push(`Missing nav label in frontend/index.html: ${label}`);
  }
}

const navLinksMatch = html.match(/<nav class="nav-links">([\s\S]*?)<\/nav>/);
const navLinksContent = navLinksMatch ? navLinksMatch[1] : "";

for (const label of forbiddenLabels) {
  if (navLinksContent.includes(label)) {
    blockers.push(`Forbidden stale nav label still present in nav links: ${label}`);
  }
}

for (const item of navOperationalContracts) {
  if (!app.includes(item.id)) {
    blockers.push(`Nav item id not referenced in frontend/app.js: ${item.id}`);
  }
  if (!app.includes(item.endpoint)) {
    blockers.push(`Nav endpoint not referenced in frontend/app.js: ${item.endpoint}`);
  }
}

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  required_labels: requiredLabels,
  forbidden_labels: forbiddenLabels,
  blockers,
};

fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync(
  "artifacts/qa/nav-contract-report.json",
  JSON.stringify(report, null, 2)
);

console.log(JSON.stringify(report, null, 2));

if (blockers.length > 0) process.exit(1);
