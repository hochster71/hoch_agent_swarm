import fs from "node:fs";
const main = fs.readFileSync("backend/main.py", "utf8");
const lifecycle = fs.readFileSync("backend/model_lifecycle.py", "utf8");
const pkg = fs.readFileSync("package.json", "utf8");
const checks: Record<string, boolean> = {
  lifecycle_module_exists: fs.existsSync("backend/model_lifecycle.py"),
  route_evaluate: main.includes("/api/v1/models/evaluate"),
  route_report: main.includes("/api/v1/models/lifecycle-report"),
  route_delete: main.includes("/api/v1/models/delete"),
  probes_tags: lifecycle.includes("/api/tags"),
  uses_generate: lifecycle.includes("/api/generate"),
  delete_endpoint: lifecycle.includes("/api/delete"),
  protected_patterns: lifecycle.includes("PROTECTED_PATTERNS"),
  quarantine_gate: lifecycle.includes("QUARANTINE"),
  trainable_gate: lifecycle.includes("TRAINABLE"),
  approval_phrase: lifecycle.includes("DELETE {model}"),
  writes_report: lifecycle.includes("latest_model_lifecycle_report.json"),
  package_script: pkg.includes("qa:model-lifecycle"),
};
const blockers = Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k);
console.log(JSON.stringify({
  generated_at: new Date().toISOString(),
  status: blockers.length ? "FAIL" : "PASS",
  checks,
  blockers,
}, null, 2));
if (blockers.length) process.exit(1);
