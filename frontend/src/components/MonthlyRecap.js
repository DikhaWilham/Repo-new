import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LabelList } from "recharts";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { BarChart3, Loader2 } from "lucide-react";

function monthOptions() {
  const opts = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const label = d.toLocaleDateString("id-ID", { month: "long", year: "numeric" });
    opts.push({ val, label });
  }
  return opts;
}

export default function MonthlyRecap() {
  const options = monthOptions();
  const [month, setMonth] = useState(options[0].val);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (m) => {
    setLoading(true);
    try {
      const { data } = await api.get("/overtime/monthly-recap", { params: { month: m } });
      setData(data);
    } catch (e) {
      toast.error("Gagal memuat rekap bulanan");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(month); }, [month, load]);

  const chartData = (data?.employees || []).map((e) => ({ name: e.employee_name, Jam: e.total_hours }));

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 sm:p-6" data-testid="monthly-recap">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 flex items-center justify-center">
            <BarChart3 className="h-4 w-4 text-indigo-600" />
          </div>
          <div>
            <h2 className="text-lg font-heading font-semibold tracking-tight text-slate-800 dark:text-slate-100">Rekap Bulanan</h2>
            <p className="text-xs text-slate-500">Total jam lembur per karyawan</p>
          </div>
        </div>
        <Select value={month} onValueChange={setMonth}>
          <SelectTrigger className="w-full sm:w-[190px]" data-testid="select-recap-month"><SelectValue /></SelectTrigger>
          <SelectContent>
            {options.map((o) => <SelectItem key={o.val} value={o.val}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="flex justify-center py-14"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
      ) : !data || data.employees.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-14">Tidak ada data lembur pada bulan ini.</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 text-center">
              <p className="text-lg font-heading font-bold text-slate-900 dark:text-white font-mono">{data.grand_total_label}</p>
              <p className="text-xs text-slate-500">Total Jam Lembur</p>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 text-center">
              <p className="text-lg font-heading font-bold text-slate-900 dark:text-white font-mono">{data.total_employees}</p>
              <p className="text-xs text-slate-500">Karyawan Lembur</p>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3 text-center">
              <p className="text-lg font-heading font-bold text-slate-900 dark:text-white font-mono">{data.total_records}</p>
              <p className="text-xs text-slate-500">Total Rekap</p>
            </div>
          </div>

          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148,163,184,0.2)" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} interval={0} angle={chartData.length > 3 ? -20 : 0} textAnchor={chartData.length > 3 ? "end" : "middle"} height={60} />
                <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} axisLine={false} unit="j" width={50} />
                <Tooltip
                  cursor={{ fill: "rgba(37,99,235,0.06)" }}
                  contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 13 }}
                  formatter={(v) => [`${v} jam`, "Total"]}
                />
                <Bar dataKey="Jam" fill="#2563EB" radius={[6, 6, 0, 0]} maxBarSize={56}>
                  <LabelList dataKey="Jam" position="top" formatter={(v) => `${v}j`} style={{ fontSize: 11, fill: "#475569", fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 divide-y divide-slate-100 dark:divide-slate-800">
            {data.employees.map((e, i) => (
              <div key={e.employee_id} className="flex items-center justify-between py-2.5" data-testid={`recap-row-${e.employee_id}`}>
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono text-slate-400 w-5">{i + 1}.</span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{e.employee_name}</p>
                    <p className="text-xs text-slate-400">{e.count} rekap · {e.with_photo} ada foto</p>
                  </div>
                </div>
                <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400 shrink-0">{e.total_label}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
