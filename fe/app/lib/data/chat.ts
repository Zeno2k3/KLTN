import type { Convo } from "@/app/types/chat";

/** Dữ liệu tĩnh cho trang chat (kịch bản trả lời mẫu + cuộc trò chuyện seed). */

export const SCRIPTED: Record<string, string> = {
  "Điều kiện nhập học": "Để vào lớp 1, bé cần đủ 6 tuổi tính theo năm (sinh năm 2020 cho năm học 2026–2027) ạ. Ba mẹ chỉ cần giấy khai sinh và sổ hộ khẩu/giấy tạm trú là đủ điều kiện nộp hồ sơ rồi nhé! 🎒",
  "Hồ sơ cần chuẩn bị": "Hồ sơ tuyển sinh lớp 1 gồm: (1) Đơn đăng ký, (2) Bản sao giấy khai sinh, (3) Sổ hộ khẩu hoặc giấy tạm trú. Một số trường cần thêm 2 ảnh 3×4. Ba mẹ muốn mình gửi mẫu đơn không ạ?",
  "Học phí 2026": "Học phí khối tiểu học dao động khá rộng tuỳ trường: trường công thường rất thấp, trường tư từ 3–15 triệu/tháng. Ba mẹ cho mình biết khu vực và ngân sách mong muốn, mình gợi ý trường phù hợp nhé.",
  "Đặt lịch tham quan": "Tuyệt vời! Nhiều trường mở cửa tham quan vào Thứ 7 hàng tuần. Ba mẹ muốn tham quan ở khu vực nào và khoảng thời gian nào ạ? Mình sẽ giúp đặt lịch và nhắc qua Zalo.",
};

export const DEFAULT_REPLY = "Cảm ơn ba mẹ đã chia sẻ! Mình đã ghi nhận. Ba mẹ có thể chọn một trong các chủ đề bên dưới, hoặc nhắn câu hỏi cụ thể để mình tư vấn kỹ hơn nhé. 💬";

export const TOPICS = ["Điều kiện nhập học", "Hồ sơ cần chuẩn bị", "Học phí 2026", "Đặt lịch tham quan"];

export const USER_NAME = "chị Hồng Nhung";

export const SEED: Convo[] = [
  { id: "c1", title: "Tuyển sinh lớp 1 Q.7", time: "09:24", tint: "var(--brand-subtle)", fg: "var(--brand-strong)", messages: [
    { from: "bot", text: "Chào ba mẹ! Mình là LuminaAi 👋 Mình hỗ trợ tư vấn tuyển sinh lớp 1. Mình giúp gì cho bé nhà mình ạ?", time: "09:20" },
    { from: "user", text: "Bé nhà mình sinh năm 2020 ạ", time: "09:21" },
    { from: "bot", text: "Dạ bé sinh 2020 năm nay vừa đủ 6 tuổi, đúng độ tuổi vào lớp 1 ạ! Ba mẹ muốn tìm trường gần khu vực nào để mình gợi ý nhé? 🎒", time: "09:21" },
    { from: "user", text: "Khu vực Quận 7 ạ", time: "09:23" },
    { from: "bot", text: "Quận 7 có nhiều trường tốt như TH Nguyễn Thị Định, Vinschool Central Park, Quốc tế Á Châu… Ba mẹ cho mình biết ngân sách học phí mong muốn, mình lọc giúp ạ.", time: "09:24" },
  ] },
  { id: "c2", title: "Hồ sơ nhập học", time: "Hôm qua", tint: "var(--sun-50)", fg: "var(--sun-600)", messages: [
    { from: "user", text: "Hồ sơ cần chuẩn bị gồm những gì ạ?", time: "20:10" },
    { from: "bot", text: "Hồ sơ tuyển sinh lớp 1 gồm: (1) Đơn đăng ký, (2) Bản sao giấy khai sinh, (3) Sổ hộ khẩu hoặc giấy tạm trú. Một số trường cần thêm 2 ảnh 3×4 ạ.", time: "20:10" },
    { from: "user", text: "Cho mình xin mẫu đơn với ạ", time: "20:12" },
    { from: "bot", text: "Dạ mình gửi ba mẹ mẫu Đơn đăng ký tuyển sinh lớp 1 qua Zalo nhé. Ba mẹ chỉ cần điền thông tin bé và ký tên là xong ạ. ✅", time: "20:12" },
  ] },
  { id: "c3", title: "Học phí trường tư", time: "T4", tint: "var(--sky-50)", fg: "var(--sky-600)", messages: [
    { from: "user", text: "Học phí trường tư khoảng bao nhiêu ạ?", time: "15:30" },
    { from: "bot", text: "Học phí khối tiểu học trường tư dao động khá rộng, thường từ 3–15 triệu/tháng tuỳ trường và chương trình. Ba mẹ cho mình biết ngân sách mong muốn, mình gợi ý trường phù hợp nhé.", time: "15:30" },
  ] },
  { id: "c4", title: "Lịch tham quan Wellspring", time: "T2", tint: "var(--ink-100)", fg: "var(--text-muted)", messages: [
    { from: "user", text: "Mình muốn đặt lịch tham quan trường", time: "10:02" },
    { from: "bot", text: "Tuyệt vời! Nhiều trường mở cửa tham quan vào Thứ 7 hàng tuần. Ba mẹ muốn tham quan trường nào và khoảng thời gian nào ạ?", time: "10:02" },
    { from: "user", text: "Wellspring Saigon, sáng Thứ 7 này", time: "10:05" },
    { from: "bot", text: "Dạ mình đã đặt lịch tham quan Wellspring Saigon lúc 9h sáng Thứ 7 này cho ba mẹ. Mình sẽ nhắc lại qua Zalo trước 1 ngày nhé! 📅", time: "10:05" },
  ] },
  { id: "c5", title: "Tuyển sinh trái tuyến", time: "12/6", tint: "var(--ink-100)", fg: "var(--text-muted)", messages: [
    { from: "user", text: "Bé học trái tuyến có được không ạ?", time: "09:00" },
    { from: "bot", text: "Dạ được ạ. Tuyển sinh trái tuyến phụ thuộc chỉ tiêu còn lại của trường sau khi nhận đúng tuyến. Ba mẹ nên nộp đơn sớm và chuẩn bị giấy tạm trú nếu có. Mình hướng dẫn chi tiết từng bước nhé.", time: "09:01" },
  ] },
];
