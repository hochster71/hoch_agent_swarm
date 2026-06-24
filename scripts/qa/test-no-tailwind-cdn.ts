import fs from "node:fs";
import path from "node:path";

const roots = ["frontend"];
const forbidden = "cdn.tailwindcss.com";
const blockers: string[] = [];

function walk(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (["node_modules", "dist", ".git", ".cache"].includes(entry.name)) return [];
      return walk(full);
    }
    if (!/\.(html|js|ts|tsx|css)$/.test(entry.name)) return [];
    return [full];
  });
}

for (const root of roots) {
  for (const file of walk(root)) {
    const text = fs.readFileSync(file, "utf8");
    if (text.includes(forbidden)) {
      blockers.push(`${file} contains forbidden production CDN: ${forbidden}`);
    }
  }
}

const report = {
  generated_at: new Date().toISOString(),
  status: blockers.length === 0 ? "PASS" : "BLOCK",
  blockers,
};

fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync("artifacts/qa/no-tailwind-cdn-report.json", JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));

if (blockers.length) process.exit(1);
