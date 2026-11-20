// Talking to the Worker, and moving between pages without reloading
import type { MouseEvent } from "react";

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly data: Record<string, unknown>) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const data = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  if (!response.ok) {
    // our Worker says "error"; Better Auth says "message"
    throw new ApiError(String(data.error ?? data.message ?? `The server answered ${response.status}.`), response.status, data);
  }
  return data as T;
}

export const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: "POST", body: JSON.stringify(body) });

export function navigate(path: string) {
  if (path === window.location.pathname) return;
  window.history.pushState(null, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
  window.scrollTo(0, 0);
}

// For a link inside the app: a plain click moves without reloading; a click with a modifier opens a tab as usual
export const go = (path: string) => (event: MouseEvent) => {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  navigate(path);
};

export async function signOut() {
  await post("/api/auth/sign-out").catch(() => undefined);
  window.location.assign("/");
}
