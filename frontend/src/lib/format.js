import { format, parseISO } from "date-fns";
import { id as localeId } from "date-fns/locale";

export function formatTanggal(iso) {
  if (!iso) return "-";
  try {
    return format(parseISO(iso), "d MMM yyyy", { locale: localeId });
  } catch {
    return iso;
  }
}

export function formatRupiah(value) {
  const num = Number(value) || 0;
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(num);
}

export const SKEMA_LABEL = {
  sewa: "Sewa",
  bagi_hasil: "Bagi Hasil",
  hybrid: "Hybrid",
};

export const STATUS_LABEL = {
  aktif: "Aktif",
  hampir_berakhir: "Hampir Berakhir",
  berakhir: "Berakhir",
};
