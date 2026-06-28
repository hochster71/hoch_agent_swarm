import fs from "fs";
import path from "path";

const blockers: string[] = [];

function exists(p: string) {
  return fs.existsSync(path.resolve(p));
}

function read(p: string) {
  return fs.readFileSync(path.resolve(p), "utf8");
}

if (!exists("frontend/index.html")) blockers.push("Missing legacy production entry: frontend/index.html");
if (!exists("frontend/app.js")) blockers.push("Missing legacy production app binding: frontend/app.js");
if (!exists("frontend/src/main.tsx")) blockers.push("Missing React candidate entry: frontend/src/main.tsx");
if (!exists("frontend/package.json")) blockers.push("Missing nested React frontend package.json");

if (exists("frontend/index.html")) {
  const html = read("frontend/index.html");
  if (html.includes('/src/main.tsx') || html.includes("src/main.tsx")) {
    blockers.push("React candidate main.tsx is directly referenced by legacy frontend/index.html before explicit promotion");
  }
  if (!html.includes("view-remediation-safety")) {
    blockers.push("Legacy UI lost view-remediation-safety contract anchor");
  }
}

if (exists("package.json")) {
  const rootPkg = JSON.parse(read("package.json"));
  const scripts = rootPkg.scripts || {};
  if (!scripts["qa:view-contract"]) blockers.push("Root package missing qa:view-contract");
  if (!scripts["qa:no-tailwind-cdn"]) blockers.push("Root package missing qa:no-tailwind-cdn");
  if (!scripts["qa:ui-contract"]) blockers.push("Root package missing qa:ui-contract");
}

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length ? "BLOCK" : "PASS",
  blockers,
};

fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync("artifacts/qa/frontend-entrypoint-contract-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

if (blockers.length) process.exit(1);
