import { Clock, Users, CalendarDays, Camera } from "lucide-react";

const CARDS = [
  { key: "total_month_label", label: "Total Lembur Bulan Ini", icon: Clock, color: "text-blue-600", bg: "bg-blue-50 dark:bg-blue-950/40" },
  { key: "employees_month", label: "Karyawan Lembur (Bulan Ini)", icon: Users, color: "text-emerald-600", bg: "bg-emerald-50 dark:bg-emerald-950/40" },
  { key: "today_count", label: "Rekap Hari Ini", icon: CalendarDays, color: "text-amber-600", bg: "bg-amber-50 dark:bg-amber-950/40" },
  { key: "with_photo", label: "Sudah Ada Foto", icon: Camera, color: "text-sky-600", bg: "bg-sky-50 dark:bg-sky-950/40" },
];

export default function StatsCards({ stats }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6" data-testid="stats-cards">
      {CARDS.map(({ key, label, icon: Icon, color, bg }) => (
        <div key={key} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 sm:p-5">
          <div className="flex items-center justify-between mb-3">
            <div className={`h-9 w-9 rounded-lg ${bg} flex items-center justify-center`}>
              <Icon className={`h-4 w-4 ${color}`} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-heading font-bold tracking-tight text-slate-900 dark:text-white">
            {stats ? stats[key] ?? "-" : "…"}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-snug">{label}</p>
        </div>
      ))}
    </div>
  );
}
