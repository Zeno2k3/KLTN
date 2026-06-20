import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, chatApi, documentApi } from "./api";

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

describe("chatApi.ask", () => {
  it("POST /chat/ask đúng URL + body (question, conversation_id)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ conversation_id: 7, answer: "Đáp.", sources: [] }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const out = await chatApi.ask("Khi nào tuyển sinh?", 7);

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/chat/ask");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      question: "Khi nào tuyển sinh?",
      conversation_id: 7,
    });
    expect(out.conversation_id).toBe(7);
  });

  it("không truyền id → conversation_id null", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ conversation_id: 1, answer: "x", sources: [] }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await chatApi.ask("Hỏi?");

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      question: "Hỏi?",
      conversation_id: null,
    });
  });
});
