import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Convo } from "@/app/types/chat";
import ConversationItem from "./ConversationItem";

afterEach(cleanup);

function makeConvo(overrides: Partial<Convo> = {}): Convo {
  return {
    id: "1",
    serverId: 1,
    title: "Tuyển sinh lớp 1",
    time: "09:24",
    tint: "var(--brand-subtle)",
    fg: "var(--brand-strong)",
    messages: [],
    loaded: false,
    ...overrides,
  };
}

describe("ConversationItem — menu 3 chấm", () => {
  it("bấm kebab mở menu Đổi tên / Xóa, KHÔNG kích hoạt mở hội thoại", () => {
    const onClick = vi.fn();
    render(
      <ConversationItem
        convo={makeConvo()}
        active={false}
        onClick={onClick}
        onRename={vi.fn()}
        onRequestDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("Tùy chọn cuộc trò chuyện"));
    expect(screen.getByText("Đổi tên")).toBeTruthy();
    expect(screen.getByText("Xóa cuộc trò chuyện")).toBeTruthy();
    expect(onClick).not.toHaveBeenCalled();
  });

  it("Xóa cuộc trò chuyện → gọi onRequestDelete với đúng convo", () => {
    const onRequestDelete = vi.fn();
    const convo = makeConvo();
    render(
      <ConversationItem
        convo={convo}
        active={false}
        onClick={vi.fn()}
        onRename={vi.fn()}
        onRequestDelete={onRequestDelete}
      />,
    );
    fireEvent.click(screen.getByLabelText("Tùy chọn cuộc trò chuyện"));
    fireEvent.click(screen.getByText("Xóa cuộc trò chuyện"));
    expect(onRequestDelete).toHaveBeenCalledWith(convo);
  });

  it("Đổi tên → hiện ô nhập, gõ tên mới + Enter → gọi onRename(id, tên mới)", () => {
    const onRename = vi.fn();
    render(
      <ConversationItem
        convo={makeConvo()}
        active={false}
        onClick={vi.fn()}
        onRename={onRename}
        onRequestDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("Tùy chọn cuộc trò chuyện"));
    fireEvent.click(screen.getByText("Đổi tên"));
    const input = screen.getByLabelText("Tên cuộc trò chuyện") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Tên đã đổi" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRename).toHaveBeenCalledTimes(1);
    expect(onRename).toHaveBeenCalledWith("1", "Tên đã đổi");
  });

  it("Đổi tên → Esc hủy, KHÔNG gọi onRename", () => {
    const onRename = vi.fn();
    render(
      <ConversationItem
        convo={makeConvo()}
        active={false}
        onClick={vi.fn()}
        onRename={onRename}
        onRequestDelete={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("Tùy chọn cuộc trò chuyện"));
    fireEvent.click(screen.getByText("Đổi tên"));
    const input = screen.getByLabelText("Tên cuộc trò chuyện") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Không lưu" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onRename).not.toHaveBeenCalled();
  });
});
