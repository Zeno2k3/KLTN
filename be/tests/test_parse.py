"""Test app/rag/parse.py — chuẩn hóa item LlamaParse + guard. Offline (không gọi mạng thật).

Đường THÀNH CÔNG (gọi REST LlamaParse) được nghiệm thu bằng chạy THẬT (xem PROGRESS/skill rag-eval);
ở đây chỉ test: chuẩn hóa item (hàm thuần), map kết quả, và các nhánh lỗi/thiếu-key (không-mạng)."""

import httpx
import pytest

from app.rag import parse
from app.rag.parse import ParsedPage


# --- _to_block: hàm thuần, dữ liệu thật ---
def test_to_block_text():
    b = parse._to_block({"type": "text", "md": "- Điểm a", "value": "- Điểm a"})
    assert b.type == "text"
    assert b.md == "- Điểm a"
    assert b.rows is None


def test_to_block_heading_keeps_level():
    b = parse._to_block(
        {"type": "heading", "md": "# Điều 5", "value": "Điều 5", "lvl": 2}
    )
    assert b.type == "heading"
    assert b.level == 2
    assert b.value == "Điều 5"


def test_to_block_table_rows_to_grid_empty_to_none():
    item = {"type": "table", "md": "| a | b |", "rows": [["a", ""], ["", "b"]]}
    b = parse._to_block(item)
    assert b.type == "table"
    assert b.rows == [["a", None], [None, "b"]]  # "" → None khớp kiểu Table


def test_to_block_skips_unknown_and_empty():
    assert parse._to_block({"type": "image"}) is None
    assert parse._to_block({"type": "text", "md": "", "value": ""}) is None


# --- _fetch_pages: map JSON kết quả → ParsedPage (client giả, không mạng) ---
class _Resp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _Client:
    def __init__(self, data):
        self._data = data

    def get(self, url, headers=None):
        return _Resp(self._data)


def test_fetch_pages_maps_pages_and_blocks():
    data = {
        "pages": [
            {
                "page": 1,
                "md": "trang 1",
                "items": [
                    {"type": "heading", "md": "# A", "value": "A", "lvl": 1},
                    {"type": "text", "md": "nội dung", "value": "nội dung"},
                ],
            },
            {"page": 2, "md": "trang 2", "items": []},
        ]
    }
    pages = parse._fetch_pages(_Client(data), "job-id")
    assert [p.page_number for p in pages] == [1, 2]
    assert pages[0].md == "trang 1"
    assert [b.type for b in pages[0].blocks] == ["heading", "text"]
    assert pages[1].blocks == []


# --- parse_document: guard + orchestration (mock các bước mạng) ---
def test_parse_document_missing_key_raises(monkeypatch):
    monkeypatch.setattr(parse.settings, "llama_cloud_api_key", "")
    with pytest.raises(RuntimeError):
        parse.parse_document("x.pdf")


def test_parse_document_empty_result_raises(monkeypatch):
    monkeypatch.setattr(parse.settings, "llama_cloud_api_key", "k")
    monkeypatch.setattr(parse, "_upload", lambda c, p: "job")
    monkeypatch.setattr(parse, "_wait", lambda c, j: "SUCCESS")
    monkeypatch.setattr(parse, "_fetch_pages", lambda c, j: [])
    with pytest.raises(ValueError):
        parse.parse_document("x.pdf")


def test_parse_document_success(monkeypatch):
    monkeypatch.setattr(parse.settings, "llama_cloud_api_key", "k")
    pages = [ParsedPage(page_number=1, md="nội dung", blocks=[])]
    monkeypatch.setattr(parse, "_upload", lambda c, p: "job")
    monkeypatch.setattr(parse, "_wait", lambda c, j: "SUCCESS")
    monkeypatch.setattr(parse, "_fetch_pages", lambda c, j: pages)
    assert parse.parse_document("x.pdf") == pages


# --- _request_with_retry: lỗi transient (499/5xx) thử lại; 4xx khác fail ngay ---
def _resp(code: int, body: dict | None = None) -> httpx.Response:
    """httpx.Response thật: raise_for_status() ném HTTPStatusError đúng cho 4xx/5xx (gồm 499)."""
    req = httpx.Request("POST", "https://api.cloud.llamaindex.ai/api/v1/parsing/upload")
    return httpx.Response(code, json=(body or {}), request=req)


class _UploadClient:
    """Client giả: trả lần lượt các status code; đọc file mỗi lần để bắt lỗi handle đã đóng."""

    def __init__(self, statuses: list[int]):
        self._statuses = list(statuses)
        self.post_calls = 0
        self.last_data: dict | None = None

    def post(self, url, headers=None, files=None, data=None):
        self.post_calls += 1
        self.last_data = data  # giữ form fields để assert parse_mode/language
        files["file"][
            1
        ].read()  # nếu file không được mở lại mỗi lần → đọc rỗng (proxy lỗi resume)
        return _resp(self._statuses.pop(0), {"id": "job-xyz"})


def test_upload_retries_on_499_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(parse.time, "sleep", lambda *_: None)  # không chờ backoff thật
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.7 noi dung")
    client = _UploadClient([499, 499, 200])  # hai lần 499 rồi 200
    job_id = parse._upload(client, str(f))
    assert job_id == "job-xyz"
    assert client.post_calls == 3  # đã thử lại đúng 3 lần (mở lại file mỗi lần)
    # parse_mode gửi lên đúng để ép vision (bỏ text-layer font lỗi → giữ dấu).
    assert client.last_data["parse_mode"] == parse.settings.llamaparse_parse_mode
    assert client.last_data["language"] == parse.settings.llamaparse_language


def test_upload_no_retry_on_400(tmp_path, monkeypatch):
    monkeypatch.setattr(parse.time, "sleep", lambda *_: None)
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.7 noi dung")
    client = _UploadClient([400])  # 4xx không-transient → raise NGAY
    with pytest.raises(httpx.HTTPStatusError):
        parse._upload(client, str(f))
    assert client.post_calls == 1  # KHÔNG thử lại


def test_upload_exhausts_retries_then_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(parse.time, "sleep", lambda *_: None)
    monkeypatch.setattr(parse.settings, "llamaparse_max_retries", 2)
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.7 noi dung")
    client = _UploadClient([499, 499, 499])  # luôn 499 → hết lượt thử → raise
    with pytest.raises(httpx.HTTPStatusError):
        parse._upload(client, str(f))
    assert client.post_calls == 3  # 1 lần đầu + 2 lần thử lại
