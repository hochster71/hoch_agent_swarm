import fs from "node:fs";
import path from "node:path";

const FORBIDDEN_TOKENS = [
  "HEALTHY 100%",
  "10 ASSETS ACTIVE",
  "SYNC: OK",
  "1.2ms",
  "Boss Noodle",
  "Dr. Signal",
  "Prof. Blueprint",
  "Eng. Patch",
  "Ms. Checkmark",
  "Capt. Guardrail",
  "Gordon Vector",
  "Prof. Ledger",
  "Eng. Rocket",
  "Kimi-Style Comic Swarm Demo",
  "Open Swarm Comic",
  "Launch Expert Swarm",
  "YouTube Research Lane",
  "Video Candidates",
  "Asset Assignment Plane",
  "SWARM ACTIVE WORKSTREAM FEED",
  "Agent Profiles",
  "Catchphrases of Swarm",
  "Docker Diagnostic Checklist",
  "CLUSTER INTEL BRIEF",
  "TERMINAL LOGS",
  "43 agents operational",
  "Mean cluster CPU load",
  "ZTA posture: ENFORCED",
  "CDAO RAI traceability: ACTIVE",
  "ConMon: STREAMING",
  "Tac-C2 Kernel Hub",
  "RMF ConMon policy rules validated"
];

// Target scan patterns
const filesToScan: string[] = [
  "frontend/index.html",
  "frontend/app.js",
  "frontend/styles.css",
  "backend/main.py"
];

const dirsToScan = [
  "config",
  "scripts/qa",
  "tests/e2e"
];

function globDir(dir: string, extension: RegExp): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...globDir(fullPath, extension));
    } else if (entry.isFile() && extension.test(entry.name)) {
      results.push(fullPath);
    }
  }
  return results;
}

const allFiles = [...filesToScan];
for (const dir of dirsToScan) {
  if (dir === "config") {
    allFiles.push(...globDir(dir, /\.(json|yaml|yml)$/));
  } else {
    allFiles.push(...globDir(dir, /\.(ts|tsx)$/));
  }
}

interface Hit {
  file: string;
  line: number;
  token: string;
  classification: "LIVE_CONVERT" | "DELETE" | "QUARANTINE" | "TEST_FIXTURE_ALLOWED";
  content: string;
}

const hits: Hit[] = [];

for (const file of allFiles) {
  if (!fs.existsSync(file)) continue;
  const content = fs.readFileSync(file, "utf8");
  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const lineContent = lines[i];
    for (const token of FORBIDDEN_TOKENS) {
      // Perform case-insensitive search
      if (lineContent.toLowerCase().includes(token.toLowerCase())) {
        let classification: "LIVE_CONVERT" | "DELETE" | "QUARANTINE" | "TEST_FIXTURE_ALLOWED" = "DELETE";
        
        const isTestOrConfig = file.includes("scripts/qa") || file.includes("tests/e2e") || file.includes("qa_evidence_matrix.json") || file.includes("live_runtime_feature_map.json");
        if (isTestOrConfig) {
          classification = "TEST_FIXTURE_ALLOWED";
        } else {
          const liveConvertTokens = ["healthy 100%", "10 assets active", "sync: ok", "1.2ms", "mean cluster cpu load", "43 agents operational"];
          if (liveConvertTokens.includes(token.toLowerCase())) {
            classification = "LIVE_CONVERT";
          } else if (token.toLowerCase().includes("comic") || token.toLowerCase().includes("youtube") || token.toLowerCase().includes("checklist") || token.toLowerCase().includes("catchphrase")) {
            classification = "QUARANTINE";
          }
        }
        
        hits.push({
          file,
          line: i + 1,
          token,
          classification,
          content: lineContent.trim()
        });
      }
    }
  }
}

// Generate artifacts/qa/live_runtime_surface_audit.json
fs.mkdirSync("artifacts/qa", { recursive: true });
fs.writeFileSync(
  "artifacts/qa/live_runtime_surface_audit.json",
  JSON.stringify({ generated_at: new Date().toISOString(), total_hits: hits.length, hits }, null, 2)
);

// Generate artifacts/qa/live_runtime_surface_gap_analysis.md
let gapAnalysis = `# Live Runtime Surface Audit Gap Analysis

Generated At: ${new Date().toISOString()}
Total Forbidden Token Hits: ${hits.length}

## Hits and Actions

| File | Line | Token | Classification | Action / Remediation |
| --- | --- | --- | --- | --- |
`;

for (const hit of hits) {
  gapAnalysis += `| \`${hit.file}\` | ${hit.line} | \`${hit.token}\` | **${hit.classification}** | ${
    hit.classification === "TEST_FIXTURE_ALLOWED"
      ? "No action required (test/contract fixture)"
      : hit.classification === "LIVE_CONVERT"
      ? "Convert to live cockpit API field or delete"
      : "Remove active reference or quarantine to archive"
  } |\n`;
}

gapAnalysis += `
## Summary of Required Actions

1. **Sidebar Navigation**: Replace all static sidebar labels with the strict allowed 9 views list.
2. **Default Cockpit Root**: Restructure root index.html view (\`view-mission-control\`) to render the 12 Live Analysis Cards.
3. **De-orbiting Mock Elements**:
   - Comic Swarm panels
   - YouTube Research Lane panels
   - Docker Diagnostic Checklist
   - Static Agent/Roster chips
   - Fake console/terminal output
4. **Active UI Verification**: Remediate \`frontend/index.html\` and \`frontend/app.js\` to guarantee zero forbidden tokens remain in active files.
`;

fs.writeFileSync("artifacts/qa/live_runtime_surface_gap_analysis.md", gapAnalysis);
console.log(`Audit complete: ${hits.length} hits found. JSON and Markdown reports written to artifacts/qa/`);
