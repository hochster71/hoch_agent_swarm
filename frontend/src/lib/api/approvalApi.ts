import type { ApprovalRequest } from "@/lib/collab/collaborationTypes";

export async function fetchApprovals(): Promise<ApprovalRequest[]> {
  const response = await fetch("/api/approval/requests");
  if (!response.ok) {
    throw new Error("Failed to fetch approvals from server");
  }
  return response.json();
}

export async function createApproval(request: any): Promise<ApprovalRequest> {
  const response = await fetch("/api/approval/requests", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(request)
  });
  if (!response.ok) {
    throw new Error("Failed to create approval request on server");
  }
  return response.json();
}

export async function submitDecision(
  approvalId: string,
  decision: ApprovalRequest["decisions"][number]
): Promise<ApprovalRequest> {
  const response = await fetch(`/api/approval/requests/${approvalId}/decisions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(decision)
  });
  if (!response.ok) {
    throw new Error("Failed to submit decision to server");
  }
  return response.json();
}
