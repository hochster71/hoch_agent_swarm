import { evaluateFreshness } from "../../frontend/src/lib/realtime/freshness";

function runTest(name: string, assertion: () => void) {
  try {
    assertion();
    console.log(` [PASS] Test: ${name}`);
  } catch (err: any) {
    console.error(` [FAIL] Test: ${name} - ${err.message}`);
    process.exit(1);
  }
}

function main() {
  console.log("==================================================");
  console.log("RUNNING STALE-GREEN REGRESSION TESTS");
  console.log("==================================================");

  runTest("never treats stale telemetry as live", () => {
    const result = evaluateFreshness({
      source: "live",
      received_at: new Date(Date.now() - 45000).toISOString(),
      ttl_ms: 10000
    });
    if (result !== "expired") {
      throw new Error(`Expected result to be 'expired', got '${result}'`);
    }
  });

  runTest("never treats simulation as live", () => {
    const result = evaluateFreshness({
      source: "simulation",
      received_at: new Date().toISOString(),
      ttl_ms: 10000
    });
    if (result !== "stale") {
      throw new Error(`Expected result to be 'stale', got '${result}'`);
    }
  });
  
  runTest("never treats manual as live", () => {
    const result = evaluateFreshness({
      source: "manual",
      received_at: new Date().toISOString(),
      ttl_ms: 10000
    });
    if (result !== "stale") {
      throw new Error(`Expected result to be 'stale', got '${result}'`);
    }
  });

  runTest("never treats unknown as live", () => {
    const result = evaluateFreshness({
      source: "unknown",
      received_at: new Date().toISOString(),
      ttl_ms: 10000
    });
    if (result !== "error") {
      throw new Error(`Expected result to be 'error', got '${result}'`);
    }
  });

  console.log("==================================================");
}

main();
