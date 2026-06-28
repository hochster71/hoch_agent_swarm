import type { PolicyEvaluationInput, PolicyEvaluationResult } from "@/lib/policy/policyTypes";

export async function evaluatePolicy(input: PolicyEvaluationInput): Promise<PolicyEvaluationResult> {
  const response = await fetch("/api/policy/evaluate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(input)
  });
  if (!response.ok) {
    throw new Error("Failed to evaluate policy on server");
  }
  return response.json();
}

export async function fetchZtaPosture(): Promise<any> {
  const response = await fetch("/api/policy/posture");
  if (!response.ok) {
    throw new Error("Failed to fetch ZTA posture from server");
  }
  return response.json();
}
