import type { AuditEvent } from "@/lib/audit/auditTypes";

export async function fetchEvents(): Promise<AuditEvent[]> {
  const response = await fetch("/api/audit/events");
  if (!response.ok) {
    throw new Error("Failed to fetch audit events from server");
  }
  return response.json();
}

export async function sendEvent(event: AuditEvent): Promise<AuditEvent> {
  const response = await fetch("/api/audit/events", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(event)
  });
  if (!response.ok) {
    throw new Error("Failed to post audit event to server");
  }
  return response.json();
}
