import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, documentApi } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("documentApi.fetchFile", () => {
  it("GET đúng URL file và trả Blob", async () => {
    const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(blob, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const out = await documentApi.fetchFile(5);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/admin/documents/5/file",
    );
    expect(out).toBeInstanceOf(Blob);
  });

  it("lỗi HTTP → ném ApiError", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Không tìm thấy tài liệu." }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(documentApi.fetchFile(9)).rejects.toBeInstanceOf(ApiError);
  });
});
