import { HochsterSolveRequest, HochsterSolution, HochsterInstance, HochsterRequestStatus } from "./hochsterTypes";

const API_BASE = "/api/v1/hochster";

export async function submitSolveRequest(
  payload: Omit<HochsterSolveRequest, "request_id" | "requested_at" | "status">
): Promise<{ request_id: string; status: HochsterRequestStatus; assigned_instances: string[]; correlation_id: string }> {
  const response = await fetch(`${API_BASE}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Failed to submit solve request: ${response.statusText}`);
  }
  return response.json();
}

export async function getRequestStatus(
  requestId: string
): Promise<{ request_id: string; status: HochsterRequestStatus; progress_percent: number; active_instances: string[]; latest_trace_event?: string }> {
  const response = await fetch(`${API_BASE}/requests/${requestId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch request status: ${response.statusText}`);
  }
  return response.json();
}

export async function getSolution(
  solutionId: string
): Promise<{ request_id: string; solution: HochsterSolution }> {
  const response = await fetch(`${API_BASE}/solutions/${solutionId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch solution: ${response.statusText}`);
  }
  return response.json();
}

export async function cancelRequest(requestId: string): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/requests/${requestId}/cancel`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Failed to cancel request: ${response.statusText}`);
  }
  return response.json();
}

export async function getInstances(): Promise<HochsterInstance[]> {
  const response = await fetch("/api/v1/hochster/instances");
  if (!response.ok) {
    throw new Error(`Failed to fetch instances: ${response.statusText}`);
  }
  return response.json();
}
