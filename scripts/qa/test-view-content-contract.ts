import fs from "node:fs";

const html = fs.readFileSync("frontend/index.html", "utf8");

const requiredByView: Record<string, string[]> = {
  "view-remediation-safety": [
    "Remediation Safety Command Center",
    "Autonomy Level",
    "Readiness Score",
    "Error Budget",
    "Burn Rate",
    "Active Incidents",
    "Safety Gates",
    "Risk Classifier",
    "SQL Allowlist",
    "Side-Effect Guard",
    "Dry-Run Simulation",
    "Approval Policy",
    "Rollback Plan",
    "Post-Fix Verification",
    "Autonomy Throttle",
    "Incident Remediation Queue",
    "Red-Team Safety Validation"
  ],
};

const forbiddenInRemediationSafety = [
  "CLUSTER TASK HISTORY",
  "Code Generation",
  "Refactoring Swarm",
  "Unit Testing",
  "task-L3",
  "task-W1"
];

const blockers: string[] = [];

for (const [viewId, requiredTexts] of Object.entries(requiredByView)) {
  const viewStart = html.indexOf(`id="${viewId}"`);
  if (viewStart === -1) {
    blockers.push(`Missing view: ${viewId}`);
    continue;
  }

  const nextView = html.indexOf('id="view-', viewStart + 1);
  const viewHtml = html.slice(viewStart, nextView === -1 ? undefined : nextView);

  for (const text of requiredTexts) {
    if (!viewHtml.includes(text)) {
      blockers.push(`${viewId} missing required text: ${text}`);
    }
  }

  for (const text of forbiddenInRemediationSafety) {
    if (viewHtml.includes(text)) {
      blockers.push(`${viewId} contains forbidden stale content: ${text}`);
    }
  }
}

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync("artifacts/qa/view-content-contract-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

if (blockers.length) process.exit(1);
