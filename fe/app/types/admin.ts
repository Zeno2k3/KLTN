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

/** Sắc thái badge delta: tăng (xanh) / giảm (đỏ) / trung tính (xám). */
export type DeltaTone = "up" | "down" | "neutral";

export type StatCardData = {
  label: string;
  value: string;
  delta: string;
  deltaTone?: DeltaTone;
  icon: IconName;
  tint: string;
  fg: string;
};

export type ChartBar = { label: string; value: string; h: string };

/** `pct` điều khiển bề rộng thanh; `value` (nếu có) là chữ hiển thị bên phải, mặc định = `pct`. */
export type TopicProgress = { label: string; pct: string; color: string; value?: string };

/** Mốc thời gian tổng hợp thống kê (khớp `StatRange` của backend). */
export type StatRange = "24h" | "7d" | "30d";

/** Một chỉ số đếm + % thay đổi so với kỳ trước (null nếu kỳ trước = 0). */
export type MetricDTO = { value: number; delta_pct: number | null };

export type ChartBucketDTO = { label: string; count: number };

export type TopicStatDTO = { label: string; count: number };

/** Dữ liệu thống kê admin trả về từ GET /admin/stats. */
export type StatsDTO = {
  range: StatRange;
  active_parents: MetricDTO;
  conversations: MetricDTO;
  answered_questions: MetricDTO;
  total_documents: number;
  chart: ChartBucketDTO[];
  topic: TopicStatDTO;
};
