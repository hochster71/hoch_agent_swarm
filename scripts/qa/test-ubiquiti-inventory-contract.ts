import fs from "node:fs";

const main = fs.readFileSync("backend/main.py", "utf8");
const inv = fs.readFileSync("backend/ubiquiti_inventory.py", "utf8");
const pkg = fs.readFileSync("package.json", "utf8");

const checks: Record<string, boolean> = {
  module_exists: fs.existsSync("backend/ubiquiti_inventory.py"),
  route_exists: main.includes("/api/v1/ubiquiti/inventory"),
  uses_env_base: inv.includes("UNIFI_BASE_URL"),
  uses_env_user: inv.includes("UNIFI_USERNAME"),
  uses_env_password: inv.includes("UNIFI_PASSWORD"),
  active_clients: inv.includes("stat/sta"),
  known_clients: inv.includes("rest/user"),
  network_devices: inv.includes("stat/device"),
  health: inv.includes("stat/health"),
  billie_filter: inv.includes("billie"),
  writes_artifact: inv.includes("latest_ubiquiti_inventory.json"),
  package_script: pkg.includes("qa:ubiquiti-inventory"),
};

const blockers = Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k);

console.log(JSON.stringify({
  generated_at: new Date().toISOString(),
  status: blockers.length ? "FAIL" : "PASS",
  checks,
  blockers,
}, null, 2));

if (blockers.length) process.exit(1);
