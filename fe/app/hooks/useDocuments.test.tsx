import type { ChangeEvent } from "react";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DocumentDTO } from "@/app/types/admin";

// Mock lớp gọi API (hoisted để dùng trong factory vi.mock).
const { listMock, uploadMock, removeMock, removeAllMock, fetchFileMock } = vi.hoisted(
  () => ({
    listMock: vi.fn(),
    uploadMock: vi.fn(),
    removeMock: vi.fn(),
    removeAllMock: vi.fn(),
    fetchFileMock: vi.fn(),
  }),
);

vi.mock("@/app/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
  documentApi: {
    list: listMock,
    upload: uploadMock,
    remove: removeMock,
    removeAll: removeAllMock,
    fetchFile: fetchFileMock,
  },
}));

import { useDocuments } from "./useDocuments";

function dto(over: Partial<DocumentDTO> = {}): DocumentDTO {
  return {
    id: 1,
    filename: "a.pdf",
    file_size: 1_500_000,
    status: "ready",
    page_count: 2,
    chunk_count: 4,
    error_message: null,
    created_at: "2026-06-12T10:00:00",
    ...over,
  };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  listMock.mockReset();
  uploadMock.mockReset();
  removeMock.mockReset();
  removeAllMock.mockReset();
  fetchFileMock.mockReset();
});

describe("useDocuments", () => {
  it("tải danh sách khi mount và map sang Doc", async () => {
    listMock.mockResolvedValue([dto({ id: 1, filename: "a.pdf" })]);
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.docs).toHaveLength(1);
    expect(result.current.docs[0].name).toBe("a.pdf");
    expect(result.current.docs[0].status).toBe("ready");
  });

  it("upload thêm tài liệu vào đầu danh sách", async () => {
    listMock.mockResolvedValue([]);
    uploadMock.mockResolvedValue(dto({ id: 9, filename: "moi.pdf", status: "processing" }));
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const file = new File(["x"], "moi.pdf", { type: "application/pdf" });
    const evt = { target: { files: [file], value: "" } } as unknown as ChangeEvent<HTMLInputElement>;
    await act(async () => {
      await result.current.onPick(evt);
    });

    expect(uploadMock).toHaveBeenCalledOnce();
    expect(result.current.docs[0].name).toBe("moi.pdf");
    expect(result.current.docs[0].status).toBe("processing");
  });

  it("xoá tài liệu (optimistic) và gọi API remove", async () => {
    listMock.mockResolvedValue([dto({ id: 1 })]);
    removeMock.mockResolvedValue(undefined);
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.docs).toHaveLength(1));

    await act(async () => {
      await result.current.deleteDoc(1);
    });

    expect(removeMock).toHaveBeenCalledWith(1);
    expect(result.current.docs).toHaveLength(0);
  });

  it("xoá tất cả (optimistic) và gọi API removeAll", async () => {
    listMock.mockResolvedValue([dto({ id: 1 }), dto({ id: 2, filename: "b.pdf" })]);
    removeAllMock.mockResolvedValue({ deleted: 2 });
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.docs).toHaveLength(2));

    await act(async () => {
      await result.current.deleteAll();
    });

    expect(removeAllMock).toHaveBeenCalledOnce();
    expect(result.current.docs).toHaveLength(0);
  });

  it("removeAll lỗi → refresh đồng bộ lại + set error", async () => {
    // list trả về cùng dữ liệu ở lần mount và lần refresh sau lỗi.
    listMock.mockResolvedValue([dto({ id: 1 })]);
    removeAllMock.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.docs).toHaveLength(1));

    await act(async () => {
      await result.current.deleteAll();
    });

    expect(result.current.docs).toHaveLength(1); // refresh kéo lại từ server
    expect(result.current.error).toBeTruthy();
  });

  it("openDoc (xem) tải blob qua apiFetch và mở tab", async () => {
    listMock.mockResolvedValue([dto({ id: 1 })]);
    fetchFileMock.mockResolvedValue(new Blob(["x"], { type: "application/pdf" }));
    const fakeWin = { location: { href: "" }, close: vi.fn() };
    const openSpy = vi
      .spyOn(window, "open")
      .mockReturnValue(fakeWin as unknown as Window);
    vi.stubGlobal("URL", {
      createObjectURL: () => "blob:abc",
      revokeObjectURL: () => {},
    });

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.docs).toHaveLength(1));

    await act(async () => {
      await result.current.openDoc(result.current.docs[0], false);
    });

    expect(fetchFileMock).toHaveBeenCalledWith(1);
    expect(openSpy).toHaveBeenCalled();
    expect(fakeWin.location.href).toBe("blob:abc");
  });

  it("openDoc (tải) tạo anchor download và click", async () => {
    listMock.mockResolvedValue([dto({ id: 1, filename: "a.pdf" })]);
    fetchFileMock.mockResolvedValue(new Blob(["x"]));
    const clickSpy = vi.fn();
    const realCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = realCreate(tag);
      if (tag === "a") el.click = clickSpy;
      return el;
    });
    vi.stubGlobal("URL", {
      createObjectURL: () => "blob:dl",
      revokeObjectURL: () => {},
    });

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.docs).toHaveLength(1));

    await act(async () => {
      await result.current.openDoc(result.current.docs[0], true);
    });

    expect(clickSpy).toHaveBeenCalled();
  });

  it("openDoc lỗi → đóng tab + set error", async () => {
    listMock.mockResolvedValue([dto({ id: 1 })]);
    fetchFileMock.mockRejectedValue(new Error("x"));
    const closeSpy = vi.fn();
    vi.spyOn(window, "open").mockReturnValue({
      location: { href: "" },
      close: closeSpy,
    } as unknown as Window);

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.docs).toHaveLength(1));

    await act(async () => {
      await result.current.openDoc(result.current.docs[0], false);
    });

    expect(closeSpy).toHaveBeenCalled();
    expect(result.current.error).toBeTruthy();
  });
});
