import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, chatApi, documentApi, statsApi } from "./api";

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

describe("documentApi.rename", () => {
  it("PATCH đúng URL + body { filename }", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: 3,
          filename: "Tên mới.pdf",
          file_size: 1,
          status: "ready",
          page_count: 1,
          chunk_count: 1,
          error_message: null,
          created_at: "2026-06-12T10:00:00",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const out = await documentApi.rename(3, "Tên mới.pdf");

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/admin/documents/3");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ filename: "Tên mới.pdf" });
    expect(out.filename).toBe("Tên mới.pdf");
  });
});

describe("statsApi.get", () => {
  it("GET /admin/stats kèm query range", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          range: "7d",
          active_parents: { value: 0, delta_pct: null },
          conversations: { value: 0, delta_pct: null },
          answered_questions: { value: 0, delta_pct: null },
          total_documents: 0,
          chart: [],
          topic: { label: "Tư vấn tuyển sinh tiểu học", count: 0 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const out = await statsApi.get("7d");

    expect(String(fetchMock.mock.calls[0][0])).toContain("/admin/stats?range=7d");
    expect(out.range).toBe("7d");
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
