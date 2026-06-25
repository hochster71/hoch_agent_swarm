import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/release-seal-attestation-contract-report.json";
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
assertFileContains("backend/main.py", "/api/v1/release/attestation-bundles", "backend_contains_list_route");
assertFileContains("backend/main.py", "/api/v1/release/seal-dry-run/{seal_dry_run_id}/attestation-bundle", "backend_contains_post_route");
assertFileContains("backend/runtime_execution_store.py", "release_seal_attestation_bundles", "db_has_table");

// 2. Generator script checks
assertFileContains("scripts/supply-chain/generate-release-seal-attestation-bundle.ts", "release_seal_attestation_bundle_manifest.json", "generator_writes_manifest");
assertFileContains("scripts/supply-chain/generate-release-seal-attestation-bundle.ts", "release_seal_attestation_bundle_summary.md", "generator_writes_summary");
assertFileContains("scripts/supply-chain/generate-release-seal-attestation-bundle.ts", "computeSha256", "generator_computes_checksums");

// 3. UI Panel Checks (DOM IDs)
const indexHtml = "frontend/index.html";
assertFileContains(indexHtml, `id="release-seal-attestation-panel"`, "html_has_id_panel");
assertFileContains(indexHtml, `id="attestation-seal-dry-run-select"`, "html_has_id_select");
assertFileContains(indexHtml, `id="attestation-operator-input"`, "html_has_id_operator");
assertFileContains(indexHtml, `id="attestation-reason-input"`, "html_has_id_reason");
assertFileContains(indexHtml, `id="attestation-create-button"`, "html_has_id_button");
assertFileContains(indexHtml, `id="attestation-status"`, "html_has_id_status");
assertFileContains(indexHtml, `id="attestation-bundle-id"`, "html_has_id_bundle_id");
assertFileContains(indexHtml, `id="attestation-bundle-path"`, "html_has_id_bundle_path");
assertFileContains(indexHtml, `id="attestation-formal-ready"`, "html_has_id_ready");
assertFileContains(indexHtml, `id="attestation-no-mutation-guarantee"`, "html_has_id_guarantee");
assertFileContains(indexHtml, `id="attestation-artifact-list"`, "html_has_id_artifact_list");
assertFileContains(indexHtml, `id="attestation-checksum-list"`, "html_has_id_checksum_list");
assertFileContains(indexHtml, `id="attestation-missing-artifacts"`, "html_has_id_missing_list");
assertFileContains(indexHtml, `id="attestation-history-list"`, "html_has_id_history_list");

// 4. UI Visible Texts
assertFileContains(indexHtml, "Release Seal Attestation Bundle", "html_text_title");
assertFileContains(indexHtml, "Select Seal Dry Run", "html_text_select");
assertFileContains(indexHtml, "Generate Attestation Bundle", "html_text_generate");
assertFileContains(indexHtml, "Attestation Status", "html_text_status");
assertFileContains(indexHtml, "Bundle ID", "html_text_bundle_id");
assertFileContains(indexHtml, "Included Evidence Artifacts", "html_text_artifacts");
assertFileContains(indexHtml, "Artifact Checksums", "html_text_checksums");
assertFileContains(indexHtml, "Missing Artifacts", "html_text_missing");
assertFileContains(indexHtml, "No Mutation Guarantee", "html_text_guarantee");
assertFileContains(indexHtml, "No Tags Are Created", "html_text_no_tags");
assertFileContains(indexHtml, "No Signing Is Performed", "html_text_no_signing");
assertFileContains(indexHtml, "No Publishing Is Performed", "html_text_no_publishing");
assertFileContains(indexHtml, "Attestation Is Not A Formal Release", "html_text_not_formal");

// 5. app.js endpoints & functions
const appJs = "frontend/app.js";
assertFileContains(appJs, "/api/v1/release/attestation-bundles", "appjs_fetches_bundles");
assertFileContains(appJs, "/api/v1/release/seal-dry-run/", "appjs_posts_attestation");

// 6. package.json check
const pkgJson = "package.json";
assertFileContains(pkgJson, "release:seal-attestation", "package_has_release_script");
assertFileContains(pkgJson, "qa:release-seal-attestation", "package_has_qa_script");
assertFileContains(pkgJson, "e2e:release-seal-attestation", "package_has_e2e_script");

// 7. Safety constraints
assertFileNotContains("scripts/supply-chain/generate-release-seal-attestation-bundle.ts", "git tag", "no_git_tag_in_generator");
assertFileNotContains("scripts/supply-chain/generate-release-seal-attestation-bundle.ts", "git push", "no_git_push_in_generator");
assertFileNotContains(indexHtml, "cdn.tailwindcss.com", "no_tailwind_cdn");
assertFileNotContains(indexHtml, "/src/main.tsx", "no_react_main_tsx");

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
  console.log("\n[PASS] Release seal attestation bundle contract validation succeeded!");
  process.exit(0);
} else {
  console.error("\n[FAIL] Release seal attestation bundle contract validation failed!");
  process.exit(1);
}
