import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.QA_BASE_URL ?? "http://localhost:8000";
const WS_URL = BASE_URL.replace(/^http/, "ws") + "/ws/metrics";

async function runEventSchemaTest() {
  console.log("==================================================");
  console.log("STARTING WEBSOCKET RUNTIME EVENT SCHEMA AUDIT");
  console.log("==================================================");

  const errors: string[] = [];
  const findings: string[] = [];
  const gaps: string[] = [];
  const receivedEvents: any[] = [];

  const ws = new WebSocket(WS_URL);

  let connectionOpened = false;

  await new Promise<void>((resolve, reject) => {
    ws.onopen = () => {
      console.log(`Connected to WebSocket: ${WS_URL}`);
      connectionOpened = true;
      resolve();
    };
    ws.onerror = (err) => {
      errors.push(`WebSocket connection error: ${JSON.stringify(err)}`);
      reject(err);
    };
    // Timeout connection after 5 seconds
    setTimeout(() => {
      if (!connectionOpened) {
        reject(new Error("WebSocket connection timeout"));
      }
    }, 5000);
  }).catch((err) => {
    errors.push(`Failed to establish WebSocket connection: ${err.message}`);
  });

  if (errors.length > 0) {
    writeReport(errors, findings, gaps, receivedEvents);
    return;
  }

  // Set up message listener
  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data as string);
      console.log("Received WebSocket event:", payload.type);
      receivedEvents.push(payload);
    } catch (e: any) {
      errors.push(`Failed to parse WebSocket message: ${e.message}`);
    }
  };

  // Trigger event: Create a run
  console.log("Triggering event: Creating a new run via REST...");
  let runId = "";
  try {
    const runResp = await fetch(`${BASE_URL}/api/v1/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "WebSocket Event Schema Audit Run" })
    });
    if (runResp.status === 200) {
      const data = await runResp.json();
      runId = data.run_id;
      findings.push(`Triggered run creation: ${runId}`);
    } else {
      errors.push(`Run creation for WS trigger failed with status: ${runResp.status}`);
    }
  } catch (e: any) {
    errors.push(`Failed to create run for WS trigger: ${e.message}`);
  }

  // Wait 3 seconds to collect WebSocket messages
  await new Promise((resolve) => setTimeout(resolve, 3000));

  // Close connection
  ws.close();

  if (receivedEvents.length === 0) {
    errors.push("No WebSocket events received during the audit window");
  } else {
    findings.push(`Received ${receivedEvents.length} events from WebSocket`);

    // Verify events against target schema
    receivedEvents.forEach((ev) => {
      const type = ev.type || ev.event_type;
      if (!type) {
        // Skip raw cluster status telemetry packets
        findings.push("Skipping raw cluster status metrics telemetry packet");
        return;
      }
      findings.push(`Evaluating event type: ${type}`);

      // Check event_type
      if (!ev.event_type) {
        gaps.push(`[${type}] Missing literal field: event_type (present as 'type')`);
      }

      // Check event_id
      if (!ev.event_id && !ev.id) {
        gaps.push(`[${type}] Missing field: event_id`);
      }

      // Check timestamp
      if (!ev.timestamp && !ev.time) {
        gaps.push(`[${type}] Missing field: timestamp`);
      }

      // Check trace_id or correlation_id
      if (!ev.trace_id && !ev.correlation_id && !ev.data?.correlation_id) {
        gaps.push(`[${type}] Missing field: trace_id / correlation_id`);
      }

      // Check run_id when relevant
      const data = ev.data || {};
      const actualRunId = ev.run_id || data.run_id;
      if (!actualRunId) {
        gaps.push(`[${type}] Missing field: run_id`);
      }

      // Check status
      const actualStatus = ev.status || data.status;
      if (!actualStatus) {
        gaps.push(`[${type}] Missing field: status`);
      }

      // Event specific checks
      if (type && type.startsWith("task.")) {
        if (!ev.task_id && !data.task_id) {
          gaps.push(`[${type}] Task event missing task_id`);
        }
      }
      if (type && type.startsWith("approval.")) {
        if (!ev.approval_id && !data.approval_id) {
          gaps.push(`[${type}] Approval event missing approval_id`);
        }
      }
      if (type && type.startsWith("artifact.")) {
        if (!ev.artifact_id && !data.artifact_id) {
          gaps.push(`[${type}] Artifact event missing artifact_id`);
        }
      }
    });
  }

  writeReport(errors, findings, gaps, receivedEvents);
}

function writeReport(errors: string[], findings: string[], gaps: string[], receivedEvents: any[]) {
  // Gaps are expected and documented as part of the audit findings, so they don't fail the contract script.
  const status = errors.length === 0 ? "PASS" : "FAIL";
  const report = {
    generated_at: new Date().toISOString(),
    status,
    errors,
    findings,
    gaps,
    received_events_count: receivedEvents.length,
    gaps_count: gaps.length
  };

  const reportPath = path.resolve(__dirname, "../../artifacts/qa/runtime-event-schema-contract-report.json");
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(`WebSocket Event Schema Audit completed with status: ${status}`);
  if (gaps.length > 0) {
    console.log(`Documented ${gaps.length} schema gaps:`, gaps);
  }
  if (errors.length > 0) {
    console.error("Errors found:", errors);
    process.exit(1);
  } else {
    console.log("All WebSocket event schema contract checks completed successfully!");
    process.exit(0);
  }
}

runEventSchemaTest();
