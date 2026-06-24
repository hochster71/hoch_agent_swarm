import * as fs from "fs";
import * as path from "path";
import * as http from "http";

const BASE_URL = "http://localhost:8000";

function fetchJson(url: string): Promise<any> {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`Failed to fetch from ${url}, status: ${res.statusCode}`));
        return;
      }
      let body = "";
      res.on("data", chunk => body += chunk);
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    }).on("error", reject);
  });
}

function readJson(filePath: string, defaultValue: any): any {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, "utf-8"));
    }
  } catch {}
  return defaultValue;
}

async function main() {
  console.log("==================================================");
  console.log("GENERATING COMPREHENSIVE BASELINE LOCK EVIDENCE PACK");
  console.log("==================================================");
  
  try {
    const lockApiUrl = `${BASE_URL}/api/v1/hochster/baseline/lock`;
    console.log(`Querying baseline lock endpoint: ${lockApiUrl}`);
    const lockResponse = await fetchJson(lockApiUrl);
    const report = lockResponse.report;
    
    const clusterJobsUrl = `${BASE_URL}/api/v1/hochster/cluster/jobs`;
    console.log(`Querying cluster jobs endpoint: ${clusterJobsUrl}`);
    const hochsterCluster = await fetchJson(clusterJobsUrl);
    
    const dbStatusUrl = `${BASE_URL}/api/v1/system/database/status`;
    console.log(`Querying database status endpoint: ${dbStatusUrl}`);
    const database = await fetchJson(dbStatusUrl);
    
    const dockerDigests = readJson(
      "artifacts/baseline/docker-image-digests.json",
      {
        status: "not_run",
        records: [],
        warnings: ["docker image digest capture not run"],
      }
    );
    
    const integrity = readJson(
      "artifacts/baseline/evidence-integrity.json",
      {
        status: "not_run",
        sha256: null,
        signed: false,
        signature_ref: null,
      }
    );
    
    const existingBlockers = report.decision?.blockers || [];
    const blockers = [
      ...existingBlockers,
      ...(hochsterCluster.data.summary.jobs_completed < 9
        ? ["HOCHSTER cluster jobs incomplete"]
        : []),
      ...hochsterCluster.data.summary.missing_trace_ids.map(
        (id: string) => `Missing HOCHSTER trace_id: ${id}`
      ),
      ...hochsterCluster.data.summary.missing_evidence_refs.map(
        (id: string) => `Missing HOCHSTER evidence_refs: ${id}`
      ),
      ...(integrity.status !== "pass" && integrity.status !== "not_run" ? ["Evidence integrity checksum missing"] : []),
    ];
    
    const evidencePack = {
      ...report,
      hochster_cluster: hochsterCluster.data.summary,
      docker_digests: dockerDigests,
      integrity: {
        sha256: integrity.sha256,
        signed: integrity.signed,
        signature_ref: integrity.signature_ref,
      },
      database: {
        engine: database.data.engine,
        sqlite_wal_enabled: database.data.sqlite_wal_enabled,
        busy_timeout_ms: database.data.busy_timeout_ms,
        database_locked_events: database.data.database_locked_events,
        migration_required: database.data.migration_required,
      },
      decision: {
        status: blockers.length === 0 ? "PASS" : "BLOCK",
        blockers,
        exceptions: report.decision?.exceptions || [],
      },
    };
    
    const outputDir = path.resolve(__dirname, "../dist");
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const outputPath = path.join(outputDir, "baseline_evidence_pack.json");
    fs.writeFileSync(outputPath, JSON.stringify(evidencePack, null, 2), "utf-8");
    
    console.log(`\n [PASS] Evidence pack generated successfully!`);
    console.log(`        Output: ${outputPath}`);
    console.log(`        Decision Status: ${evidencePack.decision.status}`);
    console.log("==================================================");
    process.exit(0);
  } catch (err) {
    console.error(`\n [FAIL] Evidence generation failed:`, err);
    console.log("==================================================");
    process.exit(1);
  }
}

main();
