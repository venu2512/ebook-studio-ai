import type { ApiErrorBody, ErrorDetail } from "@ebook/shared";

/** Error thrown for any non-2xx API response. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, detail: ErrorDetail) {
    super(detail.message);
    this.name = "ApiError";
    this.status = status;
    this.code = detail.code;
    this.details = detail.details ?? {};
  }

  /** Field-level messages from a FastAPI validation error, keyed by field. */
  get fieldErrors(): Record<string, string> {
    const errors = this.details?.errors;
    if (!Array.isArray(errors)) return {};
    const out: Record<string, string> = {};
    for (const raw of errors as Array<{ loc?: unknown[]; msg?: string }>) {
      const loc = raw.loc ?? [];
      // Drop the leading "body" segment FastAPI adds.
      const path = loc.filter((p) => p !== "body").join(".");
      if (path) out[path] = raw.msg ?? "Invalid value";
    }
    return out;
  }
}

const FALLBACK: ErrorDetail = {
  code: "network_error",
  message: "Could not reach the server. Check your connection and try again.",
  details: {},
};

/**
 * Base URL of the API.
 *
 * Client-side we use NEXT_PUBLIC_API_BASE_URL. Server-side (RSC / route
 * handlers) we prefer INTERNAL_API_BASE_URL so Docker Compose can talk to the
 * `api` service directly.
 */
export function apiBaseUrl(): string {
  if (typeof window === "undefined") {
    const internal = process.env.INTERNAL_API_BASE_URL;
    if (internal) return internal.replace(/\/$/, "");
  }
  const publicUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return publicUrl.replace(/\/$/, "");
}

const ACCESS_TOKEN_KEY = "ebook.access_token";
const REFRESH_TOKEN_KEY = "ebook.refresh_token";

export const tokenStore = {
  access(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  refresh(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  set(access: string, refresh?: string | null): void {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
    if (refresh) window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear(): void {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip attaching the Authorization header (used by auth endpoints). */
  anonymous?: boolean;
  /** Do not attempt a token refresh on 401. */
  noRetry?: boolean;
}

let refreshPromise: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const refresh = tokenStore.refresh();
  try {
    const res = await fetch(`${apiBaseUrl()}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(refresh ? { refresh_token: refresh } : {}),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      access_token: string;
      refresh_token?: string | null;
    };
    tokenStore.set(data.access_token, data.refresh_token ?? refresh);
    return data.access_token;
  } catch {
    return null;
  }
}

/**
 * Core fetch wrapper: JSON in/out, bearer auth, one automatic refresh retry,
 * and a consistent `ApiError` for any failure.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, anonymous, noRetry, headers, ...rest } = options;
  const url = path.startsWith("http") ? path : `${apiBaseUrl()}${path}`;

  const finalHeaders = new Headers(headers);
  if (body !== undefined && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (!anonymous) {
    const token = tokenStore.access();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
    const csrf = readCsrfCookie();
    if (csrf) finalHeaders.set("X-CSRF-Token", csrf);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...rest,
      headers: finalHeaders,
      credentials: "include",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, FALLBACK);
  }

  if (response.status === 401 && !anonymous && !noRetry && tokenStore.refresh() !== null) {
    refreshPromise ??= performRefresh().finally(() => {
      refreshPromise = null;
    });
    const newToken = await refreshPromise;
    if (newToken) {
      return apiFetch<T>(path, { ...options, noRetry: true });
    }
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload = text ? (JSON.parse(text) as unknown) : null;

  if (!response.ok) {
    const detail = (payload as ApiErrorBody | null)?.error;
    throw new ApiError(
      response.status,
      detail ?? {
        code: `http_${response.status}`,
        message: response.statusText || "Request failed.",
        details: {},
      },
    );
  }

  return payload as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => apiFetch<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "POST", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { ...options, method: "DELETE", body }),
};
