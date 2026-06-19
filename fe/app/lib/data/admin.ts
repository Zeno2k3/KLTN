import type { ChartBar, Doc, TopicProgress } from "@/app/types/admin";

/** Dữ liệu tĩnh cho trang quản trị. */

const CHART_RAW = [
  { label: "Tuần 1", v: 820 },
  { label: "Tuần 2", v: 1040 },
  { label: "Tuần 3", v: 960 },
  { label: "Tuần 4", v: 1380 },
  { label: "Tuần 5", v: 1610 },
  { label: "Tuần 6", v: 1920 },
];
const CHART_MAX = Math.max(...CHART_RAW.map((r) => r.v));

export const CHART: ChartBar[] = CHART_RAW.map((r) => ({
  label: r.label,
  value: (r.v / 1000).toFixed(1).replace(".", ",") + "K",
  h: Math.round((r.v / CHART_MAX) * 100) + "%",
}));

export const TOPICS: TopicProgress[] = [
  { label: "Điều kiện nhập học", pct: "82%", color: "var(--brand)" },
  { label: "Hồ sơ & giấy tờ", pct: "64%", color: "var(--sky-500)" },
  { label: "Học phí", pct: "53%", color: "var(--sun-400)" },
  { label: "Lịch tham quan", pct: "37%", color: "var(--teal-400)" },
];

export const SEED_DOCS: Doc[] = [
  { id: 1, name: "Quy chế tuyển sinh lớp 1 năm 2026.pdf", meta: "1,8 MB · thêm 12/06/2026", status: "ready" },
  { id: 2, name: "Hướng dẫn chuẩn bị hồ sơ nhập học.pdf", meta: "920 KB · thêm 12/06/2026", status: "ready" },
  { id: 3, name: "Biểu phí các trường tiểu học Q.7.pdf", meta: "2,3 MB · thêm 10/06/2026", status: "ready" },
  { id: 4, name: "Danh sách trường & chỉ tiêu 2026.pdf", meta: "1,1 MB · thêm 08/06/2026", status: "processing" },
];
