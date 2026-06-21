import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentDetailDTO } from "@/app/types/chat";

const { getDocument } = vi.hoisted(() => ({ getDocument: vi.fn() }));
vi.mock("@/app/lib/api", () => ({ chatApi: { getDocument } }));

import SourceDrawer from "./SourceDrawer";

afterEach(() => {
  cleanup();
  getDocument.mockReset();
});

const DTO: DocumentDetailDTO = {
  id: 7,
  filename: "Bảng học phí.pdf",
  page_count: 9,
  chunk_count: 3,
  chunks: [
    { chunk_index: 0, content: "Đoạn không", weaviate_uuid: "AAA" },
    { chunk_index: 1, content: "Đoạn được trích nổi bật", weaviate_uuid: "BBB" },
    { chunk_index: 2, content: "Đoạn hai", weaviate_uuid: "CCC" },
  ],
};

function renderOpen(onClose = vi.fn(), cited = new Set(["bbb"])) {
  return render(
    <SourceDrawer
      open
      documentId={7}
      citedUuids={cited}
      fallbackTitle="Bảng học phí.pdf"
      onClose={onClose}
    />,
  );
}

describe("SourceDrawer", () => {
  it("open=false → không render gì + không gọi API", () => {
    const { container } = render(
      <SourceDrawer open={false} documentId={7} citedUuids={new Set()} onClose={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
    expect(getDocument).not.toHaveBeenCalled();
  });

  it("đang tải → hiện trạng thái loading", () => {
    getDocument.mockReturnValue(new Promise(() => {})); // pending mãi
    renderOpen();
    expect(screen.getByText("Đang tải tài liệu…")).toBeTruthy();
  });

  it("mở → hiện tiêu đề + cả 3 đoạn; đoạn được trích tô sáng (★) đúng 1 lần; meta vị trí đoạn", async () => {
    getDocument.mockResolvedValue(DTO);
    renderOpen();

    expect(await screen.findByText("Đoạn được trích nổi bật")).toBeTruthy();
    expect(getDocument).toHaveBeenCalledWith(7);
    expect(screen.getByText("Đoạn không")).toBeTruthy();
    expect(screen.getByText("Đoạn hai")).toBeTruthy();
    expect(screen.getByText("Nguồn tham khảo")).toBeTruthy(); // eyebrow
    // chỉ 1 đoạn được tô sáng (chunk BBB).
    expect(screen.getAllByText("Đoạn được trích dẫn")).toHaveLength(1);
    expect(screen.getByText(/tô sáng bên dưới/)).toBeTruthy();
    expect(screen.getByText("Đoạn 2 / 3")).toBeTruthy(); // BBB ở vị trí 2/3
  });

  it("đóng bằng X / Esc / bấm overlay; bấm panel KHÔNG đóng", async () => {
    getDocument.mockResolvedValue(DTO);
    const onClose = vi.fn();
    const { container } = renderOpen(onClose);
    await screen.findByText("Đoạn hai");

    fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);

    fireEvent.click(container.querySelector('[role="presentation"]')!);
    expect(onClose).toHaveBeenCalledTimes(3);

    // Bấm vào panel (dialog) không lan ra overlay → không đóng.
    fireEvent.click(container.querySelector('[role="dialog"]')!);
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("lỗi tải → hiện thông báo + nút thử lại", async () => {
    getDocument.mockRejectedValue(new Error("boom"));
    renderOpen();
    expect(await screen.findByText(/Không tải được tài liệu/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Thử lại" })).toBeTruthy();
  });
});
