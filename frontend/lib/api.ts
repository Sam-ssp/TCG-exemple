export class ApiError extends Error {}

export const navigation = {
  toLogin() {
    // Plain module, no router here; a full load also clears client state after a lost session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/connexion/");
  },
};

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const hasBody = options.body !== undefined;
  const response = await fetch(path, {
    method: options.method ?? "GET",
    credentials: "same-origin",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    body: hasBody ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (response.ok) return data as T;
  const detail = typeof data.detail === "string" ? data.detail : "Requête invalide";
  if (response.status === 401 && path !== "/api/connexion") navigation.toLogin();
  throw new ApiError(detail);
}

export const cardPath = (id: string) => `/api/cartes/${encodeURIComponent(id)}`;
