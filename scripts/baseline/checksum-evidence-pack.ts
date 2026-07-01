import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const evidencePath =
  process.env.BASELINE_EVIDENCE_PACK ??
  "dist/baseline_evidence_pack.json";

if (!fs.existsSync(evidencePath)) {
  throw new Error(`Evidence pack not found: ${evidencePath}`);
}

const buffer = fs.readFileSync(evidencePath);
const sha256 = crypto.createHash("sha256").update(buffer).digest("hex");
const checksumPath = `${evidencePath}.sha256`;

// Write the sha256 checksum file
fs.writeFileSync(checksumPath, `${sha256}  ${path.basename(evidencePath)}\n`);

const integrityPath = "artifacts/baseline/evidence-integrity.json";
fs.mkdirSync("artifacts/baseline", { recursive: true });
fs.writeFileSync(
  integrityPath,
  JSON.stringify(
    {
      generated_at: new Date().toISOString(),
      evidence_pack: evidencePath,
      sha256,
      signed: false,
      signature_ref: null,
      status: "pass",
    },
    null,
    2
  )
);

// Inject back into the evidence pack JSON to avoid stale/out-of-sync integrity blocks
try {
  const packContent = JSON.parse(buffer.toString("utf-8"));
  packContent.integrity = {
    sha256,
    signed: false,
    signature_ref: null,
  };
  fs.writeFileSync(evidencePath, JSON.stringify(packContent, null, 2), "utf-8");
  console.log(` [PASS] Updated report integrity block in ${evidencePath}.`);
} catch (e) {
  console.warn(` [WARNING] Could not update integrity block in json:`, e);
}

console.log(`sha256=${sha256}`);
