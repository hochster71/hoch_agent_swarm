import fs from "node:fs";
const main = fs.readFileSync("backend/main.py", "utf8");
const improvement = fs.readFileSync("backend/model_improvement.py", "utf8");
const pkg = fs.readFileSync("package.json", "utf8");
const checks: Record<string, boolean> = {
  improvement_module_exists: fs.existsSync("backend/model_improvement.py"),
  route_improve: main.includes("/api/v1/models/improve"),
  writes_improvement_report: improvement.includes("model_improvement_report.json"),
  uses_api_create: improvement.includes("/api/create"),
  system_prompt_specialization: improvement.includes("SPECIALIZED_SYSTEM_PROMPT"),
  compares_scores: improvement.includes("improved_score > original_score"),
  deletes_demoted: improvement.includes("/api/delete"),
  package_script: pkg.includes("qa:model-improvement"),
};
const blockers = Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k);
console.log(JSON.stringify({
  generated_at: new Date().toISOString(),
  status: blockers.length ? "FAIL" : "PASS",
  checks,
  blockers,
}, null, 2));
if (blockers.length) process.exit(1);
