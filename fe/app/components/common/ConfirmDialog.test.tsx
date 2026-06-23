import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ConfirmDialog from "./ConfirmDialog";

afterEach(cleanup);

describe("ConfirmDialog", () => {
  it("open=false → không render gì", () => {
    const { container } = render(
      <ConfirmDialog
        open={false}
        title="Xóa cuộc trò chuyện"
        message="msg"
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("hiện message; nút Xóa → onConfirm, Hủy → onCancel", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Xóa cuộc trò chuyện"
        message={<span>Bạn có chắc muốn xóa “A” không?</span>}
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        variant="danger"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByText("Bạn có chắc muốn xóa “A” không?")).toBeTruthy();
    fireEvent.click(screen.getByText("Xóa"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText("Hủy"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("nhấn Esc → onCancel", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        title="t"
        message="m"
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("variant=danger: Hủy là nút primary, Xóa là outline đỏ (không nền đỏ đặc)", () => {
    render(
      <ConfirmDialog
        open
        title="Xóa cuộc trò chuyện"
        message="m"
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        variant="danger"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const cancelBtn = screen.getByText("Hủy");
    const confirmBtn = screen.getByText("Xóa");
    expect(cancelBtn.className).toContain("gw-btn--primary");
    expect(confirmBtn.className).toContain("gw-btn--danger-outline");
    expect(confirmBtn.className).not.toMatch(/gw-btn--danger(?!-outline)/);
  });

  it("click nền (overlay) → onCancel; click trong dialog → không", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        open
        title="Xóa cuộc trò chuyện"
        message="m"
        confirmLabel="Xóa"
        cancelLabel="Hủy"
        variant="danger"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    const dialog = screen.getByRole("dialog");
    // Click trong dialog: stopPropagation → không đóng.
    fireEvent.click(dialog);
    expect(onCancel).not.toHaveBeenCalled();
    // Click nền overlay (cha của dialog) → đóng.
    const overlay = dialog.parentElement as HTMLElement;
    fireEvent.click(overlay);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
