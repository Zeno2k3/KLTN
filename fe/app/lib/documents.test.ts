import { describe, expect, it } from "vitest";
import type { DocumentDTO } from "@/app/types/admin";
import { docFromDTO, formatDateDMY, formatSize } from "./documents";

describe("formatSize", () => {
  it("hiển thị MB khi >= 1MB", () => {
    expect(formatSize(2_000_000)).toBe("1,9 MB");
  });
  it("hiển thị KB khi < 1MB", () => {
    expect(formatSize(920 * 1024)).toBe("920 KB");
  });
  it("thiếu/0 kích thước → —", () => {
    expect(formatSize(null)).toBe("—");
    expect(formatSize(0)).toBe("—");
  });
});

describe("formatDateDMY", () => {
  it("ISO → DD/MM/YYYY", () => {
    expect(formatDateDMY("2026-06-08T10:00:00")).toBe("08/06/2026");
  });
  it("chuỗi sai → rỗng", () => {
    expect(formatDateDMY("khong-phai-ngay")).toBe("");
  });
});

describe("docFromDTO", () => {
  const base: DocumentDTO = {
    id: 3,
    filename: "quy-che.pdf",
    file_size: 2_000_000,
    status: "processing",
    page_count: null,
    chunk_count: 0,
    error_message: null,
    created_at: "2026-06-12T10:00:00",
  };

  it("map các trường + ghép meta (dung lượng · thêm ngày)", () => {
    const d = docFromDTO(base);
    expect(d.id).toBe(3);
    expect(d.name).toBe("quy-che.pdf");
    expect(d.status).toBe("processing");
    expect(d.meta).toBe("1,9 MB · thêm 12/06/2026");
  });

  it("trạng thái failed mang theo error_message", () => {
    const d = docFromDTO({ ...base, status: "failed", error_message: "PDF scan ảnh" });
    expect(d.status).toBe("failed");
    expect(d.error).toBe("PDF scan ảnh");
  });
});
