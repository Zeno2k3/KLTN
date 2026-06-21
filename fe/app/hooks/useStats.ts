"use client";

import { useEffect, useState } from "react";
import type { StatRange, StatsDTO } from "@/app/types/admin";
import { ApiError, statsApi } from "@/app/lib/api";

/** Tải số liệu thống kê admin (API thật) theo mốc thời gian; tự fetch lại khi `range` đổi. */
export function useStats(range: StatRange) {
  const [stats, setStats] = useState<StatsDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const data = await statsApi.get(range);
        if (active) {
          setStats(data);
          setError(null);
        }
      } catch (e) {
        if (active) {
          setError(
            e instanceof ApiError ? e.message : "Không tải được số liệu thống kê.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [range]);

  return { stats, loading, error };
}
