import type { IconName } from "@/app/components/ui/Icon";

export type Status = "ready" | "processing" | "failed";

export type Doc = { id: number; name: string; meta: string; status: Status; error?: string };

/** Dữ liệu tài liệu trả về từ backend (GET/POST /admin/documents). */
export type DocumentDTO = {
  id: number;
  filename: string;
  file_size: number | null;
  status: Status;
  page_count: number | null;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
};

export type StatCardData = {
  label: string;
  value: string;
  delta: string;
  icon: IconName;
  tint: string;
  fg: string;
};

export type ChartBar = { label: string; value: string; h: string };

export type TopicProgress = { label: string; pct: string; color: string };
