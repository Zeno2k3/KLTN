import type { ReactNode } from "react";

/** Dữ liệu tĩnh cho trang landing. */

export const PARTNERS = [
  { name: "Vinschool", initial: "V" },
  { name: "Hệ thống EMASI", initial: "E" },
  { name: "TH Lê Quý Đôn", initial: "LQ" },
  { name: "Quốc tế Á Châu", initial: "ÁC" },
  { name: "Wellspring Saigon", initial: "W" },
  { name: "TH Nguyễn Bỉnh Khiêm", initial: "NBK" },
  { name: "TH Kim Đồng", initial: "KĐ" },
  { name: "Sở GD&ĐT TP.HCM", initial: "GD" },
];

export const REVIEWS = [
  { name: "Chị Hồng Nhung", area: "Phụ huynh bé Bốp · Quận 7", initial: "HN", color: "var(--teal-400)", quote: "Lần đầu cho con vào lớp 1 mình rất lo, LuminaAi giải thích từng bước rõ ràng và nhẹ nhàng. Yên tâm hẳn." },
  { name: "Anh Minh Tuấn", area: "Phụ huynh bé Su · TP. Thủ Đức", initial: "MT", color: "var(--sky-400)", quote: "Hỏi lúc nửa đêm vẫn được trả lời ngay. Tiết kiệm bao nhiêu thời gian gọi tổng đài tuyển sinh." },
  { name: "Chị Thu Hà", area: "Phụ huynh bé Nhím · Bình Thạnh", initial: "TH", color: "var(--sun-400)", quote: "Được gợi ý 3 trường gần nhà đúng tầm học phí, lại còn đặt lịch tham quan giúp mình luôn." },
  { name: "Chị Lan Anh", area: "Phụ huynh bé Kem · Gò Vấp", initial: "LA", color: "var(--teal-500)", quote: "Danh sách hồ sơ rất chi tiết, mình chuẩn bị đầy đủ không thiếu một loại giấy tờ nào." },
  { name: "Anh Đức Thành", area: "Phụ huynh bé Bin · Quận 1", initial: "ĐT", color: "var(--sky-500)", quote: "Giao diện dễ thương, con mình mê cái robot. Tư vấn nhiệt tình mà lại hoàn toàn miễn phí." },
  { name: "Chị Phương Mai", area: "Phụ huynh bé Na · Tân Bình", initial: "PM", color: "var(--sun-500)", quote: "Mình hỏi về tuyển sinh trái tuyến, LuminaAi hướng dẫn cặn kẽ và rất trung thực. Cảm ơn nhiều!" },
];

export const STATS = [
  { value: "12.000+", label: "ba mẹ đã được hỗ trợ", color: "var(--brand)" },
  { value: "350+", label: "trường tiểu học trong dữ liệu", color: "var(--accent)" },
  { value: "50.000+", label: "câu hỏi đã được giải đáp", color: "var(--sky-500)" },
  { value: "24/7", label: "luôn sẵn sàng trả lời", color: "var(--brand)" },
];

export const AVATARS = [
  { initials: "AN", bg: "var(--teal-400)" },
  { initials: "BÌ", bg: "var(--sky-400)" },
  { initials: "CH", bg: "var(--sun-400)" },
  { initials: "DU", bg: "var(--teal-500)" },
];

type Feature = { tint: string; fg: string; title: string; body: string; icon: ReactNode };

export const FEATURES: Feature[] = [
  {
    tint: "var(--teal-50)", fg: "var(--brand)", title: "Hỏi đáp tức thì",
    body: "Trả lời ngay mọi câu hỏi về tuyển sinh, không cần chờ tổng đài hay xếp hàng.",
    icon: <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />,
  },
  {
    tint: "var(--sun-50)", fg: "var(--accent)", title: "Gợi ý trường phù hợp",
    body: "Đề xuất trường theo khu vực, học phí và mong muốn riêng của từng gia đình.",
    icon: <><path d="M22 10 12 5 2 10l10 5 10-5Z" /><path d="M6 12v5c0 1.4 2.7 3 6 3s6-1.6 6-3v-5" /></>,
  },
  {
    tint: "var(--sky-50)", fg: "var(--sky-500)", title: "Hướng dẫn hồ sơ",
    body: "Danh sách giấy tờ cần chuẩn bị và mẫu đơn, hướng dẫn từng bước rõ ràng.",
    icon: <><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" /><rect x="9" y="3" width="6" height="4" rx="1" /><path d="m9 14 2 2 4-4" /></>,
  },
  {
    tint: "var(--teal-50)", fg: "var(--brand)", title: "Đặt lịch tham quan",
    body: "Chọn lịch tham quan trường và nhận nhắc nhở nhẹ nhàng qua Zalo.",
    icon: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /><path d="m9 16 2 2 4-4" /></>,
  },
];

type Step = { n: string; numColor: string; bg: string; title: string; body: string; icon: ReactNode };

export const STEPS: Step[] = [
  {
    n: "01", numColor: "var(--teal-100)", bg: "var(--brand)", title: "Đặt câu hỏi",
    body: "Nhắn cho LuminaAi bất cứ điều gì về tuyển sinh lớp 1 — bằng tiếng Việt, tự nhiên như trò chuyện.",
    icon: <><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M8 9h8M8 13h5" /></>,
  },
  {
    n: "02", numColor: "var(--sun-100)", bg: "var(--accent)", title: "Cá nhân hóa tư vấn",
    body: "LuminaAi gợi ý trường, giải thích hồ sơ và học phí phù hợp với khu vực và mong muốn của gia đình.",
    icon: <><path d="M15 14c.2-1 .7-1.7 1.5-2.5A4.5 4.5 0 1 0 7.5 11.5c.8.8 1.3 1.5 1.5 2.5" /><path d="M9 18h6M10 22h4" /></>,
  },
  {
    n: "03", numColor: "var(--sky-100)", bg: "var(--sky-500)", title: "Đặt lịch & đăng ký",
    body: "Đặt lịch tham quan và hoàn tất hồ sơ đăng ký ngay trong vài phút, có nhắc nhở qua Zalo.",
    icon: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /><path d="m9 16 2 2 4-4" /></>,
  },
];
