function deterministicStringify(obj: any): string {
  if (obj === null) return "null";
  if (typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) {
    return "[" + obj.map(deterministicStringify).join(",") + "]";
  }
  const sortedKeys = Object.keys(obj).sort();
  const pairs = sortedKeys.map((key) => {
    return JSON.stringify(key) + ":" + deterministicStringify(obj[key]);
  });
  return "{" + pairs.join(",") + "}";
}

export async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  return hashHex;
}

export async function calculateBlockHash(
  index: number,
  timestamp: string,
  eventId: string,
  eventData: any,
  previousHash: string
): Promise<string> {
  const eventString = typeof eventData === "string" ? eventData : deterministicStringify(eventData);
  const dataToHash = `${index}|${timestamp}|${eventId}|${eventString}|${previousHash}`;
  return sha256(dataToHash);
}
