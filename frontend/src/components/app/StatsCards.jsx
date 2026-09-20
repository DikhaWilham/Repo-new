import { Card, CardContent } from "@/components/ui/card";
import { FileText, CheckCircle2, AlarmClock, XCircle, Ruler, Wallet } from "lucide-react";
import { formatRupiah } from "@/lib/format";

const ITEMS = [
  { key: "total", label: "Total Kontrak", icon: FileText, cls: "text-slate-900 bg-slate-100" },
  { key: "aktif", label: "Kontrak Aktif", icon: CheckCircle2, cls: "text-emerald-600 bg-emerald-50" },
  { key: "hampir_berakhir", label: "Hampir Berakhir", icon: AlarmClock, cls: "text-amber-600 bg-amber-50" },
  { key: "berakhir", label: "Kontrak Berakhir", icon: XCircle, cls: "text-rose-600 bg-rose-50" },
];

export default function StatsCards({ stats }) {
  if (!stats) return null;
  return (
    <div data-testid="stats-overview" className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {ITEMS.map(({ key, label, icon: Icon, cls }) => (
          <Card key={key} data-testid={`stat-card-${key}`} className="border-slate-200 shadow-sm">
            <CardContent className="flex items-center gap-4 p-5">
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${cls}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-slate-500">{label}</p>
                <p data-testid={`stat-value-${key}`} className="font-data text-2xl font-semibold text-slate-900">{stats[key]}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="flex items-center gap-4 p-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Ruler className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Total Luasan Disewa</p>
              <p data-testid="stat-total-luasan" className="font-data text-lg font-semibold text-slate-900">
                {Number(stats.total_luasan).toLocaleString("id-ID")} m²
              </p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="flex items-center gap-4 p-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Wallet className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500">Total Service Charge / Bulan</p>
              <p data-testid="stat-total-service-charge" className="font-data text-lg font-semibold text-slate-900">
                {formatRupiah(stats.total_service_charge)}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
