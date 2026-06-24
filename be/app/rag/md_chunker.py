"""LLM chunker trên markdown LlamaParse (thay ``chunker.py``) — văn bản hành chính tiếng Việt cho RAG.

Đầu vào là ``list[ParsedPage]`` của ``app.rag.parse`` — mỗi trang đã có ``blocks`` ĐÃ PHÂN LOẠI bởi
LlamaParse (heading | text | table, kèm ``rows`` lưới ô cho bảng). Block chính là ĐƠN VỊ NGUYÊN TỬ →
không cần regex tách cấu trúc (structure.py cũ đã bỏ).

Triết lý (giữ ràng buộc cứng của dự án):
- **LLM quyết định GỘP + sinh ``context``, KHÔNG sinh lại nội dung.** LLM nhận các block đánh số, trả về
  các nhóm chỉ-số block + ``heading_path`` + ``context`` + ``chunk_type``. Nội dung chunk do code GHÉP
  từ ``block.md`` VERBATIM → LLM không thể sửa/bịa văn bản pháp lý. Phân hoạch không hợp lệ / LLM lỗi →
  fallback rule-based (gộp block theo ``chunk_size``).
- **Bảng → chunk độc lập** (markdown GFM), ``has_table=True``, lưới ô lấy thẳng từ ``block.rows`` →
  ``table_data``; KHÔNG gửi bảng qua LLM (đã có cấu trúc, tránh mangle + tốn token).
- **Contextual prepend:** ``node.text = context + "\\n\\n" + content`` → context vào CẢ embedding LẪN
  BM25. Nội dung gốc + context lưu riêng để trích dẫn sạch.
- **Batch theo region** (token budget, cắt ở ranh giới heading) để prompt LLM bị chặn kích thước với
  tài liệu dài; fallback cục bộ từng region.

LLM dùng module-singleton RIÊNG (không chung synthesize/rewriter); mọi call qua LlamaIndex → Phoenix
auto-trace; toàn bộ bọc trong span ``rag.ingest.chunk``.
"""

from __future__ import annotations

import json
import logging
import re
import uuid as uuid_lib
from dataclasses import dataclass

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode
from llama_index.llms.openai import OpenAI
from opentelemetry import trace

from app.core.config import settings
from app.rag.ingest import count_tokens
from app.rag.parse import ParsedBlock, ParsedPage, Table

logger = logging.getLogger(__name__)

# LLM RIÊNG cho bước chunking (singleton trong module). Model: chunker_model → fallback chat model.
_llm: OpenAI | None = None


def _get_llm() -> OpenAI:
    global _llm
    if _llm is None:
        _llm = OpenAI(
            model=settings.chunker_model or settings.openai_chat_model,
            api_key=settings.openai_api_key,
        )
    return _llm


_CHUNK_SYSTEM_PROMPT = """\
Bạn là bộ chia chunk cho VĂN BẢN HÀNH CHÍNH tiếng Việt (đã ở dạng Markdown sạch) phục vụ tìm kiếm (RAG).

Đầu vào: một SECTION đã được tách sẵn thành các BLOCK đánh số (mỗi block là một tiêu đề, một đoạn, một
Khoản, hoặc một Điểm). Phân cấp văn bản hành chính: Phần → Chương → Mục → Điều → Khoản (gạch đầu dòng
'-') → Điểm ((a),(b)/(i),(ii)). Lưu ý: LlamaParse đôi khi tách nhầm một SỐ THỨ TỰ ("4.", "5.") thành
tiêu đề riêng — hãy GỘP nó với đoạn nội dung liền sau.

Nhiệm vụ:
1. GỘP các block LIỀN KỀ thành các chunk mạch lạc về ngữ nghĩa, bám sát ranh giới cấu trúc:
   - TUYỆT ĐỐI không tách một block; chỉ gộp nguyên block. Mỗi block thuộc đúng MỘT chunk; giữ nguyên
     thứ tự; phải phủ HẾT mọi block.
   - Gom trọn một Điều (cùng các Khoản/Điểm của nó) vào một chunk nếu không quá dài; Điều quá dài thì
     tách theo Khoản, mỗi nhóm Khoản một chunk, KHÔNG cắt giữa Khoản.
2. Với MỖI chunk, viết:
   - "heading_path": danh sách đầu mục từ ngoài vào trong, vd ["A. YÊU CẦU","I. PHƯƠNG THỨC","Điều 5"].
   - "context": 1–2 câu tiếng Việt nêu chunk thuộc văn bản nào, ở Điều/Mục nào, nói về gì.
   - "chunk_type": "text" | "list" | "mixed".

KHÔNG viết lại, KHÔNG tóm tắt, KHÔNG dịch, KHÔNG bịa nội dung — chỉ trả về ranh giới + heading_path +
context. CHỈ in JSON (không giải thích), dạng mảng:
[{"blocks":[0,1],"heading_path":["..."],"context":"...","chunk_type":"text"}, ...]
"""


@dataclass
class ChunkNode:
    """Một chunk sẵn sàng ghi Weaviate (``node``) + lưu Postgres (các field còn lại)."""

    node: TextNode
    content: str  # nội dung gốc (KHÔNG kèm context) — lưu DocumentChunk.content
    context: str
    heading_path: list[str]
    chunk_type: str
    has_table: bool
    page_number: int
    token_count: int = 0
    table_data: Table | None = None


# ---------------------------------------------------------------------------
# Block (item LlamaParse) — kiểu (page_number, ParsedBlock)
# ---------------------------------------------------------------------------
PagedBlock = tuple[int, ParsedBlock]


def _heading_context(heading_path: list[str], doc_meta: dict, extra: str = "") -> str:
    parts: list[str] = []
    name = doc_meta.get("doc_name") or doc_meta.get("filename")
    if name:
        parts.append(f"Trích từ {name}.")
    if heading_path:
        parts.append("Thuộc: " + " > ".join(heading_path) + ".")
    if extra:
        parts.append(extra)
    return " ".join(parts).strip()


def _chunk_type_from_text(text: str) -> str:
    """Đoán loại chunk: ≥2 dòng gạch đầu dòng → "list"; ngược lại "text"."""
    bullets = sum(1 for ln in text.splitlines() if ln.lstrip().startswith(("- ", "* ")))
    return "list" if bullets >= 2 else "text"


# ---------------------------------------------------------------------------
# Heading breadcrumb (stack theo level) — fallback heading_path + ngữ cảnh region
# ---------------------------------------------------------------------------
def _update_stack(stack: dict[int, str], block: ParsedBlock) -> None:
    """Cập nhật stack tiêu đề khi gặp block heading (pop mọi level >= level hiện hành)."""
    if block.type != "heading" or not block.value:
        return
    lvl = block.level or 1
    for deeper in [d for d in stack if d >= lvl]:
        del stack[deeper]
    stack[lvl] = block.value


def _breadcrumb(stack: dict[int, str]) -> list[str]:
    return [stack[k] for k in sorted(stack)]


# ---------------------------------------------------------------------------
# Fallback rule-based: gộp block theo ngưỡng mềm chunk_size (KHÔNG gọi LLM)
# ---------------------------------------------------------------------------
def _merge_block_texts(texts: list[str]) -> list[str]:
    """Gộp các block markdown liền kề tới ngưỡng mềm ``chunk_size`` token; KHÔNG tách một block."""
    if len(texts) <= 1:
        return [t for t in texts if t.strip()]
    chunks: list[str] = []
    cur: list[str] = []
    cur_tok = 0
    for t in texts:
        tt = count_tokens(t)
        if cur and cur_tok + tt > settings.chunk_size:
            chunks.append("\n\n".join(cur))
            cur, cur_tok = [], 0
        cur.append(t)
        cur_tok += tt
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


# ---------------------------------------------------------------------------
# LLM grouping
# ---------------------------------------------------------------------------
def _parse_json_array(raw: str) -> list:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    start, end = s.find("["), s.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Không tìm thấy mảng JSON trong output LLM.")
    data = json.loads(s[start : end + 1])
    if not isinstance(data, list) or not data:
        raise ValueError("Output LLM không phải mảng JSON không rỗng.")
    return data


def _validate_partition(groups: list, n_blocks: int) -> list[list[int]]:
    """Kiểm các nhóm block là phân hoạch HỢP LỆ (phủ hết, không trùng, mỗi nhóm LIỀN KỀ tăng dần)."""
    seen: set[int] = set()
    norm: list[list[int]] = []
    for g in groups:
        idx = g.get("blocks") if isinstance(g, dict) else None
        if not isinstance(idx, list) or not idx:
            raise ValueError("Nhóm thiếu 'blocks'.")
        idx = [int(i) for i in idx]
        if any(i < 0 or i >= n_blocks for i in idx):
            raise ValueError("Chỉ số block ngoài phạm vi.")
        if idx != list(range(idx[0], idx[0] + len(idx))):
            raise ValueError("Block trong nhóm không liền kề/tăng dần.")
        if seen & set(idx):
            raise ValueError("Block bị gộp vào nhiều nhóm.")
        seen.update(idx)
        norm.append(idx)
    if seen != set(range(n_blocks)):
        raise ValueError("Phân hoạch không phủ hết block.")
    return norm


def _clean_heading_path(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out = [str(x).strip() for x in value if str(x).strip()]
    return out or None


def _llm_group(
    blocks: list[PagedBlock], breadcrumb: list[str], doc_meta: dict
) -> list[tuple[str, list[str], str, str, int]]:
    """Gọi LLM gộp block + sinh heading_path/context. Trả [(content, heading_path, context, ctype, page)].

    content GHÉP từ ``block.md`` verbatim. Lỗi/không hợp lệ → raise (tầng gọi fallback rule-based)."""
    numbered = "\n\n".join(f"[BLOCK {i}]\n{b.md}" for i, (_, b) in enumerate(blocks))
    crumb = " > ".join(breadcrumb) if breadcrumb else "(đầu văn bản)"
    user = (
        f"TÀI LIỆU: {doc_meta.get('doc_name') or doc_meta.get('filename') or 'không rõ'}\n"
        f"VỊ TRÍ (breadcrumb): {crumb}\n\n"
        f"SECTION gồm {len(blocks)} block:\n{numbered}\n\n"
        "Hãy gộp block và sinh heading_path/context theo đúng định dạng JSON đã nêu."
    )
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_CHUNK_SYSTEM_PROMPT),
        ChatMessage(role=MessageRole.USER, content=user),
    ]
    response = _get_llm().chat(messages)
    data = _parse_json_array(response.message.content or "")
    norm = _validate_partition(data, len(blocks))

    out: list[tuple[str, list[str], str, str, int]] = []
    for grp_idx, idx in enumerate(norm):
        content = "\n\n".join(blocks[i][1].md for i in idx)
        meta = data[grp_idx] if isinstance(data[grp_idx], dict) else {}
        hp = _clean_heading_path(meta.get("heading_path")) or breadcrumb
        context = (meta.get("context") or "").strip() or _heading_context(hp, doc_meta)
        ctype = (
            meta.get("chunk_type")
            if meta.get("chunk_type") in {"text", "list", "mixed"}
            else _chunk_type_from_text(content)
        )
        page_no = blocks[idx[0]][0]
        out.append((content, hp, context, ctype, page_no))
    return out


def _chunk_segment(
    blocks: list[PagedBlock], breadcrumb: list[str], doc_meta: dict
) -> list[tuple[str, list[str], str, str, int]]:
    """Chia một segment block NON-TABLE → [(content, heading_path, context, ctype, page)]."""
    if not blocks:
        return []
    total = count_tokens("\n\n".join(b.md for _, b in blocks))
    use_llm = (
        settings.chunk_llm_enabled
        and len(blocks) > 1
        and total > settings.chunk_llm_min_tokens
    )
    if use_llm:
        try:
            return _llm_group(blocks, breadcrumb, doc_meta)
        except Exception:  # noqa: BLE001 — mọi lỗi LLM/parse/phân hoạch → fallback an toàn
            logger.warning(
                "LLM chunker fallback rule-based (breadcrumb: %s).",
                " > ".join(breadcrumb) or "(đầu văn bản)",
            )
    # Fallback rule-based: gộp block theo ngưỡng mềm; heading_path/context xác định từ breadcrumb.
    page_no = blocks[0][0]
    ctx = _heading_context(breadcrumb, doc_meta)
    return [
        (ct, breadcrumb, ctx, _chunk_type_from_text(ct), page_no)
        for ct in _merge_block_texts([b.md for _, b in blocks])
    ]


# ---------------------------------------------------------------------------
# Dựng TextNode (giữ Y NGUYÊN cơ chế ref_doc_id + excluded keys của chunker cũ)
# ---------------------------------------------------------------------------
def _doc_ref_id(document_id: int) -> str:
    """UUID xác định theo tài liệu, dùng làm ``ref_doc_id`` (SOURCE) cho mọi chunk của tài liệu.

    BẮT BUỘC: WeaviateVectorStore map ``ref_doc_id`` sang property ``doc_id``/``document_id`` (UUID).
    Node không có SOURCE → ref_doc_id=None → Weaviate từ chối. UUID5 ổn định theo id tài liệu để vừa
    hợp lệ vừa gom chunk theo tài liệu (hỗ trợ xoá theo ref)."""
    return str(uuid_lib.uuid5(uuid_lib.NAMESPACE_URL, f"kltn-document:{document_id}"))


def _make_node(
    *,
    content: str,
    context: str,
    document_id: int,
    filename: str | None,
    doc_meta: dict,
    heading_path: list[str],
    chunk_type: str,
    has_table: bool,
    page_number: int,
    table_data: Table | None = None,
) -> ChunkNode:
    text = f"{context}\n\n{content}" if context else content
    metadata: dict[str, object] = {
        "document_id": document_id,
        "filename": filename,
        "doc_name": doc_meta.get("doc_name"),
        "doc_type": doc_meta.get("doc_type"),
        "issued_date": doc_meta.get("issued_date"),
        "issuing_body": doc_meta.get("issuing_body"),
        "school_year": doc_meta.get("school_year"),
        "ward": doc_meta.get("ward"),
        "heading_path": " > ".join(heading_path),
        "chunk_type": chunk_type,
        "has_table": has_table,
        "page_number": page_number,
    }
    node = TextNode(text=text, metadata=metadata)
    node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
        node_id=_doc_ref_id(document_id)
    )
    keys = list(metadata.keys())
    node.excluded_embed_metadata_keys = keys
    node.excluded_llm_metadata_keys = keys
    return ChunkNode(
        node=node,
        content=content,
        context=context,
        heading_path=heading_path,
        chunk_type=chunk_type,
        has_table=has_table,
        page_number=page_number,
        token_count=count_tokens(text),
        table_data=table_data,
    )


# ---------------------------------------------------------------------------
# Ráp toàn bộ chunk
# ---------------------------------------------------------------------------
def build_nodes(
    pages: list[ParsedPage],
    document_id: int,
    filename: str | None = None,
    doc_meta: dict | None = None,
) -> list[ChunkNode]:
    """Ráp toàn bộ chunk (text + bảng) từ các trang LlamaParse đã parse.

    Duyệt block theo thứ tự tài liệu: bảng → chunk độc lập; chuỗi block non-table → segment (cắt ở
    ranh giới heading khi vượt ``chunk_llm_region_max_tokens``) → LLM gộp/fallback. Bọc span
    ``rag.ingest.chunk``."""
    doc_meta = dict(doc_meta or {})
    doc_meta.setdefault("filename", filename)
    doc_meta.setdefault("doc_name", doc_meta.get("doc_name") or filename)

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.ingest.chunk") as span:
        span.set_attribute("rag.ingest.document_id", document_id)
        span.set_attribute("rag.ingest.pages", len(pages))

        out: list[ChunkNode] = []
        stack: dict[int, str] = {}
        segment: list[PagedBlock] = []
        seg_breadcrumb: list[str] = []
        seg_tokens = 0

        def flush_segment() -> None:
            nonlocal segment, seg_breadcrumb, seg_tokens
            if not segment:
                return
            for content, hp, ctx, ctype, page_no in _chunk_segment(
                segment, seg_breadcrumb, doc_meta
            ):
                if not content.strip():
                    continue
                out.append(
                    _make_node(
                        content=content,
                        context=ctx,
                        document_id=document_id,
                        filename=filename,
                        doc_meta=doc_meta,
                        heading_path=hp,
                        chunk_type=ctype,
                        has_table=False,
                        page_number=page_no,
                    )
                )
            segment, seg_breadcrumb, seg_tokens = [], [], 0

        for page in pages:
            for block in page.blocks:
                if block.type == "table":
                    flush_segment()
                    _update_stack(stack, block)  # bảng không là heading, no-op
                    hp = _breadcrumb(stack)
                    grid = block.rows
                    content = block.md or ""
                    if not content.strip() and not grid:
                        continue
                    out.append(
                        _make_node(
                            content=content,
                            context=_heading_context(
                                hp, doc_meta, extra="Dữ liệu dạng bảng."
                            ),
                            document_id=document_id,
                            filename=filename,
                            doc_meta=doc_meta,
                            heading_path=hp,
                            chunk_type="table",
                            has_table=True,
                            page_number=page.page_number,
                            table_data=grid,
                        )
                    )
                    continue

                _update_stack(stack, block)
                if not segment:
                    seg_breadcrumb = _breadcrumb(stack)
                # Cắt segment ở ranh giới heading khi vượt ngưỡng region (chặn prompt LLM quá to).
                if (
                    block.type == "heading"
                    and seg_tokens >= settings.chunk_llm_region_max_tokens
                ):
                    flush_segment()
                    seg_breadcrumb = _breadcrumb(stack)
                segment.append((page.page_number, block))
                seg_tokens += count_tokens(block.md)

        flush_segment()
        span.set_attribute("rag.ingest.chunks", len(out))
        return out
