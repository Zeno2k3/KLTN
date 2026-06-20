---
name: rag-eval
description: Evaluate retrieval and answer quality after changing the RAG pipeline. Use whenever you modify chunking, embeddings, the retriever, the vector index, the system prompt, or any LlamaIndex, Weaviate, or OpenAI configuration in the backend.
---

# Đánh giá RAG sau khi thay đổi pipeline

Thay đổi pipeline RAG có thể làm giảm chất lượng mà unit test KHÔNG bắt được.
Một thay đổi chỉ được coi là "hoạt động" sau khi có số liệu đánh giá chứng minh.

## Yêu cầu cài đặt (nếu chưa có)

- RAGAS: `pip install ragas`
- Phoenix: `pip install arize-phoenix openinference-instrumentation-llama-index`
  (LlamaIndex đã có sẵn llama-index-instrumentation để Phoenix móc vào.)

## Các bước

1. Xác định rõ bạn đã đổi gì: chunking / embedding / retriever / index / prompt.
2. Chạy RAGAS trên tập câu hỏi mẫu — tối thiểu: faithfulness, answer relevancy,
   context precision, context recall.
3. So sánh với baseline (số liệu trước thay đổi). Nếu chỉ số giảm đáng kể → CHƯA xong.
4. Mở trace trong Arize Phoenix: xác nhận retriever trả về đúng ngữ cảnh, không có
   span lỗi, độ trễ chấp nhận được.
5. Đính kèm bảng số liệu RAGAS + ảnh/đường dẫn trace Phoenix làm bằng chứng.

## Quy tắc

- Không báo "đã cải thiện retrieval / câu trả lời" nếu chưa có số RAGAS chứng minh.
- Nếu faithfulness thấp → mô hình đang bịa; ưu tiên sửa trước khi làm việc khác.
