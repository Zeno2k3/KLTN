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
});
