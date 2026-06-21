/** Mô hình tài liệu trích dẫn cho bảng nguồn (drawer) + ánh xạ từ DTO backend. */

import type { DocumentDetailDTO, Source } from "@/app/types/chat";

/** Một đoạn trong tài liệu: tiêu đề mục (heading) hoặc đoạn văn (text), có cờ tô sáng. */
export type CitationPara = {
  kind: "heading" | "text";
  text: string;
  highlight: boolean;
};

/** Tài liệu hiển thị trong drawer. `pages` là chuỗi meta sẵn dùng (vd "Đoạn 2 / 9"). */
export type CitationDocument = {
  id: number;
  title: string;
  kind: string;
  pages: string;
  paras: CitationPara[];
};

/** Loại tài liệu mặc định (backend chưa lưu trường này). */
const DEFAULT_KIND = "Tài liệu nội bộ";

/** Một nhóm nguồn theo tài liệu → một chip. */
export type SourceGroup = {
  /** null nếu nguồn không gắn tài liệu (document_id null) → chip không bấm được. */
  documentId: number | null;
  label: string;
  snippet: string | null;
  /** UUID các đoạn được trích của tài liệu này (tập tô sáng trong drawer). */
  citedUuids: Set<string>;
};

/** Nhãn chip: ưu tiên tên file, fallback "Tài liệu #id". */
function sourceLabel(s: Source): string {
  if (s.filename) return s.filename;
  if (s.document_id != null) return `Tài liệu #${s.document_id}`;
  return "Tài liệu";
}

/** Gộp nguồn theo tài liệu (document_id, fallback filename/index) → 1 chip mỗi tài liệu,
 *  kèm tập uuid được trích để tô sáng đúng đoạn. Giữ thứ tự xuất hiện. */
export function groupSourcesByDocument(sources: Source[] | undefined): SourceGroup[] {
  if (!sources?.length) return [];
  const order: string[] = [];
  const map = new Map<string, SourceGroup>();
  for (const s of sources) {
    const key =
      s.document_id != null ? `d${s.document_id}` : (s.filename ?? `i${s.index}`);
    let group = map.get(key);
    if (!group) {
      group = {
        documentId: s.document_id,
        label: sourceLabel(s),
        snippet: s.snippet,
        citedUuids: new Set<string>(),
      };
      map.set(key, group);
      order.push(key);
    }
    const u = normUuid(s.weaviate_uuid);
    if (u) group.citedUuids.add(u);
  }
  return order.map((k) => map.get(k)!);
}

/** Chuẩn hoá uuid để so khớp không phân biệt hoa/thường. */
function normUuid(uuid: string | null | undefined): string | null {
  return uuid ? uuid.toLowerCase() : null;
}

/** Tập uuid các đoạn đã được trích (từ danh sách nguồn của một tin nhắn), đã lọc null. */
export function citedUuidsFromSources(sources: Source[]): Set<string> {
  const set = new Set<string>();
  for (const s of sources) {
    const u = normUuid(s.weaviate_uuid);
    if (u) set.add(u);
  }
  return set;
}

/** Chuỗi meta "vị trí đoạn trích" cho pill — dựa trên các đoạn được tô sáng. */
export function pageMeta(paras: CitationPara[]): string {
  const total = paras.length;
  const cited = paras.reduce((n, p, i) => (p.highlight ? [...n, i + 1] : n), [] as number[]);
  if (total === 0) return "Chưa có nội dung";
  if (cited.length === 0) return `${total} đoạn`;
  if (cited.length === 1) return `Đoạn ${cited[0]} / ${total}`;
  return `${cited.length} đoạn được trích / ${total}`;
}

/** Dựng mô hình tài liệu cho drawer từ DTO backend + tập uuid được trích trong tin nhắn. */
export function buildCitationDocument(
  dto: DocumentDetailDTO,
  citedUuids: Set<string>,
): CitationDocument {
  const paras: CitationPara[] = dto.chunks.map((chunk) => {
    const u = normUuid(chunk.weaviate_uuid);
    return {
      kind: "text",
      text: chunk.content,
      highlight: u != null && citedUuids.has(u),
    };
  });
  return {
    id: dto.id,
    title: dto.filename,
    kind: DEFAULT_KIND,
    pages: pageMeta(paras),
    paras,
  };
}
