import type { IconName } from "@/app/components/ui/Icon";

export type Status = "ready" | "processing";

export type Doc = { id: number; name: string; meta: string; status: Status };

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
