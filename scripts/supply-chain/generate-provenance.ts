import crypto from "node:crypto";
import fs from "node:fs";
import { execSync } from "node:child_process";

const VERSION = "v0.1.2-SUPPLY-CHAIN-PROVENANCE";
const RELEASE_DIR = `dist/releases/${VERSION}`;
const EVIDENCE_PATH = `${RELEASE_DIR}/baseline_evidence_pack.json`;

function run(command: string): string {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "unknown";
  }
}

function sha256(path: string): string {
  return crypto.createHash("sha256").update(fs.readFileSync(path)).digest("hex");
}

if (!fs.existsSync(EVIDENCE_PATH)) {
  const sourcePack = "dist/baseline_evidence_pack.json";
  if (fs.existsSync(sourcePack)) {
    fs.mkdirSync(RELEASE_DIR, { recursive: true });
    fs.copyFileSync(sourcePack, EVIDENCE_PATH);
    const sourceChecksum = "dist/baseline_evidence_pack.json.sha256";
    if (fs.existsSync(sourceChecksum)) {
      fs.copyFileSync(sourceChecksum, `${EVIDENCE_PATH}.sha256`);
    }
  } else {
    throw new Error(`Missing evidence pack: ${EVIDENCE_PATH}`);
  }
}

const statement = {
  _type: "https://in-toto.io/Statement/v1",
  subject: [
    {
      name: "baseline_evidence_pack.json",
      digest: {
        sha256: sha256(EVIDENCE_PATH),
      },
    },
  ],
  predicateType: "https://slsa.dev/provenance/v1",
  predicate: {
    buildDefinition: {
      buildType: "https://hoch-agent-swarm.local/buildTypes/baseline-lock/v1",
      externalParameters: {
        version: VERSION,
        branch: run("git rev-parse --abbrev-ref HEAD"),
      },
      internalParameters: {
        baseline_chain: [
          "v0.1.0-RT-LOCK",
          "v0.1.1-HOCHSTER-CLUSTER-HARDENING",
          VERSION,
        ],
      },
      resolvedDependencies: [
        {
          uri: "git+file://hoch-agent-swarm",
          digest: {
            gitCommit: run("git rev-parse HEAD"),
          },
        },
      ],
    },
    runDetails: {
      builder: {
        id: process.env.GITHUB_ACTIONS
          ? "github-actions"
          : "local-hoch-agent-swarm",
      },
      metadata: {
        invocationId: process.env.GITHUB_RUN_ID ?? `local-${Date.now()}`,
        startedOn: new Date().toISOString(),
        finishedOn: new Date().toISOString(),
      },
      byproducts: [
        {
          name: "baseline_evidence_pack.json",
          digest: {
            sha256: sha256(EVIDENCE_PATH),
          },
        },
      ],
    },
  },
};

fs.mkdirSync(RELEASE_DIR, { recursive: true });
fs.writeFileSync(
  `${RELEASE_DIR}/provenance.intoto.jsonl`,
  `${JSON.stringify(statement)}\n`
);
console.log(`Wrote ${RELEASE_DIR}/provenance.intoto.jsonl`);
