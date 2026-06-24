import fs from "node:fs";
import { execSync } from "node:child_process";

const VERSION = "v0.1.2-SUPPLY-CHAIN-PROVENANCE";
const RELEASE_DIR = `dist/releases/${VERSION}`;

function run(command: string): string {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

const packageJson = JSON.parse(fs.readFileSync("package.json", "utf8"));
const lockHash = fs.existsSync("package-lock.json")
  ? run("shasum -a 256 package-lock.json").split(" ")[0]
  : null;

const packages = Object.entries({
  ...(packageJson.dependencies ?? {}),
  ...(packageJson.devDependencies ?? {}),
}).map(([name, version]) => ({
  SPDXID: `SPDXRef-Package-${name.replace(/[^A-Za-z0-9.-]/g, "-")}`,
  name,
  versionInfo: String(version),
  downloadLocation: "NOASSERTION",
  filesAnalyzed: false,
  licenseConcluded: "NOASSERTION",
  licenseDeclared: "NOASSERTION",
  copyrightText: "NOASSERTION",
}));

const sbom = {
  spdxVersion: "SPDX-2.3",
  dataLicense: "CC0-1.0",
  SPDXID: "SPDXRef-DOCUMENT",
  name: "hoch-agent-swarm",
  documentNamespace: `https://hoch-agent-swarm.local/sbom/${VERSION}/${Date.now()}`,
  creationInfo: {
    created: new Date().toISOString(),
    creators: ["Tool: hoch-agent-swarm-generate-sbom"],
  },
  packages,
  documentDescribes: packages.map((pkg) => pkg.SPDXID),
  externalDocumentRefs: lockHash
    ? [
        {
          externalDocumentId: "DocumentRef-package-lock",
          spdxDocument: "package-lock.json",
          checksum: {
            algorithm: "SHA256",
            checksumValue: lockHash,
          },
        },
      ]
    : [],
};

fs.mkdirSync(RELEASE_DIR, { recursive: true });
fs.writeFileSync(`${RELEASE_DIR}/sbom.spdx.json`, JSON.stringify(sbom, null, 2));
console.log(`Wrote ${RELEASE_DIR}/sbom.spdx.json`);
