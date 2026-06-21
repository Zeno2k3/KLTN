import { describe, expect, it } from "vitest";

import {
  buildCitationDocument,
  citedUuidsFromSources,
  groupSourcesByDocument,
  pageMeta,
} from "./citations";
import type { DocumentDetailDTO, Source } from "@/app/types/chat";

function src(p: Partial<Source>): Source {
  return {
    index: null,
    document_id: null,
    filename: null,
    weaviate_uuid: null,
    snippet: null,
    score: null,
    ...p,
  };
}

const DTO: DocumentDetailDTO = {
  id: 1,
  filename: "hp.pdf",
  page_count: 9,
  chunk_count: 2,
  chunks: [
    { chunk_index: 0, content: "A", weaviate_uuid: "ABC" },
    { chunk_index: 1, content: "B", weaviate_uuid: "DEF" },
  ],
};

describe("citations", () => {
  it("buildCitationDocument tô sáng đúng chunk (so khớp uuid bất kể hoa/thường)", () => {
    const doc = buildCitationDocument(DTO, new Set(["def"]));
    expect(doc.title).toBe("hp.pdf");
    expect(doc.kind).toBe("Tài liệu nội bộ");
    expect(doc.paras.map((p) => p.highlight)).toEqual([false, true]);
    expect(doc.pages).toBe("Đoạn 2 / 2");
  });

  it("không có đoạn trích → pages = 'N đoạn'", () => {
    expect(buildCitationDocument(DTO, new Set()).pages).toBe("2 đoạn");
    expect(pageMeta([{ kind: "text", text: "x", highlight: false }])).toBe("1 đoạn");
  });

  it("nhiều đoạn trích → 'K đoạn được trích / N'", () => {
    const doc = buildCitationDocument(DTO, new Set(["abc", "def"]));
    expect(doc.pages).toBe("2 đoạn được trích / 2");
  });

  it("groupSourcesByDocument gộp theo document_id + gom uuid (hạ thường)", () => {
    const groups = groupSourcesByDocument([
      src({ index: 1, document_id: 1, filename: "a.pdf", weaviate_uuid: "U1" }),
      src({ index: 2, document_id: 1, filename: "a.pdf", weaviate_uuid: "U2" }),
      src({ index: 3, document_id: 2, filename: "b.pdf", weaviate_uuid: null }),
    ]);
    expect(groups).toHaveLength(2);
    expect(groups[0].documentId).toBe(1);
    expect(groups[0].citedUuids).toEqual(new Set(["u1", "u2"]));
    expect(groups[1].documentId).toBe(2);
    expect(groups[1].citedUuids.size).toBe(0);
  });

  it("citedUuidsFromSources lọc null + hạ thường", () => {
    expect(
      citedUuidsFromSources([src({ weaviate_uuid: "X" }), src({ weaviate_uuid: null })]),
    ).toEqual(new Set(["x"]));
  });
});
