"""Structure-aware + LLM chunker cho văn bản hành chính tiếng Việt (thay ``chunk_to_nodes``).

Triết lý (đáp ứng ràng buộc cứng của dự án):
- **Khoản là đơn vị nguyên tử.** Section được tách thành các *block* theo ranh giới Khoản (dấu ``-``)
  TRƯỚC; chunk chỉ là phép GỘP các block liền kề. Vì vậy **không bao giờ cắt giữa Khoản**, và một
  Khoản dài luôn là một chunk dù vượt ``chunk_size``.
- **LLM quyết định GỘP + sinh ``context``, KHÔNG sinh lại nội dung.** LLM trả về các nhóm chỉ-số
  block + một đoạn ``context`` định vị chunk (Contextual Retrieval). Nội dung chunk do code GHÉP từ
  block verbatim → LLM không thể sửa/bịa nội dung văn bản pháp lý. Nếu LLM lỗi / phân hoạch không
  hợp lệ → fallback rule-based (gộp theo ``chunk_size``).
- **Contextual prepend:** ``node.text = context + "\n\n" + content`` → ``context`` vào CẢ embedding
  LẪN BM25 (Weaviate lưu ``text`` = node.text). Nội dung gốc + context lưu riêng để trích dẫn sạch.
- **Bảng → node độc lập** (markdown), ``has_table=True``, KHÔNG qua LLM chunking.

LLM dùng module-singleton RIÊNG (không chung với synthesize/rewriter); mọi call qua LlamaIndex →
Phoenix auto-trace; toàn bộ bọc trong span ``rag.ingest.chunk``.
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
from app.rag.extract import PageBlock, Table
from app.rag.ingest import count_tokens
from app.rag.structure import Section, classify_line, heading_path_for_page, segment

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
Bạn là bộ chia chunk cho tài liệu hành chính tiếng Việt phục vụ tìm kiếm (RAG).

Bạn nhận một SECTION đã được tách sẵn thành các BLOCK đánh số (mỗi block thường là một Khoản hoặc
đoạn mở đầu). Nhiệm vụ:
1. GỘP các block LIỀN KỀ thành các chunk mạch lạc về ngữ nghĩa. TUYỆT ĐỐI không tách một block; chỉ
   gộp nguyên block. Mỗi block thuộc đúng MỘT chunk; thứ tự block giữ nguyên; phải phủ hết mọi block.
2. Với MỖI chunk, viết một câu ``context`` NGẮN (1–2 câu) định vị chunk trong tài liệu (thuộc văn
   bản nào, Phần/Mục/Điều nào, nói về gì) để tăng độ chính xác truy hồi. Viết bằng tiếng Việt.

CHỈ in ra JSON (không giải thích), dạng mảng:
[{"blocks": [0,1], "context": "...", "chunk_type": "text|list|mixed"}, ...]
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


# ---------------------------------------------------------------------------
# Tách Khoản nguyên tử
# ---------------------------------------------------------------------------
def split_into_khoan_blocks(text: str) -> list[str]:
    """Tách text của section thành các block nguyên tử theo ranh giới Khoản (dấu ``-``).

    Đoạn mở đầu trước Khoản đầu tiên là một block riêng. Điểm ``(i)/(a)`` và dòng thường thuộc về
    Khoản hiện hành (không mở block mới) → Khoản giữ trọn vẹn cùng các Điểm con."""
    blocks: list[str] = []
    cur: list[str] = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        if classify_line(line) == "khoan" and cur:
            blocks.append("\n".join(cur))
            cur = [line]
        elif classify_line(line) == "khoan":
            cur = [line]
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks or ([text.strip()] if text.strip() else [])


def _merge_blocks(blocks: list[str]) -> list[str]:
    """Gộp block liền kề tới ngưỡng mềm ``chunk_size`` token; KHÔNG bao giờ tách một block.

    Một block đơn vượt ngưỡng vẫn đứng riêng (Khoản nguyên tử)."""
    if len(blocks) <= 1:
        return [b for b in blocks if b.strip()]
    chunks: list[str] = []
    cur: list[str] = []
    cur_tok = 0
    for b in blocks:
        bt = count_tokens(b)
        if cur and cur_tok + bt > settings.chunk_size:
            chunks.append("\n".join(cur))
            cur, cur_tok = [], 0
        cur.append(b)
        cur_tok += bt
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def _chunk_type(text: str) -> str:
    """Đoán loại chunk text: có nhiều dòng Khoản → "list"; ngược lại "text"."""
    khoan = sum(1 for ln in text.split("\n") if classify_line(ln) == "khoan")
    return "list" if khoan >= 2 else "text"


# ---------------------------------------------------------------------------
# Context xác định (không gọi LLM) — cho chunk nhỏ / fallback / bảng
# ---------------------------------------------------------------------------
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
    """Kiểm các nhóm block là phân hoạch HỢP LỆ (phủ hết, không trùng, mỗi nhóm LIỀN KỀ tăng dần).

    Trả về danh sách nhóm chỉ-số đã chuẩn hoá; raise nếu không hợp lệ → tầng gọi fallback."""
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


def _llm_group(
    section: Section, blocks: list[str], doc_meta: dict
) -> list[tuple[str, str, str]]:
    """Gọi LLM gộp block + sinh context. Trả [(content, context, chunk_type)].

    content GHÉP từ block verbatim (LLM không sửa nội dung). Lỗi/không hợp lệ → raise (tầng gọi
    fallback rule-based)."""
    numbered = "\n\n".join(f"[BLOCK {i}]\n{b}" for i, b in enumerate(blocks))
    breadcrumb = " > ".join(section.heading_path) if section.heading_path else "(đầu văn bản)"
    user = (
        f"TÀI LIỆU: {doc_meta.get('doc_name') or doc_meta.get('filename') or 'không rõ'}\n"
        f"VỊ TRÍ (breadcrumb): {breadcrumb}\n\n"
        f"SECTION gồm {len(blocks)} block:\n{numbered}\n\n"
        "Hãy gộp block và sinh context theo đúng định dạng JSON đã nêu."
    )
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_CHUNK_SYSTEM_PROMPT),
        ChatMessage(role=MessageRole.USER, content=user),
    ]
    response = _get_llm().chat(messages)
    data = _parse_json_array(response.message.content or "")
    norm = _validate_partition(data, len(blocks))

    out: list[tuple[str, str, str]] = []
    for grp_idx, idx in enumerate(norm):
        content = "\n".join(blocks[i] for i in idx)
        meta = data[grp_idx] if isinstance(data[grp_idx], dict) else {}
        context = (meta.get("context") or "").strip() or _heading_context(
            section.heading_path, doc_meta
        )
        ctype = meta.get("chunk_type") if meta.get("chunk_type") in {"text", "list", "mixed"} else _chunk_type(content)
        out.append((content, context, ctype))
    return out


def chunk_section(section: Section, doc_meta: dict) -> list[tuple[str, str, str]]:
    """Chia một section → [(content, context, chunk_type)]. LLM khi đáng, fallback rule-based."""
    blocks = split_into_khoan_blocks(section.text)
    use_llm = (
        settings.chunk_llm_enabled
        and len(blocks) > 1
        and count_tokens(section.text) > settings.chunk_llm_min_tokens
    )
    if use_llm:
        try:
            return _llm_group(section, blocks, doc_meta)
        except Exception:  # noqa: BLE001 — mọi lỗi LLM/parse/phân hoạch → fallback an toàn
            logger.warning(
                "LLM chunker fallback rule-based (section: %s).",
                " > ".join(section.heading_path) or "(đầu văn bản)",
            )
    # Rule-based: gộp block theo ngưỡng mềm, context xác định từ heading.
    return [
        (ct, _heading_context(section.heading_path, doc_meta), _chunk_type(ct))
        for ct in _merge_blocks(blocks)
    ]


# ---------------------------------------------------------------------------
# Bảng → markdown
# ---------------------------------------------------------------------------
def table_to_markdown(table: Table) -> str:
    """Chuyển lưới bảng thành markdown. Ô None→"" ; xuống dòng trong ô → khoảng trắng."""

    def cell(c: str | None) -> str:
        return (c or "").replace("\n", " ").replace("|", "\\|").strip()

    rows = [r for r in table if any((c or "").strip() for c in r)]
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [[cell(r[i]) if i < len(r) else "" for i in range(width)] for r in rows]
    header = "| " + " | ".join(norm[0]) + " |"
    sep = "| " + " | ".join(["---"] * width) + " |"
    body = ["| " + " | ".join(r) + " |" for r in norm[1:]]
    return "\n".join([header, sep, *body])


# ---------------------------------------------------------------------------
# Dựng TextNode
# ---------------------------------------------------------------------------
def _doc_ref_id(document_id: int) -> str:
    """UUID xác định theo tài liệu, dùng làm ``ref_doc_id`` (SOURCE) cho mọi chunk của tài liệu.

    BẮT BUỘC: WeaviateVectorStore của LlamaIndex map ``ref_doc_id`` sang property ``doc_id`` và
    ``document_id`` (kiểu UUID trong collection). Node tạo trực tiếp mà không có SOURCE → ref_doc_id
    = None → Weaviate từ chối (UUID không nhận None). Gán UUID5 ổn định theo id tài liệu để vừa hợp
    lệ, vừa gom chunk theo tài liệu (hỗ trợ xoá theo ref)."""
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
) -> ChunkNode:
    text = f"{context}\n\n{content}" if context else content
    metadata: dict[str, object] = {
        "document_id": document_id,
        "filename": filename,
        "doc_name": doc_meta.get("doc_name"),
        "doc_type": doc_meta.get("doc_type"),
        "issued_date": doc_meta.get("issued_date"),
        "issuing_body": doc_meta.get("issuing_body"),
        "heading_path": " > ".join(heading_path),
        "chunk_type": chunk_type,
        "has_table": has_table,
        "page_number": page_number,
    }
    node = TextNode(text=text, metadata=metadata)
    # ref_doc_id hợp lệ (UUID) → tránh lỗi UUID None khi ghi Weaviate (xem _doc_ref_id).
    node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
        node_id=_doc_ref_id(document_id)
    )
    # Embedding/BM25 = node.text (đã có context). Metadata chỉ để lưu/lọc/trích dẫn → loại khỏi
    # cả embed lẫn LLM để không nhiễu vector và không lộ vào câu trả lời.
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
    )


def build_nodes(
    pages: list[PageBlock],
    document_id: int,
    filename: str | None = None,
    doc_meta: dict | None = None,
) -> list[ChunkNode]:
    """Ráp toàn bộ chunk (text + bảng) từ các trang PDF đã trích xuất.

    Bọc trong span Phoenix ``rag.ingest.chunk`` để đối chiếu trace các call LLM chunking."""
    doc_meta = dict(doc_meta or {})
    doc_meta.setdefault("filename", filename)
    doc_meta.setdefault("doc_name", doc_meta.get("doc_name") or filename)

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("rag.ingest.chunk") as span:
        span.set_attribute("rag.ingest.document_id", document_id)
        span.set_attribute("rag.ingest.pages", len(pages))

        out: list[ChunkNode] = []
        sections = segment(pages)

        # 1) Chunk text theo section.
        for section in sections:
            for content, context, ctype in chunk_section(section, doc_meta):
                if not content.strip():
                    continue
                out.append(
                    _make_node(
                        content=content,
                        context=context,
                        document_id=document_id,
                        filename=filename,
                        doc_meta=doc_meta,
                        heading_path=section.heading_path,
                        chunk_type=ctype,
                        has_table=False,
                        page_number=section.page_number,
                    )
                )

        # 2) Bảng → node độc lập (không qua LLM), heading_path suy từ trang.
        for page in pages:
            hp = heading_path_for_page(sections, page.page_number)
            for table in page.tables:
                md = table_to_markdown(table)
                if not md.strip():
                    continue
                ctx = _heading_context(hp, doc_meta, extra="Dữ liệu dạng bảng.")
                out.append(
                    _make_node(
                        content=md,
                        context=ctx,
                        document_id=document_id,
                        filename=filename,
                        doc_meta=doc_meta,
                        heading_path=hp,
                        chunk_type="table",
                        has_table=True,
                        page_number=page.page_number,
                    )
                )

        span.set_attribute("rag.ingest.chunks", len(out))
        return out
