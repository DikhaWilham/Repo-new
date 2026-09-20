import { AlarmClock } from "lucide-react";
import { formatTanggal } from "@/lib/format";

export default function ReminderBanner({ stats, onOpenDetail }) {
  const list = stats?.hampir_berakhir_list || [];
  if (list.length === 0) return null;
  return (
    <div data-testid="reminder-banner" className="rounded-lg border border-amber-200 bg-amber-50 p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
          <AlarmClock className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-headline text-sm font-semibold text-amber-900">
            {list.length} kontrak memasuki masa reminder
          </h3>
          <p className="mt-0.5 text-xs text-amber-700">Segera tindaklanjuti perpanjangan atau pengakhiran sewa counter berikut.</p>
          <ul className="mt-3 space-y-2">
            {list.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <button
                  data-testid={`reminder-item-${item.id}`}
                  onClick={() => onOpenDetail(item.id)}
                  className="font-medium text-amber-900 underline decoration-amber-300 underline-offset-2 hover:text-amber-700"
                >
                  {item.nama_counter}
                </button>
                <span className="text-xs text-amber-700">
                  {item.nama_brand} · berakhir {formatTanggal(item.tanggal_akhir)} ·{" "}
                  <span className={`font-data font-semibold ${item.status === "reminder_3_bulan" ? "text-emerald-700" : "text-amber-800"}`}>
                    {item.hari_tersisa} hari lagi
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
