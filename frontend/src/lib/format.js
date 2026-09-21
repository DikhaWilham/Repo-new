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
  reminder_3_bulan: "Reminder 3 Bulan",
  hampir_berakhir: "Hampir Berakhir",
  berakhir: "Berakhir",
};

export const PROGRES_MOU_OPTIONS = [
  { value: "proses_mou", label: "Proses MOU" },
  { value: "mou_ditandatangani", label: "MOU Ditandatangani" },
  { value: "proses_fit_out", label: "Proses Fit Out / Renovasi" },
  { value: "akan_buka", label: "Akan Buka" },
  { value: "sudah_beroperasi", label: "Sudah Beroperasi" },
];

export const PROGRES_MOU_LABEL = Object.fromEntries(PROGRES_MOU_OPTIONS.map((o) => [o.value, o.label]));
