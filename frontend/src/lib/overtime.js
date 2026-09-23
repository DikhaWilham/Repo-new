export function minutesToLabel(minutes) {
  const m = Number(minutes) || 0;
  const h = Math.floor(m / 60);
  const min = m % 60;
  if (h && min) return `${h} Jam ${min} Menit`;
  if (h) return `${h} Jam`;
  return `${min} Menit`;
}

export function calcMinutes(start, end) {
  if (!start || !end) return 0;
  const [sh, sm] = start.split(":").map(Number);
  const [eh, em] = end.split(":").map(Number);
  if ([sh, sm, eh, em].some((n) => Number.isNaN(n))) return 0;
  let diff = eh * 60 + em - (sh * 60 + sm);
  if (diff < 0) diff += 24 * 60;
  return diff;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const DAYS = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

export function formatDate(dateStr) {
  if (!dateStr) return "-";
  const d = new Date(dateStr + "T00:00:00");
  if (Number.isNaN(d.getTime())) return dateStr;
  return `${DAYS[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
