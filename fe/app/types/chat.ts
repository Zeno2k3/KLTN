// --- Mô hình dùng trong UI ---

/** Nguồn trích dẫn (chunk tài liệu) hiển thị dưới câu trả lời của AI. */
export type Source = {
  index: number | null;
  document_id: number | null;
  filename: string | null;
  /** UUID chunk trong Weaviate — khớp `DocumentChunk.weaviate_uuid` để tô sáng đúng đoạn trong drawer. */
  weaviate_uuid: string | null;
  snippet: string | null;
  score: number | null;
};

export type Msg = {
  from: "bot" | "user";
  text: string;
  time: string;
  sources?: Source[];
};

export type Convo = {
  id: string; // khoá UI ổn định (chuỗi)
  serverId: number | null; // id hội thoại ở backend (null = chat mới chưa gửi)
  title: string;
  time: string;
  tint: string;
  fg: string;
  messages: Msg[];
  loaded: boolean; // đã nạp tin nhắn từ server chưa (lazy-load khi mở)
  preview?: string; // snippet tin cuối (cho sidebar trước khi nạp messages)
};

// --- DTO khớp backend (/api/v1/chat/*) ---

export type SourceDTO = {
  index: number | null;
  document_id: number | null;
  filename: string | null;
  weaviate_uuid: string | null;
  snippet: string | null;
  score: number | null;
};

export type AskResponseDTO = {
  conversation_id: number;
  answer: string;
  sources: SourceDTO[];
};

export type ConversationSummaryDTO = {
  id: number;
  title: string;
  updated_at: string; // ISO
  last_message: string | null;
};

export type MessageDTO = {
  id: number;
  sender_type: "user" | "assistant";
  content: string;
  sources: SourceDTO[];
  created_at: string; // ISO
};

export type ConversationDetailDTO = {
  id: number;
  title: string;
  messages: MessageDTO[];
};

/** Một đoạn text của tài liệu (cho bảng trích dẫn). */
export type DocumentChunkDTO = {
  chunk_index: number;
  content: string;
  weaviate_uuid: string | null;
};

/** Tài liệu + toàn bộ đoạn text — trả từ GET /chat/documents/{id}. */
export type DocumentDetailDTO = {
  id: number;
  filename: string;
  page_count: number | null;
  chunk_count: number;
  chunks: DocumentChunkDTO[];
};
