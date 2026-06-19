/** Tiện ích thời gian dùng cho chat & admin. */

/** Giờ hiện tại dạng "HH:MM". */
export function now(): string {
  const d = new Date();
  return String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0");
}

/** Buổi trong ngày theo giờ hiện tại ("sáng" | "chiều" | "tối"). */
export function partOfDay(): string {
  const hour = new Date().getHours();
  return hour < 11 ? "sáng" : hour < 18 ? "chiều" : "tối";
}

/** Ngày hôm nay dạng "DD/MM/YYYY". */
export function todayDMY(): string {
  const today = new Date();
  return String(today.getDate()).padStart(2, "0") + "/" + String(today.getMonth() + 1).padStart(2, "0") + "/" + today.getFullYear();
}
