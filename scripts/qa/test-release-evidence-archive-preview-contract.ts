import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/release-evidence-archive-preview-contract-report.json";
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

// 1. Backend API route check
assertFileContains("backend/main.py", "/api/v1/release/evidence/archive/preview", "backend_contains_api_route");

// 2. Frontend index.html checks (DOM IDs)
const indexHtml = "frontend/archive/unused_views.html";
const requiredIds = [
  "release-evidence-archive-preview-panel",
  "btn-calculate-archive-preview",
  "archive-preview-details",
  "archive-preview-path",
  "archive-preview-checksum",
  "archive-preview-count-included",
  "archive-preview-count-excluded",
  "archive-preview-count-review",
  "archive-preview-count-missing",
  "archive-preview-warnings",
  "archive-preview-warnings-list",
  "archive-preview-included-tbody",
  "btn-export-preview-markdown",
  "btn-export-preview-json"
];

for (const id of requiredIds) {
  assertFileContains(indexHtml, `id="${id}"`, `html_has_id_${id}`);
}

// 3. Frontend app.js checks
const appJs = "frontend/archive/unused_views.js";
assertFileContains(appJs, "/api/v1/release/evidence/archive/preview", "appjs_fetches_archive_preview");
assertFileContains(appJs, "initReleaseEvidenceArchivePreview", "appjs_has_init_function");
assertFileContains(appJs, "calculateArchivePreview", "appjs_has_calculate_function");
assertFileContains(appJs, "exportArchivePreviewMarkdown", "appjs_has_export_markdown_function");
assertFileContains(appJs, "exportArchivePreviewJSON", "appjs_has_export_json_function");

// 4. package.json checks
assertFileContains("package.json", "qa:release-evidence-archive-preview-contract", "package_json_has_qa_script");
assertFileContains("package.json", "e2e:release-evidence-archive-preview", "package_json_has_e2e_script");

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
  console.log("\n[PASS] Release evidence archive preview contract validation succeeded!");
  process.exit(0);
} else {
  console.error("\n[FAIL] Release evidence archive preview contract validation failed!");
  process.exit(1);
}
