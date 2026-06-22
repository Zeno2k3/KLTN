/**
 * Lớp gọi backend (FastAPI). Mọi request gửi kèm cookie (credentials: "include")
 * để httpOnly cookie chứa token được đính tự động.
 *
 * Tự động refresh: khi gặp 401 (access token hết hạn), gọi /auth/refresh một lần
 * rồi thử lại request gốc.
 */

import type { DocumentDTO, StatRange, StatsDTO } from "@/app/types/admin";
import type { LoginInput, RegisterInput, User } from "@/app/types/auth";
import type {
  AskResponseDTO,
  ConversationDetailDTO,
  ConversationSummaryDTO,
  DocumentDetailDTO,
} from "@/app/types/chat";

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
  // Với FormData (upload tệp) KHÔNG đặt Content-Type — trình duyệt tự thêm boundary.
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers: HeadersInit = isFormData
    ? { ...options.headers }
    : { "Content-Type": "application/json", ...options.headers };
  return fetch(`${BASE}${path}`, { ...options, credentials: "include", headers });
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

async function ensureOk(res: Response): Promise<Response> {
  if (res.ok) return res;
  let detail = "Có lỗi xảy ra, vui lòng thử lại.";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // body không phải JSON — giữ thông báo mặc định
  }
  throw new ApiError(detail, res.status);
}

async function parse<T>(res: Response): Promise<T> {
  await ensureOk(res);
  return res.json() as Promise<T>;
}

/** Cho response không có body (vd 204 No Content): ném ApiError nếu lỗi, ngược lại void. */
async function parseEmpty(res: Response): Promise<void> {
  await ensureOk(res);
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

export const documentApi = {
  list: () => apiFetch("/admin/documents").then((r) => parse<DocumentDTO[]>(r)),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiFetch("/admin/documents", { method: "POST", body: form }).then((r) =>
      parse<DocumentDTO>(r),
    );
  },

  remove: (id: number) =>
    apiFetch(`/admin/documents/${id}`, { method: "DELETE" }).then((r) => parseEmpty(r)),

  /** Đổi tên hiển thị tài liệu (DB-only) → trả về DTO đã cập nhật. */
  rename: (id: number, filename: string) =>
    apiFetch(`/admin/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ filename }),
    }).then((r) => parse<DocumentDTO>(r)),

  removeAll: () =>
    apiFetch("/admin/documents", { method: "DELETE" }).then((r) =>
      parse<{ deleted: number }>(r),
    ),

  /** Tải file PDF qua apiFetch (tự refresh khi 401) → Blob, để xem/tải an toàn cả khi
   * access token ngắn hạn đã hết (điều hướng <a> thẳng sẽ không tự refresh được). */
  fetchFile: async (id: number): Promise<Blob> => {
    const res = await apiFetch(`/admin/documents/${id}/file`);
    await ensureOk(res);
    return res.blob();
  },
};

export const statsApi = {
  /** Số liệu thống kê admin theo mốc thời gian (24h / 7d / 30d). */
  get: (range: StatRange) =>
    apiFetch(`/admin/stats?range=${range}`).then((r) => parse<StatsDTO>(r)),
};

export const chatApi = {
  /** Gửi câu hỏi → câu trả lời RAG + nguồn. `conversationId` null = tạo hội thoại mới. */
  ask: (question: string, conversationId: number | null = null) =>
    apiFetch("/chat/ask", {
      method: "POST",
      body: JSON.stringify({ question, conversation_id: conversationId }),
    }).then((r) => parse<AskResponseDTO>(r)),

  /** Danh sách hội thoại của người dùng (sidebar), mới nhất trước. */
  listConversations: () =>
    apiFetch("/chat/conversations").then((r) => parse<ConversationSummaryDTO[]>(r)),

  /** Toàn bộ tin nhắn của một hội thoại (mở từ sidebar). */
  getMessages: (id: number) =>
    apiFetch(`/chat/conversations/${id}/messages`).then((r) =>
      parse<ConversationDetailDTO>(r),
    ),

  /** Đổi tên một hội thoại → trả về bản tóm tắt đã cập nhật. */
  renameConversation: (id: number, title: string) =>
    apiFetch(`/chat/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }).then((r) => parse<ConversationSummaryDTO>(r)),

  /** Xóa một hội thoại (204 No Content). */
  deleteConversation: (id: number) =>
    apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }).then((r) =>
      parseEmpty(r),
    ),

  /** Tài liệu + toàn bộ đoạn text (mở bảng trích dẫn khi bấm chip nguồn). */
  getDocument: (id: number) =>
    apiFetch(`/chat/documents/${id}`).then((r) => parse<DocumentDetailDTO>(r)),
};
