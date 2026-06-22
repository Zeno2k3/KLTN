import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Doc } from "@/app/types/admin";
import DocRow from "./DocRow";

const baseDoc: Doc = {
  id: 1,
  name: "cu.pdf",
  meta: "1 KB · thêm 20/06/2026",
  status: "ready",
};

afterEach(() => cleanup());

function setup(over: Partial<Doc> = {}) {
  const onDelete = vi.fn();
  const onOpen = vi.fn();
  const onRename = vi.fn();
  render(
    <DocRow
      doc={{ ...baseDoc, ...over }}
      onDelete={onDelete}
      onOpen={onOpen}
      onRename={onRename}
    />,
  );
  return { onDelete, onOpen, onRename };
}

describe("DocRow", () => {
  it("ẩn nút action khi đang sửa tên (tránh race blur-lưu khi bấm Xoá)", () => {
    setup();
    expect(screen.getByRole("button", { name: "Xoá" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Đổi tên" }));

    expect(screen.getByRole("textbox", { name: "Tên tài liệu" })).toBeTruthy();
    // Các nút action biến mất khi đang sửa → không thể race với blur-lưu.
    expect(screen.queryByRole("button", { name: "Xoá" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Xem" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Đổi tên" })).toBeNull();
  });

  it("Enter lưu tên mới qua onRename", () => {
    const { onRename } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Đổi tên" }));
    const input = screen.getByRole("textbox", { name: "Tên tài liệu" });
    fireEvent.change(input, { target: { value: "moi.pdf" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onRename).toHaveBeenCalledWith(1, "moi.pdf");
  });

  it("Escape huỷ, không gọi onRename", () => {
    const { onRename } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Đổi tên" }));
    const input = screen.getByRole("textbox", { name: "Tên tài liệu" });
    fireEvent.change(input, { target: { value: "moi.pdf" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onRename).not.toHaveBeenCalled();
  });

  it("tên không đổi → không gọi onRename", () => {
    const { onRename } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Đổi tên" }));
    const input = screen.getByRole("textbox", { name: "Tên tài liệu" });
    fireEvent.keyDown(input, { key: "Enter" }); // giữ nguyên "cu.pdf"
    expect(onRename).not.toHaveBeenCalled();
  });
});
