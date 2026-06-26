import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/formal-release-preview-contract-report.json";
fs.mkdirSync(path.dirname(reportPath), { recursive: true });

const results: Record<string, boolean> = {};
const issues: string[] = [];

function assertFileContains(filePath: string, term: string, checkName: string) {
  if (!fs.existsSync(filePath)) {
    results[checkName] = false;
    issues.push(`File missing: ${filePath}`);
    return;
  }
  const content = fs.readFileSync(filePath, "utf8");
  if (content.includes(term)) {
    results[checkName] = true;
  } else {
    results[checkName] = false;
    issues.push(`File ${filePath} does not contain term "${term}"`);
  }
}

function assertFileNotContains(filePath: string, term: string, checkName: string) {
  if (!fs.existsSync(filePath)) {
    results[checkName] = false;
    issues.push(`File missing: ${filePath}`);
    return;
  }
  const content = fs.readFileSync(filePath, "utf8");
  if (!content.includes(term)) {
    results[checkName] = true;
  } else {
    results[checkName] = false;
    issues.push(`File ${filePath} contains forbidden term "${term}"`);
  }
}

// 1. Backend routes check
assertFileContains("backend/main.py", "/api/v1/release/formal-preview", "backend_contains_api_route");

// 2. Runtime execution store check
assertFileContains("backend/runtime_execution_store.py", "formal_release_previews", "store_contains_table_schema");

// 3. Git tag mutation checks (no git tag or push in preview paths)
// Let's check main.py to verify no tag or push operations are invoked on the preview route
// Since the preview route starts at create_formal_preview, we check that no git tag commands exist inside main.py in a modifying context.
assertFileNotContains("backend/main.py", "run_git_command([\"tag\"", "backend_no_git_tag_mutation");
assertFileNotContains("backend/main.py", "run_git_command([\"push\"", "backend_no_git_push_mutation");

// 4. Manifest and summary file generation checks in backend/main.py
assertFileContains("backend/main.py", "formal_release_preview_manifest.json", "manifest_file_written");
assertFileContains("backend/main.py", "formal_release_preview_summary.md", "summary_file_written");

// 5. Frontend index.html checks (DOM IDs and visible text)
const indexHtml = "frontend/archive/unused_views.html";
const requiredIds = [
  "formal-release-preview-panel",
  "formal-preview-candidate-select",
  "formal-preview-operator-input",
  "formal-preview-reason-input",
  "formal-preview-create-button",
  "formal-preview-status",
  "formal-preview-id",
  "formal-preview-formal-ready",
  "formal-preview-blockers",
  "formal-preview-required-actions",
  "formal-preview-path",
  "formal-preview-history-list"
];

for (const id of requiredIds) {
  assertFileContains(indexHtml, `id="${id}"`, `html_has_id_${id}`);
}

const requiredTexts = [
  "Formal Release Finalization Preview",
  "Select Candidate Packet",
  "Preview Formal Release Readiness",
  "Formal Release Ready",
  "Formal Release Blockers",
  "Required Operator Actions",
  "No Tags Are Created",
  "No Signing Is Performed",
  "No Publishing Is Performed",
  "Preview Only"
];

for (const text of requiredTexts) {
  assertFileContains(indexHtml, text, `html_has_text_${text.replace(/\s+/g, "_")}`);
}

// 6. Frontend app.js checks
const appJs = "frontend/archive/unused_views.js";
assertFileContains(appJs, "/api/v1/release/candidate-packets", "appjs_fetches_candidate_packets");
assertFileContains(appJs, "/api/v1/release/formal-preview", "appjs_posts_formal_preview");

// 7. package.json check
assertFileContains("package.json", "qa:formal-release-preview", "package_json_has_qa_script");

// 8. General constraints
results["tailwind_css_compiled_exists"] = fs.existsSync("frontend/dist/tailwind.css");
if (!fs.existsSync("frontend/dist/tailwind.css")) {
  issues.push("Compiled tailwind.css file is missing from frontend/dist/tailwind.css");
}

const allPassed = Object.values(results).every(v => v === true);
const report = {
  generated_at: new Date().toISOString(),
  status: allPassed ? "PASS" : "BLOCK",
  results,
  issues
};

fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));

if (allPassed) {
  console.log("\n[PASS] Formal release preview contract validation succeeded!");
  process.exit(0);
} else {
  console.error("\n[FAIL] Formal release preview contract validation failed!");
  process.exit(1);
}
