/** Mô hình tài liệu trích dẫn cho bảng nguồn (drawer) + ánh xạ từ DTO backend. */

import type { DocumentDetailDTO, Source } from "@/app/types/chat";

/** Một mảnh text trong đoạn được trích: `mark=true` → tô sáng (đúng đoạn câu trả lời dựa vào). */
export type CitationSegment = { text: string; mark: boolean };

/** Một đoạn trong tài liệu: tiêu đề mục (heading) hoặc đoạn văn (text), có cờ tô sáng.
 *  `segments` (chỉ khi đoạn được trích VÀ khớp được cited_spans) chia nhỏ để tô sáng đúng câu;
 *  thiếu segments → tô sáng cả đoạn (tương thích ngược / fallback khi không khớp). */
export type CitationPara = {
  kind: "heading" | "text";
  text: string;
  highlight: boolean;
  segments?: CitationSegment[];
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
  /** UUID chunk → các đoạn nguyên văn được trích trong chunk đó (để highlight sub-chunk). */
  citedSpans: Map<string, string[]>;
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
        citedSpans: new Map<string, string[]>(),
      };
      map.set(key, group);
      order.push(key);
    }
    const u = normUuid(s.weaviate_uuid);
    if (u) {
      group.citedUuids.add(u);
      const spans = s.cited_spans ?? [];
      if (spans.length) {
        group.citedSpans.set(u, [...(group.citedSpans.get(u) ?? []), ...spans]);
      }
    }
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

/** Escape ký tự đặc biệt cho RegExp. */
function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Gộp các khoảng [start,end) chồng/kề nhau, đã sắp xếp. */
function mergeRanges(ranges: [number, number][]): [number, number][] {
  if (ranges.length <= 1) return ranges;
  const sorted = [...ranges].sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [sorted[0]];
  for (let i = 1; i < sorted.length; i++) {
    const last = merged[merged.length - 1];
    const cur = sorted[i];
    if (cur[0] <= last[1]) last[1] = Math.max(last[1], cur[1]);
    else merged.push(cur);
  }
  return merged;
}

/** Vị trí các span (verbatim quote) trong content — khớp linh hoạt khoảng trắng, không phân biệt
 *  hoa/thường. Bỏ span < 3 ký tự (dễ khớp nhiễu). Trả [] nếu không khớp gì (→ fallback tô cả đoạn). */
function spanRanges(content: string, spans: string[]): [number, number][] {
  const ranges: [number, number][] = [];
  for (const raw of spans) {
    const span = raw.trim();
    if (span.length < 3) continue;
    const pattern = escapeRegex(span).replace(/\s+/g, "\\s+");
    let re: RegExp;
    try {
      re = new RegExp(pattern, "gi");
    } catch {
      continue;
    }
    let m: RegExpExecArray | null;
    while ((m = re.exec(content)) !== null) {
      if (m.index === re.lastIndex) re.lastIndex++;
      if (m[0].length > 0) ranges.push([m.index, m.index + m[0].length]);
    }
  }
  return mergeRanges(ranges);
}

/** Chia content thành segments tô sáng theo cited_spans. undefined nếu không khớp span nào
 *  (caller fallback tô sáng cả đoạn — giữ tương thích ngược với tin nhắn cũ không có cited_spans). */
function highlightSegments(
  content: string,
  spans: string[],
): CitationSegment[] | undefined {
  const ranges = spanRanges(content, spans);
  if (!ranges.length) return undefined;
  const segs: CitationSegment[] = [];
  let pos = 0;
  for (const [s, e] of ranges) {
    if (s > pos) segs.push({ text: content.slice(pos, s), mark: false });
    segs.push({ text: content.slice(s, e), mark: true });
    pos = e;
  }
  if (pos < content.length) segs.push({ text: content.slice(pos), mark: false });
  return segs;
}

/** Dựng mô hình tài liệu cho drawer từ DTO backend + tập uuid được trích trong tin nhắn.
 *  ``citedSpans`` (tuỳ chọn): uuid → các đoạn nguyên văn → tô sáng đúng câu (sub-chunk). */
export function buildCitationDocument(
  dto: DocumentDetailDTO,
  citedUuids: Set<string>,
  citedSpans?: Map<string, string[]>,
): CitationDocument {
  const paras: CitationPara[] = dto.chunks.map((chunk) => {
    const u = normUuid(chunk.weaviate_uuid);
    const highlight = u != null && citedUuids.has(u);
    const spans = (u != null ? citedSpans?.get(u) : undefined) ?? [];
    return {
      kind: "text",
      text: chunk.content,
      highlight,
      segments: highlight && spans.length ? highlightSegments(chunk.content, spans) : undefined,
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
