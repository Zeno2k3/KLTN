import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { askMock, listMock, getMock, renameMock, deleteMock } = vi.hoisted(() => ({
  askMock: vi.fn(),
  listMock: vi.fn(),
  getMock: vi.fn(),
  renameMock: vi.fn(),
  deleteMock: vi.fn(),
}));

vi.mock("@/app/lib/api", () => {
  class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
    }
  }
  return {
    ApiError,
    chatApi: {
      ask: askMock,
      listConversations: listMock,
      getMessages: getMock,
      renameConversation: renameMock,
      deleteConversation: deleteMock,
    },
  };
});

import { ApiError } from "@/app/lib/api";
import { useChat } from "@/app/hooks/useChat";

beforeEach(() => {
  listMock.mockResolvedValue([]);
  getMock.mockResolvedValue({ id: 1, title: "x", messages: [] });
  renameMock.mockResolvedValue({
    id: 5,
    title: "Tên mới",
    updated_at: "2026-06-21T08:00:00.000Z",
    last_message: null,
  });
  deleteMock.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("useChat — gọi backend RAG thật", () => {
  it("send: thêm tin user + bot (kèm nguồn), đặt serverId, lần sau truyền lại id", async () => {
    askMock.mockResolvedValue({
      conversation_id: 7,
      answer: "Trường THCS Lê Hồng Phong [1].",
      sources: [
        {
          index: 1,
          document_id: 11,
          filename: "quy-che.pdf",
          weaviate_uuid: "u",
          snippet: "s",
          score: 0.5,
        },
      ],
    });

    const { result } = renderHook(() => useChat("bạn"));
    await act(async () => {
      await result.current.send("Trường nào tuyển sinh lớp 6?");
    });

    expect(result.current.msgs.map((m) => m.from)).toEqual(["user", "bot"]);
    expect(result.current.msgs[1].text).toContain("Lê Hồng Phong");
    expect(result.current.msgs[1].sources?.[0].filename).toBe("quy-che.pdf");
    expect(askMock).toHaveBeenNthCalledWith(1, "Trường nào tuyển sinh lớp 6?", null);

    await act(async () => {
      await result.current.send("Còn lớp 1 thì sao?");
    });
    expect(askMock).toHaveBeenNthCalledWith(2, "Còn lớp 1 thì sao?", 7);
    expect(result.current.typing).toBe(false);
  });

  it("send lỗi 401 → set error, hết typing, giữ lại tin user", async () => {
    askMock.mockRejectedValue(new ApiError("unauth", 401));

    const { result } = renderHook(() => useChat("bạn"));
    await act(async () => {
      await result.current.send("Hỏi gì đó?");
    });

    expect(result.current.error).toContain("đăng nhập");
    expect(result.current.typing).toBe(false);
    expect(result.current.msgs[0].from).toBe("user");
  });

  it("openConvo: nạp tin nhắn lịch sử từ server (lazy)", async () => {
    listMock.mockResolvedValue([
      {
        id: 5,
        title: "Hội thoại cũ",
        updated_at: "2026-06-21T08:00:00.000Z",
        last_message: "tin cuối",
      },
    ]);
    getMock.mockResolvedValue({
      id: 5,
      title: "Hội thoại cũ",
      messages: [
        {
          id: 1,
          sender_type: "user",
          content: "hỏi cũ",
          sources: [],
          created_at: "2026-06-21T08:00:00.000Z",
        },
        {
          id: 2,
          sender_type: "assistant",
          content: "đáp cũ",
          sources: [],
          created_at: "2026-06-21T08:01:00.000Z",
        },
      ],
    });

    const { result } = renderHook(() => useChat("bạn"));
    await waitFor(() =>
      expect(result.current.convos.some((c) => c.id === "5")).toBe(true),
    );

    await act(async () => {
      await result.current.openConvo("5");
    });

    expect(result.current.activeId).toBe("5");
    expect(result.current.msgs.map((m) => m.from)).toEqual(["user", "bot"]);
    expect(result.current.msgs[1].text).toBe("đáp cũ");
    expect(getMock).toHaveBeenCalledWith(5);
  });
});

describe("useChat — đổi tên / xóa hội thoại", () => {
  function seedConvo() {
    listMock.mockResolvedValue([
      { id: 5, title: "Tên cũ", updated_at: "2026-06-21T08:00:00.000Z", last_message: "x" },
    ]);
  }

  it("renameConvo: cập nhật title trong state + gọi API với serverId", async () => {
    seedConvo();
    const { result } = renderHook(() => useChat("bạn"));
    await waitFor(() =>
      expect(result.current.convos.some((c) => c.id === "5")).toBe(true),
    );

    await act(async () => {
      await result.current.renameConvo("5", "Tên mới");
    });

    expect(renameMock).toHaveBeenCalledWith(5, "Tên mới");
    expect(result.current.convos.find((c) => c.id === "5")?.title).toBe("Tên mới");
  });

  it("deleteConvo (không phải cuộc đang mở): gọi API + bỏ khỏi danh sách, giữ active", async () => {
    seedConvo();
    const { result } = renderHook(() => useChat("bạn"));
    await waitFor(() =>
      expect(result.current.convos.some((c) => c.id === "5")).toBe(true),
    );
    const activeBefore = result.current.activeId;

    await act(async () => {
      await result.current.deleteConvo("5");
    });

    expect(deleteMock).toHaveBeenCalledWith(5);
    expect(result.current.convos.some((c) => c.id === "5")).toBe(false);
    expect(result.current.activeId).toBe(activeBefore);
  });

  it("deleteConvo (cuộc đang mở): xóa rồi mở cuộc trò chuyện mới trống", async () => {
    seedConvo();
    const { result } = renderHook(() => useChat("bạn"));
    await waitFor(() =>
      expect(result.current.convos.some((c) => c.id === "5")).toBe(true),
    );

    await act(async () => {
      await result.current.openConvo("5");
    });
    expect(result.current.activeId).toBe("5");

    await act(async () => {
      await result.current.deleteConvo("5");
    });

    expect(deleteMock).toHaveBeenCalledWith(5);
    expect(result.current.convos.some((c) => c.id === "5")).toBe(false);
    expect(result.current.activeId.startsWith("new-")).toBe(true);
    expect(result.current.msgs).toEqual([]);
  });
});
