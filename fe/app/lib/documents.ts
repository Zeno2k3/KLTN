/** Chuyển DTO tài liệu từ backend sang dạng hiển thị `Doc` (định dạng dung lượng + ngày). */

import type { Doc, DocumentDTO } from "@/app/types/admin";

/** Dung lượng dạng "1,8 MB" / "920 KB" (giống mock cũ); thiếu kích thước → "—". */
export function formatSize(bytes: number | null): string {
  if (!bytes || bytes <= 0) return "—";
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) return mb.toFixed(1).replace(".", ",") + " MB";
  return Math.max(1, Math.round(bytes / 1024)) + " KB";
}

/** ISO → "DD/MM/YYYY"; chuỗi không hợp lệ → "". */
export function formatDateDMY(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return (
    String(d.getDate()).padStart(2, "0") +
    "/" +
    String(d.getMonth() + 1).padStart(2, "0") +
    "/" +
    d.getFullYear()
  );
}

export function docFromDTO(dto: DocumentDTO): Doc {
  const parts = [formatSize(dto.file_size)];
  const date = formatDateDMY(dto.created_at);
  if (date) parts.push("thêm " + date);
  return {
    id: dto.id,
    name: dto.filename,
    meta: parts.join(" · "),
    status: dto.status,
    error: dto.error_message ?? undefined,
  };
}
