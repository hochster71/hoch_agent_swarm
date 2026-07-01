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
      // Telemetry snapshots are filtered separately (contain metrics, CPU, RAM, active_assets, etc., but no type/event_type)
      if (!ev.type && !ev.event_type) {
        findings.push("Skipping raw cluster status metrics telemetry packet");
        return;
      }

      const type = ev.event_type || ev.type;
      findings.push(`Evaluating event type: ${type}`);

      // Assert runtime events use normalized envelope root fields
      const requiredFields = ["event_type", "event_id", "run_id", "status", "timestamp", "trace_id"];
      requiredFields.forEach((field) => {
        if (ev[field] === undefined || ev[field] === null || ev[field] === "") {
          errors.push(`[${type}] Missing required normalized root field: ${field}`);
        }
      });

      // Event specific root checks
      if (type && type.startsWith("task.")) {
        if (!ev.task_id) {
          errors.push(`[${type}] Task event missing root field: task_id`);
        }
      }
      if (type && type.startsWith("approval.")) {
        if (!ev.approval_id) {
          errors.push(`[${type}] Approval event missing root field: approval_id`);
        }
      }
      if (type && type.startsWith("artifact.")) {
        if (!ev.artifact_id) {
          errors.push(`[${type}] Artifact event missing root field: artifact_id`);
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
