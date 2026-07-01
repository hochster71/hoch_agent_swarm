import fs from "node:fs";

function read(path: string): string {
  return fs.existsSync(path) ? fs.readFileSync(path, "utf8") : "";
}

const files = {
  backend: read("backend/mesh_sentinel.py"),
  main: read("backend/main.py"),
  html: read("frontend/index.html"),
  js: read("frontend/app.js"),
  css: read("frontend/styles.css"),
  pkg: read("package.json"),
  featureMap: read("config/live_runtime_feature_map.json"),
};

const activeFrontend = `${files.html}\n${files.js}`;

const forbidden = [
  "43 agents operational",
  "Mean cluster CPU load",
  "HEALTHY 100%",
  "10 ASSETS ACTIVE",
  "YouTube Research Lane",
  "Kimi-Style Comic Swarm Demo",
  "Boss Noodle",
  "Dr. Signal",
];

const checks: Record<string, boolean> = {
  backend_module_exists: fs.existsSync("backend/mesh_sentinel.py"),
  endpoint_registered: files.main.includes("/api/v1/mesh-sentinel/map"),
  backend_build_function: files.backend.includes("build_mesh_sentinel_map"),
  frontend_view_exists: files.html.includes("Mesh Sentinel"),
  frontend_fetches_map: files.js.includes("/api/v1/mesh-sentinel/map"),
  frontend_rescan_wired: files.js.includes("/api/v1/discovery/ai-runtimes/rescan"),
  rescan_button_visible: files.html.includes("Rescan AI Runtimes"),
  map_container_exists: files.html.includes("mesh-sentinel-map"),
  truth_state_rendered: files.js.includes("truth") && files.html.includes("mesh-truth-state"),
  source_endpoint_rendered: files.js.includes("source") && files.html.includes("/api/v1/mesh-sentinel/map"),
  feature_map_registered: files.featureMap.includes("mesh-sentinel"),
  package_script_exists: files.pkg.includes("qa:mesh-sentinel"),
  ui_contract_invokes: files.pkg.includes("qa:mesh-sentinel"),
  css_theme_exists: files.css.includes("mesh-sentinel-map"),
};

for (const token of forbidden) {
  checks[`forbidden_absent_${token}`] = !activeFrontend.includes(token);
}

const issues = Object.entries(checks).filter(([, ok]) => !ok).map(([name]) => name);

console.log(JSON.stringify({
  generated_at: new Date().toISOString(),
  status: issues.length ? "FAIL" : "PASS",
  checks,
  issues,
}, null, 2));

if (issues.length) process.exit(1);
