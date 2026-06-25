import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/formal-release-approval-contract-report.json";
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
assertFileContains("backend/main.py", "/api/v1/release/formal-preview/{formal_preview_id}/approve-request", "backend_contains_api_route");
assertFileContains("backend/main.py", "formal_release_approval_report.json", "manifest_file_written");
assertFileContains("backend/main.py", "formal_release_approval_report.md", "summary_file_written");

// 2. Git tag mutation checks (no git tag or push in preview/approval paths)
assertFileNotContains("backend/main.py", "run_git_command([\"tag\"", "backend_no_git_tag_mutation");
assertFileNotContains("backend/main.py", "run_git_command([\"push\"", "backend_no_git_push_mutation");

// 3. Frontend index.html checks (DOM IDs)
const indexHtml = "frontend/index.html";
assertFileContains(indexHtml, `id="formal-preview-request-approval-button"`, `html_has_id_request_button`);
assertFileContains(indexHtml, `id="formal-preview-approval-report-container"`, `html_has_id_report_container`);
assertFileContains(indexHtml, `id="formal-preview-approval-status"`, `html_has_id_approval_status`);
assertFileContains(indexHtml, `id="formal-preview-approval-report-path"`, `html_has_id_approval_report_path`);

// 4. Frontend app.js checks
const appJs = "frontend/app.js";
assertFileContains(appJs, "/approve-request", "appjs_posts_approve_request");
assertFileContains(appJs, "checkApprovalStatusForPreview", "appjs_checks_status");

// 5. package.json check
assertFileContains("package.json", "qa:formal-release-approval", "package_json_has_qa_script");

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
  console.log("\n[PASS] Formal release approval contract validation succeeded!");
  process.exit(0);
} else {
  console.error("\n[FAIL] Formal release approval contract validation failed!");
  process.exit(1);
}
