/**
 * Frontend-safe pull-request governance policy (fail-closed).
 *
 * Server-only modules must not be imported into the browser bundle.
 * This module is the authoritative client-side policy evaluation for
 * Hochster PR automation UI.
 */

export type PullRequestCheckParams = {
  validationPassed: boolean;
  regressionRisk: string;
  humanApproved: boolean;
  secretsDetected: boolean;
};

export type PullRequestPolicyResult = {
  allowed: boolean;
  blockers: string[];
};

/**
 * Fail-closed: any unmet precondition blocks PR creation.
 * Does not invent success; defaults deny when inputs are incomplete.
 */
export function canCreatePullRequest(
  params: PullRequestCheckParams
): PullRequestPolicyResult {
  const blockers: string[] = [];

  if (!params || typeof params !== "object") {
    return { allowed: false, blockers: ["INVALID_POLICY_INPUT"] };
  }

  if (!params.validationPassed) {
    blockers.push("VALIDATION_TESTS_NOT_PASSED");
  }

  if (params.secretsDetected) {
    blockers.push("SECRETS_DETECTED_IN_CANDIDATE");
  }

  if (!params.humanApproved) {
    blockers.push("HUMAN_APPROVAL_REQUIRED");
  }

  const risk = (params.regressionRisk || "").toLowerCase();
  if (risk === "high" || risk === "critical") {
    blockers.push(`REGRESSION_RISK_${risk.toUpperCase()}`);
  }
  if (!risk) {
    blockers.push("REGRESSION_RISK_UNKNOWN");
  }

  return {
    allowed: blockers.length === 0,
    blockers,
  };
}
