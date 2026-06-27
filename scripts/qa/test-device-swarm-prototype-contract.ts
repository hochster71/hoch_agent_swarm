import fs from "node:fs";

const main = fs.readFileSync("backend/main.py", "utf8");
const backend = fs.readFileSync("backend/swarm_device_mesh.py", "utf8");
const html = fs.readFileSync("frontend/index.html", "utf8");
const js = fs.readFileSync("frontend/app.js", "utf8");
const css = fs.readFileSync("frontend/styles.css", "utf8");
const proto = fs.readFileSync("artifacts/ui/hoch_10_device_swarm_prototype.html", "utf8");
const pkg = fs.readFileSync("package.json", "utf8");

const checks: Record<string, boolean> = {
  backend_exists: fs.existsSync("backend/swarm_device_mesh.py"),
  route_devices: main.includes("/api/v1/swarm/devices"),
  route_rescan: main.includes("/api/v1/swarm/devices/rescan"),
  route_chat: main.includes("/api/v1/swarm/agent-chat"),
  probes_lmstudio: backend.includes("/v1/models"),
  probes_ollama: backend.includes("/api/tags"),
  includes_expected_10_0_0_8: backend.includes("10.0.0.8"),
  includes_expected_10_0_0_241: backend.includes("10.0.0.241"),
  includes_expected_10_devices: backend.includes("EXPECTED_DEVICES"),
  frontend_view: html.includes("HOCH 10-Device Agent Swarm"),
  frontend_nav: html.includes("Device Swarm"),
  frontend_fetch_devices: js.includes("/api/v1/swarm/devices?limit=10"),
  frontend_rescan: js.includes("/api/v1/swarm/devices/rescan?limit=10"),
  frontend_chat: js.includes("/api/v1/swarm/agent-chat"),
  css_cards: css.includes(".device-swarm-card"),
  standalone_proto: proto.includes("HOCH 10-Device Agent Swarm Prototype"),
  package_script: pkg.includes("qa:device-swarm-prototype"),
};

const blockers = Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k);

console.log(JSON.stringify({
  generated_at: new Date().toISOString(),
  status: blockers.length ? "FAIL" : "PASS",
  checks,
  blockers,
}, null, 2));

if (blockers.length) process.exit(1);
