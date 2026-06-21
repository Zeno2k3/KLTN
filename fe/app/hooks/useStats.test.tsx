import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { StatRange, StatsDTO } from "@/app/types/admin";

// Mock lớp gọi API (hoisted để dùng trong factory vi.mock).
const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }));

vi.mock("@/app/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  statsApi: { get: getMock },
}));

import { useStats } from "./useStats";

function dto(over: Partial<StatsDTO> = {}): StatsDTO {
  return {
    range: "30d",
    active_parents: { value: 2, delta_pct: 100 },
    conversations: { value: 4, delta_pct: 300 },
    answered_questions: { value: 2, delta_pct: null },
    total_documents: 3,
    chart: [{ label: "01/06", count: 1 }],
    topic: { label: "Tư vấn tuyển sinh tiểu học", count: 4 },
    ...over,
  };
}

afterEach(() => {
  cleanup();
  getMock.mockReset();
});

describe("useStats", () => {
  it("tải số liệu khi mount theo range", async () => {
    getMock.mockResolvedValue(dto());
    const { result } = renderHook(() => useStats("30d"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getMock).toHaveBeenCalledWith("30d");
    expect(result.current.stats?.conversations.value).toBe(4);
    expect(result.current.error).toBeNull();
  });

  it("fetch lại khi range đổi", async () => {
    getMock.mockResolvedValue(dto());
    const { result, rerender } = renderHook(({ r }: { r: StatRange }) => useStats(r), {
      initialProps: { r: "30d" },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));

    getMock.mockResolvedValue(dto({ range: "7d", conversations: { value: 9, delta_pct: 0 } }));
    rerender({ r: "7d" });
    await waitFor(() => expect(result.current.stats?.range).toBe("7d"));
    expect(getMock).toHaveBeenCalledWith("7d");
    expect(result.current.stats?.conversations.value).toBe(9);
  });

  it("lỗi API → set error, không có stats", async () => {
    getMock.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useStats("24h"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeTruthy();
    expect(result.current.stats).toBeNull();
  });
});
