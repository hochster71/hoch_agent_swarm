import { execSync } from "node:child_process";
import fs from "node:fs";

type DockerDigestRecord = {
  repository: string;
  tag: string;
  digest: string;
  image_id: string;
  created_since: string;
  size: string;
  captured_at: string;
};

function run(command: string): string {
  try {
    return execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch (err) {
    return "";
  }
}

function main() {
  const capturedAt = new Date().toISOString();
  const output = run("docker images --digests --format '{{json .}}'");
  const records: DockerDigestRecord[] = output
    ? output.split("\n").map((line) => {
        try {
          const raw = JSON.parse(line);
          return {
            repository: raw.Repository || "",
            tag: raw.Tag || "",
            digest: raw.Digest || "",
            image_id: raw.ID || "",
            created_since: raw.CreatedSince || "",
            size: raw.Size || "",
            captured_at: capturedAt,
          };
        } catch {
          return null;
        }
      }).filter((r): r is DockerDigestRecord => r !== null)
    : [];

  const missingDigests = records.filter(
    (record) => !record.digest || record.digest === "<none>"
  );

  const isCi = process.env.CI === "true";
  
  // If we have records and none are missing, it's a pass. Otherwise, it is a warning locally, and a blocker in CI.
  const status = (missingDigests.length === 0 && records.length > 0) 
    ? "pass" 
    : (isCi ? "block" : "warning");

  const warnings = [
    ...missingDigests.map((record) => `${record.repository}:${record.tag} missing digest`),
    ...(records.length === 0 ? ["Docker daemon unreachable or no images found. Fallback warnings active."] : [])
  ];

  const report = {
    generated_at: capturedAt,
    records,
    missing_digest_count: missingDigests.length,
    status,
    warnings,
  };

  fs.mkdirSync("artifacts/baseline", { recursive: true });
  fs.writeFileSync(
    "artifacts/baseline/docker-image-digests.json",
    JSON.stringify(report, null, 2)
  );
  console.log(JSON.stringify(report, null, 2));

  if (isCi && status === "block") {
    process.exit(1);
  }
}
main();
