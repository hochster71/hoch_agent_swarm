import type { Runbook } from "./runbookTypes";

export function simulateRunbook(runbook: Runbook): {
  executable: boolean;
  required_approvals: string[];
  predicted_impact: string[];
  blockers: string[];
} {
  const blockers: string[] = [];
  const requiredApprovals = runbook.steps
    .filter((step) => step.requires_approval)
    .map((step) => step.step_id);

  if (runbook.status !== "approved") {
    blockers.push("Runbook must be approved before execution.");
  }
  if (runbook.risk === "critical") {
    blockers.push("Critical runbook requires dual approval.");
  }

  return {
    executable: blockers.length === 0,
    required_approvals: requiredApprovals,
    predicted_impact: [
      "Expected to reduce incident severity if success conditions pass.",
      "Rollback available for reversible command steps.",
    ],
    blockers,
  };
}
