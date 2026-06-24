export async function fetchInsights(): Promise<any[]> {
  const response = await fetch("/api/intel/insights");
  if (!response.ok) {
    throw new Error("Failed to fetch insights from server");
  }
  return response.json();
}

export async function sendInsightFeedback(insightId: string, feedback: any): Promise<any> {
  const response = await fetch(`/api/intel/insights/${insightId}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(feedback)
  });
  if (!response.ok) {
    throw new Error("Failed to send insight feedback to server");
  }
  return response.json();
}
