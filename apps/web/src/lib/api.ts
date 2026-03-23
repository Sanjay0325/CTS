const DEFAULT_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Base API URL - proxy in browser unless NEXT_PUBLIC_USE_DIRECT_API=true */
export function getApiUrl(): string {
  if (typeof window === "undefined") return DEFAULT_API_URL;
  return process.env.NEXT_PUBLIC_USE_DIRECT_API === "true" ? DEFAULT_API_URL : "/api/proxy";
}

export async function getAuthHeaders(): Promise<HeadersInit> {
  const { createClient } = await import("@/lib/supabase");
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (session?.access_token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${session.access_token}`;
  }
  return headers;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders();
  const url = `${getApiUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...options.headers },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function apiDelete(path: string): Promise<void> {
  await apiFetch(path, { method: "DELETE" });
}
