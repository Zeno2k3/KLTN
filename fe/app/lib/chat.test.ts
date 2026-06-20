import { describe, expect, it } from "vitest";

import { convoFromSummary, msgFromDTO, sourceFromDTO } from "./chat";

const ISO = "2026-06-21T08:30:00.000Z";

describe("chat DTO → model mapping", () => {
  it("msgFromDTO: assistant → bot + giữ nguồn", () => {
    const m = msgFromDTO({
      id: 1,
      sender_type: "assistant",
      content: "Trường THCS Lê Hồng Phong [1].",
      created_at: ISO,
      sources: [
        {
          index: 1,
          document_id: 11,
          filename: "quy-che.pdf",
          weaviate_uuid: "u1",
          snippet: "đoạn",
          score: 0.5,
        },
      ],
    });
    expect(m.from).toBe("bot");
    expect(m.text).toContain("Lê Hồng Phong");
    expect(m.sources).toHaveLength(1);
    expect(m.sources?.[0].filename).toBe("quy-che.pdf");
  });

  it("msgFromDTO: user → không có sources", () => {
    const m = msgFromDTO({
      id: 2,
      sender_type: "user",
      content: "Hỏi gì đó?",
      created_at: ISO,
      sources: [],
    });
    expect(m.from).toBe("user");
    expect(m.sources).toBeUndefined();
  });

  it("convoFromSummary: serverId + preview + chưa loaded", () => {
    const c = convoFromSummary({
      id: 5,
      title: "Tuyển sinh lớp 1",
      updated_at: ISO,
      last_message: "Tin nhắn cuối",
    });
    expect(c.id).toBe("5");
    expect(c.serverId).toBe(5);
    expect(c.preview).toBe("Tin nhắn cuối");
    expect(c.loaded).toBe(false);
    expect(c.messages).toEqual([]);
  });

  it("sourceFromDTO: lược bỏ weaviate_uuid, giữ phần hiển thị", () => {
    const s = sourceFromDTO({
      index: 1,
      document_id: 3,
      filename: "a.pdf",
      weaviate_uuid: "uuid",
      snippet: "trích",
      score: 0.9,
    });
    expect(s).toEqual({
      index: 1,
      document_id: 3,
      filename: "a.pdf",
      snippet: "trích",
      score: 0.9,
    });
  });
});
