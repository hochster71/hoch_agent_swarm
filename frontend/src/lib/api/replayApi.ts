export async function fetchReplaySessions(): Promise<any[]> {
  const response = await fetch("/api/replay/sessions");
  if (!response.ok) {
    throw new Error("Failed to fetch replay sessions from server");
  }
  return response.json();
}

export async function fetchReplayEvents(correlationId: string): Promise<any[]> {
  const response = await fetch(`/api/replay/events/${correlationId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch replay events from server");
  }
  return response.json();
}
