/**
 * Lớp gọi backend (FastAPI). Mọi request gửi kèm cookie (credentials: "include")
 * để httpOnly cookie chứa token được đính tự động.
 *
 * Tự động refresh: khi gặp 401 (access token hết hạn), gọi /auth/refresh một lần
 * rồi thử lại request gốc.
 */

import type { LoginInput, RegisterInput, User } from "@/app/types/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API_URL}/api/v1`;

/** Những endpoint không tự refresh (tránh vòng lặp / hiểu nhầm 401 sai mật khẩu). */
const NO_REFRESH = new Set([
  "/auth/refresh",
  "/auth/login",
  "/auth/register",
  "/auth/google",
]);

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function rawFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
}

// Gộp nhiều request refresh đồng thời thành một.
let refreshing: Promise<boolean> | null = null;

function tryRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = rawFetch("/auth/refresh", { method: "POST" })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const res = await rawFetch(path, options);
  if (res.status === 401 && !NO_REFRESH.has(path)) {
    const ok = await tryRefresh();
    if (ok) return rawFetch(path, options);
  }
  return res;
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = "Có lỗi xảy ra, vui lòng thử lại.";
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // body không phải JSON — giữ thông báo mặc định
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const authApi = {
  register: (data: RegisterInput) =>
    apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }).then((r) => parse<User>(r)),

  login: (data: LoginInput) =>
    apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }).then((r) => parse<User>(r)),

  loginWithGoogle: (accessToken: string) =>
    apiFetch("/auth/google", {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
    }).then((r) => parse<User>(r)),

  logout: () =>
    apiFetch("/auth/logout", { method: "POST" }).then((r) => parse<{ detail: string }>(r)),

  me: () => apiFetch("/auth/me").then((r) => parse<User>(r)),
};
