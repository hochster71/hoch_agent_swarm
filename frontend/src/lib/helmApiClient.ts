export interface ApiResponse<T> {
  data: T | null;
  status: "OK" | "UNKNOWN_ENDPOINT" | "FORBIDDEN" | "AUTH_REQUIRED" | "OFFLINE" | "ERROR";
  statusCode: number | null;
  errorDetail: string | null;
}

// Track endpoints that should not be polled anymore (404/403)
const blacklistedEndpoints = new Set<string>();

// Track endpoints that returned 401 so we stop hammering them without auth.
// Unlike permanent blacklist, these clear when clearAuthRequiredEndpoints() is called
// (e.g. after CyberGov login).
const authRequiredEndpoints = new Set<string>();

export function clearAuthRequiredEndpoints(): void {
  authRequiredEndpoints.clear();
}

export function isAuthRequiredEndpoint(url: string): boolean {
  const base = url.split("?")[0];
  return authRequiredEndpoints.has(url) || authRequiredEndpoints.has(base);
}

export async function fetchJsonWithStatus<T>(
  url: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const baseUrl = url.split("?")[0];

  if (blacklistedEndpoints.has(url) || blacklistedEndpoints.has(baseUrl)) {
    return {
      data: null,
      status: url.includes("/offers") ? "FORBIDDEN" : "UNKNOWN_ENDPOINT",
      statusCode: url.includes("/offers") ? 403 : 404,
      errorDetail: `Requests to ${url} are suppressed (blacklisted due to prior failure).`,
    };
  }

  if (authRequiredEndpoints.has(url) || authRequiredEndpoints.has(baseUrl)) {
    return {
      data: null,
      status: "AUTH_REQUIRED",
      statusCode: 401,
      errorDetail:
        "Authentication required (CyberGov session cookie or Bearer token). Open Compliance login, then retry.",
    };
  }

  try {
    const res = await fetch(url, {
      ...options,
      // Include cookies so /api/v1/auth/login sessions work through the Vite proxy.
      credentials: options.credentials ?? "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (res.status === 404) {
      console.warn(`[HELM API] 404 Not Found: ${url}. Blacklisting endpoint.`);
      blacklistedEndpoints.add(url);
      blacklistedEndpoints.add(baseUrl);
      return { data: null, status: "UNKNOWN_ENDPOINT", statusCode: 404, errorDetail: "Not Found" };
    }

    if (res.status === 403) {
      console.warn(`[HELM API] 403 Forbidden: ${url}. Blacklisting endpoint.`);
      blacklistedEndpoints.add(url);
      blacklistedEndpoints.add(baseUrl);
      return { data: null, status: "FORBIDDEN", statusCode: 403, errorDetail: "Forbidden" };
    }

    if (res.status === 401) {
      // Suppress further unauthenticated polls for this path (stops console 401 spam).
      authRequiredEndpoints.add(url);
      authRequiredEndpoints.add(baseUrl);
      let detail =
        "Authentication credentials are required (CyberGov session cookie or Bearer token).";
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        /* ignore */
      }
      console.warn(`[HELM API] 401 Unauthorized: ${url}. Suppressing further polls until auth clears.`);
      return {
        data: null,
        status: "AUTH_REQUIRED",
        statusCode: 401,
        errorDetail: detail,
      };
    }

    if (!res.ok) {
      return {
        data: null,
        status: "ERROR",
        statusCode: res.status,
        errorDetail: `HTTP Error ${res.status}: ${res.statusText}`,
      };
    }

    const data = await res.json();
    return { data, status: "OK", statusCode: res.status, errorDetail: null };
  } catch (err: any) {
    console.error(`[HELM API] Network failure on ${url}:`, err);
    return {
      data: null,
      status: "OFFLINE",
      statusCode: null,
      errorDetail: err.message || String(err),
    };
  }
}
