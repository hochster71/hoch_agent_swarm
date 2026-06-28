import type { AdversarialScenario, ScenarioResult } from "./adversarialTypes";

const triggerAuditLog = (action: string, summary: string, targetId: string, severity: string, result: string) => {
  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      action: {
        type: action,
        summary: summary,
      },
      actor: {
        id: "red-team-bot",
        name: "Red-Team Automated Runner",
        type: "agent",
        role: "Adversarial Tester",
      },
      target: {
        type: "system",
        id: targetId,
        name: "Adversarial Drill Target",
      },
      result: result,
      severity: severity,
      provenance: {
        source: "synthetic",
        evidence_refs: [],
      },
      policy: {
        required: false,
        result: "not_required",
      },
    });
  }
};

export function runMockScenario(scenario: AdversarialScenario): AdversarialScenario {
  triggerAuditLog(
    "RED_TEAM_SCENARIO_STARTED",
    `Red-team drill simulation started: ${scenario.name}`,
    scenario.scenario_id,
    scenario.severity,
    "success"
  );

  // Determine failed assertions based on scenario kind
  let failedAssertions: string[] = [];
  let findings: string[] = [];
  let status: ScenarioResult = "passed";

  switch (scenario.kind) {
    case "prompt_injection":
      // Let's pass this one to simulate safety filter block
      failedAssertions = [];
      findings = [
        "Prompt injection patterns detected in input payload.",
        "System Policy intercept returned action COMMAND_BLOCKED.",
        "All guardrails held as expected.",
      ];
      status = "passed";
      break;

    case "policy_bypass":
      // Let's fail one of the assertions to demonstrate remediation triggers!
      failedAssertions = ["ast-policy-blocked"];
      findings = [
        "Simulated privileged execution command dispatched.",
        "ZTA policy engine allowed action due to simulated bypass fault.",
        "Critical safety assertion failed: Command bypass was successful.",
      ];
      status = "failed";
      break;

    case "telemetry_failure":
      failedAssertions = [];
      findings = [
        "WebSocket connection terminated manually.",
        "UI registered STALE warning status after 10s latency window.",
        "Audit log warnings recorded successfully.",
      ];
      status = "passed";
      break;

    case "ledger_tamper":
      failedAssertions = [];
      findings = [
        "Historic SQLite block hash modified dynamically.",
        "SHA-256 validation scan detected validation mismatch.",
        "Integrity locks verified as active.",
      ];
      status = "passed";
      break;

    case "approval_abuse":
      failedAssertions = ["ast-approval-blocked"];
      findings = [
        "Operator submitted execution request and granted self-approval.",
        "Authorization engine failed to catch Operator duplicate ID.",
        "Safety assertion failed: Dual authorization bypassed.",
      ];
      status = "failed";
      break;

    default:
      failedAssertions = [];
      findings = ["Simulation ran successfully. Guardrails held."];
      status = "passed";
  }

  const resultRecord = {
    status,
    started_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    findings,
    failed_assertions: failedAssertions,
    evidence_refs: [`scenario.${scenario.scenario_id}.run.latest`],
  };

  triggerAuditLog(
    "RED_TEAM_SCENARIO_COMPLETED",
    `Red-team drill simulation completed: ${scenario.name} - Status: ${status.toUpperCase()}`,
    scenario.scenario_id,
    status === "failed" ? "critical" : scenario.severity,
    status === "failed" ? "failed" : "success"
  );

  if (status === "failed") {
    failedAssertions.forEach((astId) => {
      triggerAuditLog(
        "SAFETY_ASSERTION_FAILED",
        `Safety assertion failed: ${astId} on drill ${scenario.name}`,
        scenario.scenario_id,
        "critical",
        "failed"
      );
    });
  }

  return {
    ...scenario,
    result: resultRecord,
  };
}
