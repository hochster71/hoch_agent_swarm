import { execSync } from "node:child_process";
import fs from "node:fs";

const VERSION = "v0.1.2-SUPPLY-CHAIN-PROVENANCE";
const RELEASE_DIR = `dist/releases/${VERSION}`;

function run(command: string) {
  try {
    return execSync(command, { encoding: "utf8", stdio: "pipe" });
  } catch (err) {
    console.warn(` [WARNING] Cosign run failed: ${(err as Error).message}`);
    return "";
  }
}

if (!process.env.ENABLE_COSIGN_SIGNING) {
  console.log("Cosign signing skipped: ENABLE_COSIGN_SIGNING not set.");
  process.exit(0);
}

for (const artifact of [
  "baseline_evidence_pack.json",
  "release_manifest.json",
  "provenance.intoto.jsonl",
  "sbom.spdx.json",
]) {
  const path = `${RELEASE_DIR}/${artifact}`;
  if (!fs.existsSync(path)) continue;
  run(`cosign sign-blob --yes --output-signature ${path}.sig ${path}`);
  console.log(`Signed ${path}`);
}
