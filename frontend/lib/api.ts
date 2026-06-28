const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("kizuna_access_token");
}

export function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem("kizuna_access_token", accessToken);
  localStorage.setItem("kizuna_refresh_token", refreshToken);
}

export function clearTokens() {
  localStorage.removeItem("kizuna_access_token");
  localStorage.removeItem("kizuna_refresh_token");
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    },
    cache: "no-store"
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error: ${res.status}`);
  }
  return res.json();
}
