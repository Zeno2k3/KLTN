/** Dữ liệu tĩnh cho trang chat: gợi ý chủ đề (gửi như câu hỏi thật) + tên mặc định.
 *
 * Lưu ý: dữ liệu giả lập trước đây (SCRIPTED / DEFAULT_REPLY / SEED) đã bỏ — chat nay gọi
 * backend RAG thật qua ``chatApi`` trong [hooks/useChat.ts].
 */

export const TOPICS = [
  "Điều kiện nhập học",
  "Hồ sơ cần chuẩn bị",
  "Học phí 2026",
  "Đặt lịch tham quan",
];

/** Tên mặc định trong lời chào khi chưa lấy được tên người dùng. */
export const USER_NAME = "bạn";
