"""Hạ tầng RAG: vector store (Weaviate) + ingest (trích xuất/chunk PDF).

Tách riêng khỏi services/ để cô lập phần phụ thuộc nặng (LlamaIndex/Weaviate/OpenAI)
và rủi ro hồi quy — mọi thay đổi ở đây kích hoạt skill ``rag-eval``.
"""
