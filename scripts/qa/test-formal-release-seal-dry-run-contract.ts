import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/formal-release-seal-dry-run-contract-report.json";
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
assertFileContains("backend/main.py", "/api/v1/release/formal-preview/{formal_preview_id}/seal-dry-run", "backend_contains_api_route");
assertFileContains("backend/main.py", "/api/v1/release/seal-dry-run", "backend_contains_list_route");
assertFileContains("backend/main.py", "formal_release_seal_dry_run_manifest.json", "manifest_file_written");
assertFileContains("backend/main.py", "formal_release_seal_dry_run_report.md", "report_file_written");

// 2. Git tag/push mutation checks (no git tag or push in preview/approval/seal paths)
assertFileNotContains("backend/main.py", "run_git_command([\"tag\"", "backend_no_git_tag_mutation");
assertFileNotContains("backend/main.py", "run_git_command([\"push\"", "backend_no_git_push_mutation");

// 3. Frontend index.html checks (DOM IDs)
const indexHtml = "frontend/archive/unused_views.html";
assertFileContains(indexHtml, `id="formal-release-seal-dry-run-panel"`, `html_has_id_seal_panel`);
assertFileContains(indexHtml, `id="seal-dry-run-preview-select"`, `html_has_id_preview_select`);
assertFileContains(indexHtml, `id="seal-dry-run-operator-input"`, `html_has_id_operator_input`);
assertFileContains(indexHtml, `id="seal-dry-run-execute-button"`, `html_has_id_execute_button`);
assertFileContains(indexHtml, `id="seal-dry-run-status"`, `html_has_id_seal_status`);
assertFileContains(indexHtml, `id="seal-dry-run-id"`, `html_has_id_seal_id`);
assertFileContains(indexHtml, `id="seal-dry-run-manifest-path"`, `html_has_id_manifest_path`);
assertFileContains(indexHtml, `id="seal-dry-run-report-path"`, `html_has_id_report_path`);
assertFileContains(indexHtml, `id="seal-dry-run-blockers"`, `html_has_id_blockers`);
assertFileContains(indexHtml, `id="seal-dry-run-history-list"`, `html_has_id_history_list`);

// 4. Frontend app.js checks
const appJs = "frontend/archive/unused_views.js";
assertFileContains(appJs, "initFormalReleaseSealDryRun", "appjs_has_init_function");
assertFileContains(appJs, "loadApprovedPreviewsForDryRun", "appjs_has_load_function");
assertFileContains(appJs, "executeSealDryRun", "appjs_has_execute_function");
assertFileContains(appJs, "loadSealDryRunHistory", "appjs_has_history_function");

// 5. package.json check
assertFileContains("package.json", "qa:formal-release-seal-dry-run", "package_json_has_qa_script");

// 6. General constraints
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
  console.log("\n[PASS] Formal release seal dry run contract validation succeeded!");
  process.exit(0);
} else {
  console.error("\n[FAIL] Formal release seal dry run contract validation failed!");
  process.exit(1);
}
