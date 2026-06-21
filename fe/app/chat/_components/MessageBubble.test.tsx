import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Msg, Source } from "@/app/types/chat";

vi.mock("@/app/components/common/LogoBadge", () => ({ default: () => null }));
vi.mock("@/app/components/ui/Avatar", () => ({ default: () => null }));

const { getDocument } = vi.hoisted(() => ({ getDocument: vi.fn() }));
vi.mock("@/app/lib/api", () => ({ chatApi: { getDocument } }));

import MessageBubble from "./MessageBubble";

afterEach(() => {
  cleanup();
  getDocument.mockReset();
});

/** Source đầy đủ field (gọn cho test). */
function src(p: Partial<Source>): Source {
  return {
    index: null,
    document_id: null,
    filename: null,
    weaviate_uuid: null,
    snippet: null,
    score: null,
    ...p,
  };
}

describe("MessageBubble — chip nguồn", () => {
  it("tin bot có nguồn → gộp theo document_id (1 chip mỗi tài liệu)", () => {
    const message: Msg = {
      from: "bot",
      text: "Đáp án.",
      time: "10:00",
      sources: [
        src({ index: 1, document_id: 1, filename: "a.pdf", weaviate_uuid: "u1", snippet: "s1" }),
        src({ index: 2, document_id: 1, filename: "a.pdf", weaviate_uuid: "u2", snippet: "s2" }),
        src({ index: 3, document_id: 2, filename: "b.pdf", weaviate_uuid: "u3", snippet: "s3" }),
      ],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.getByText("Nguồn:")).toBeTruthy();
    expect(screen.getAllByText("a.pdf")).toHaveLength(1); // gộp trùng
    expect(screen.getByText("b.pdf")).toBeTruthy();
    // chip có tài liệu → là button (bấm được).
    expect(screen.getByRole("button", { name: /a\.pdf/ })).toBeTruthy();
  });

  it("tin người dùng → KHÔNG hiện chip nguồn", () => {
    const message: Msg = {
      from: "user",
      text: "Câu hỏi.",
      time: "10:00",
      sources: [src({ index: 1, document_id: 1, filename: "a.pdf", weaviate_uuid: "u" })],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.queryByText("Nguồn:")).toBeNull();
  });

  it("nguồn thiếu filename → nhãn 'Tài liệu #id'", () => {
    const message: Msg = {
      from: "bot",
      text: "Đáp.",
      time: "10:00",
      sources: [src({ index: 1, document_id: 9 })],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.getByText("Tài liệu #9")).toBeTruthy();
  });

  it("nguồn không có document_id → chip không bấm được (không phải button)", () => {
    const message: Msg = {
      from: "bot",
      text: "Đáp.",
      time: "10:00",
      sources: [src({ index: 1, document_id: null, filename: "x.pdf", snippet: "trích" })],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.getByText("x.pdf")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /x\.pdf/ })).toBeNull();
  });

  it("bấm chip → mở bảng tài liệu (gọi getDocument + hiện nội dung)", async () => {
    getDocument.mockResolvedValue({
      id: 1,
      filename: "a.pdf",
      page_count: 3,
      chunk_count: 1,
      chunks: [{ chunk_index: 0, content: "Nội dung đoạn trích", weaviate_uuid: "u1" }],
    });
    const message: Msg = {
      from: "bot",
      text: "Đáp.",
      time: "10:00",
      sources: [src({ index: 1, document_id: 1, filename: "a.pdf", weaviate_uuid: "u1", snippet: "s" })],
    };
    render(<MessageBubble message={message} showAvatar />);

    fireEvent.click(screen.getByRole("button", { name: /a\.pdf/ }));
    await waitFor(() => expect(getDocument).toHaveBeenCalledWith(1));
    expect(await screen.findByText("Nội dung đoạn trích")).toBeTruthy();
    expect(screen.getByText("Nguồn tham khảo")).toBeTruthy(); // eyebrow drawer
  });
});
