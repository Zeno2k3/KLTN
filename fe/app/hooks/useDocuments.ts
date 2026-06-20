"use client";

import { useCallback, useEffect, useState } from "react";
import type { Doc } from "@/app/types/admin";
import { ApiError, documentApi } from "@/app/lib/api";
import { docFromDTO } from "@/app/lib/documents";

const POLL_MS = 3000;

/** Quản lý kho tài liệu PDF (API thật): tải danh sách, upload, xoá, và poll
 * trạng thái khi còn tài liệu đang xử lý (ingest chạy nền ở backend). */
export function useDocuments() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const dtos = await documentApi.list();
      setDocs(dtos.map(docFromDTO));
      setError(null);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Không tải được danh sách tài liệu.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Tải danh sách lần đầu (setState nằm sau await → không phải cập nhật đồng bộ).
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const dtos = await documentApi.list();
        if (active) {
          setDocs(dtos.map(docFromDTO));
          setError(null);
        }
      } catch (e) {
        if (active) {
          setError(
            e instanceof ApiError ? e.message : "Không tải được danh sách tài liệu.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  // Còn tài liệu "processing" → poll định kỳ tới khi xong/hết.
  const hasProcessing = docs.some((d) => d.status === "processing");
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [hasProcessing, refresh]);

  const onPick = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (!files.length) return;
    setError(null);
    for (const file of files) {
      try {
        const dto = await documentApi.upload(file);
        setDocs((prev) => [docFromDTO(dto), ...prev]);
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : `Tải lên "${file.name}" thất bại.`,
        );
      }
    }
  }, []);

  // Optimistic bằng functional update; khi LỖI gọi refresh() để đồng bộ lại với server
  // thay vì khôi phục snapshot tuyệt đối (snapshot có thể đè mất poll/upload đồng thời).
  const deleteDoc = useCallback(
    async (id: number) => {
      setDocs((prev) => prev.filter((d) => d.id !== id)); // optimistic
      try {
        await documentApi.remove(id);
      } catch (err) {
        await refresh(); // đồng bộ lại từ server TRƯỚC (refresh tự xoá error)…
        setError(
          err instanceof ApiError ? err.message : "Không xoá được tài liệu.",
        ); // …rồi mới đặt thông báo lỗi để nó tồn tại
      }
    },
    [refresh],
  );

  const deleteAll = useCallback(async () => {
    setDocs([]); // optimistic: dọn sạch
    try {
      await documentApi.removeAll();
    } catch (err) {
      await refresh();
      setError(
        err instanceof ApiError ? err.message : "Không xoá được tất cả tài liệu.",
      );
    }
  }, [refresh]);

  // Xem/Tải PDF qua apiFetch (tự refresh khi access token hết hạn) → blob, không điều
  // hướng <a> thẳng tới BE (sẽ hiện JSON 401 nếu token ngắn hạn đã hết).
  const openDoc = useCallback(async (doc: Doc, download: boolean) => {
    // Mở tab ĐỒNG BỘ với cú click (tránh bị chặn popup), đổ nội dung sau khi tải xong.
    const win = download ? null : window.open("about:blank", "_blank");
    try {
      const blob = await documentApi.fetchFile(doc.id);
      const url = URL.createObjectURL(blob);
      if (download) {
        const a = document.createElement("a");
        a.href = url;
        a.download = doc.name;
        a.click();
      } else if (win) {
        win.location.href = url;
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      if (win) win.close();
      setError(
        err instanceof ApiError ? err.message : "Không mở được tài liệu.",
      );
    }
  }, []);

  return { docs, loading, error, onPick, deleteDoc, deleteAll, openDoc };
}
