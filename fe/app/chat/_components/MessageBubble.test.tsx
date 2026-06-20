import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Msg } from "@/app/types/chat";

vi.mock("@/app/components/common/LogoBadge", () => ({ default: () => null }));
vi.mock("@/app/components/ui/Avatar", () => ({ default: () => null }));

import MessageBubble from "./MessageBubble";

afterEach(cleanup);

describe("MessageBubble — chip nguồn", () => {
  it("tin bot có nguồn → hiện chip (gộp trùng document_id)", () => {
    const message: Msg = {
      from: "bot",
      text: "Đáp án.",
      time: "10:00",
      sources: [
        { index: 1, document_id: 1, filename: "a.pdf", snippet: "s1", score: 0.5 },
        { index: 2, document_id: 1, filename: "a.pdf", snippet: "s2", score: 0.4 },
        { index: 3, document_id: 2, filename: "b.pdf", snippet: "s3", score: 0.3 },
      ],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.getByText("Nguồn:")).toBeTruthy();
    expect(screen.getAllByText("a.pdf")).toHaveLength(1); // gộp trùng
    expect(screen.getByText("b.pdf")).toBeTruthy();
  });

  it("tin người dùng → KHÔNG hiện chip nguồn", () => {
    const message: Msg = {
      from: "user",
      text: "Câu hỏi.",
      time: "10:00",
      sources: [{ index: 1, document_id: 1, filename: "a.pdf", snippet: "s", score: 1 }],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.queryByText("Nguồn:")).toBeNull();
  });

  it("nguồn thiếu filename → nhãn 'Tài liệu #id'", () => {
    const message: Msg = {
      from: "bot",
      text: "Đáp.",
      time: "10:00",
      sources: [{ index: 1, document_id: 9, filename: null, snippet: null, score: null }],
    };
    render(<MessageBubble message={message} showAvatar />);
    expect(screen.getByText("Tài liệu #9")).toBeTruthy();
  });
});
