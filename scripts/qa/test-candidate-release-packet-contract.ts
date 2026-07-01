import fs from "node:fs";
import path from "node:path";

const reportPath = "artifacts/qa/candidate-release-packet-contract-report.json";
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
assertFileContains("backend/main.py", "/api/v1/release/candidate-packets", "backend_contains_api_route");

// 2. Runtime execution store check
assertFileContains("backend/runtime_execution_store.py", "candidate_release_packets", "store_contains_table_schema");

// 3. Git tag mutation check in backend/main.py
assertFileNotContains("backend/main.py", "run_git_command([\"tag\"", "backend_no_git_tag_mutation");
assertFileNotContains("backend/main.py", "run_git_command([\"push\"", "backend_no_git_push_mutation");

// 4. TS generator script check
const generatorPath = "scripts/supply-chain/generate-candidate-release-packet.ts";
results["ts_generator_exists"] = fs.existsSync(generatorPath);
if (!fs.existsSync(generatorPath)) {
  issues.push(`TS generator script missing: ${generatorPath}`);
} else {
  assertFileContains(generatorPath, "candidate_packet_manifest.json", "ts_generator_writes_manifest");
  assertFileContains(generatorPath, "candidate_packet_summary.md", "ts_generator_writes_summary");
}

// 5. Frontend index.html checks (DOM IDs and visible text)
const indexHtml = "frontend/archive/unused_views.html";
const requiredIds = [
  "candidate-release-packet-panel",
  "candidate-packet-version-input",
  "candidate-packet-operator-input",
  "candidate-packet-reason-input",
  "candidate-packet-channel-select",
  "candidate-packet-create-button",
  "candidate-packet-status",
  "candidate-packet-id",
  "candidate-packet-path",
  "candidate-packet-formal-ready",
  "candidate-packet-blockers",
  "candidate-packet-artifact-list",
  "candidate-packet-history-list"
];

for (const id of requiredIds) {
  assertFileContains(indexHtml, `id="${id}"`, `html_has_id_${id}`);
}

const requiredTexts = [
  "Candidate Release Packet Builder",
  "Candidate Version",
  "Candidate Channel",
  "Operator",
  "Reason",
  "Create Candidate Packet",
  "Candidate Packet Status",
  "Formal Release Ready",
  "Formal Release Blockers",
  "Included Evidence Artifacts",
  "Candidate Packet History",
  "No Tags Are Created Automatically",
  "Formal Release Still Requires Signing and Tag Alignment"
];

for (const text of requiredTexts) {
  assertFileContains(indexHtml, text, `html_has_text_${text.replace(/\s+/g, "_")}`);
}

// 6. Frontend app.js checks
const appJs = "frontend/archive/unused_views.js";
assertFileContains(appJs, "/api/v1/release/candidate-packets", "appjs_calls_candidate_packets_api");
assertFileContains(appJs, '"POST"', "appjs_calls_post_api");

// 7. package.json check
assertFileContains("package.json", "qa:candidate-release-packet", "package_json_has_qa_script");

// 8. General constraints
assertFileNotContains(indexHtml, "cdn.tailwindcss.com", "no_cdn_tailwindcss");
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
  console.log("\n[PASS] Candidate release packet contract validation succeeded!");
  process.exit(0);
} else {
  console.error("\n[FAIL] Candidate release packet contract validation failed!");
  process.exit(1);
}
