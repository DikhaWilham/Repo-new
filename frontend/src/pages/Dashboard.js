import { useState, useEffect, useCallback } from "react";
import api, { API } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { formatDate } from "@/lib/overtime";
import HeaderNav from "@/components/HeaderNav";
import StatsCards from "@/components/StatsCards";
import MonthlyRecap from "@/components/MonthlyRecap";
import OvertimeEditModal from "@/components/OvertimeEditModal";
import OvertimeAddModal from "@/components/OvertimeAddModal";
import EmployeeManagementSheet from "@/components/EmployeeManagementSheet";
import PhotoPreviewModal from "@/components/PhotoPreviewModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { Plus, Search, FileSpreadsheet, FileDown, Pencil, Trash2, Camera, ImageOff, Loader2, Filter } from "lucide-react";

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const [records, setRecords] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const [filters, setFilters] = useState({ employee_id: "all", date_from: "", date_to: "", search: "" });

  const [editRecord, setEditRecord] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [empSheetOpen, setEmpSheetOpen] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const buildParams = useCallback(() => {
    const p = {};
    if (isAdmin && filters.employee_id !== "all") p.employee_id = filters.employee_id;
    if (filters.date_from) p.date_from = filters.date_from;
    if (filters.date_to) p.date_to = filters.date_to;
    if (filters.search) p.search = filters.search;
    return p;
  }, [filters, isAdmin]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [ot, st] = await Promise.all([
        api.get("/overtime", { params: buildParams() }),
        api.get("/stats"),
      ]);
      setRecords(ot.data);
      setStats(st.data);
    } catch (e) {
      toast.error("Gagal memuat data lembur");
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  const loadEmployees = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const { data } = await api.get("/employees");
      setEmployees(data);
    } catch (e) { /* ignore */ }
  }, [isAdmin]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadEmployees(); }, [loadEmployees]);

  const handleDelete = async () => {
    try {
      await api.delete(`/overtime/${deleteTarget.id}`);
      toast.success("Data lembur dihapus");
      setDeleteTarget(null);
      loadData();
    } catch (e) {
      toast.error("Gagal menghapus data");
    }
  };

  const handleExport = async (fmt) => {
    try {
      const { data } = await api.get("/overtime/export", { params: { ...buildParams(), fmt }, responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rekap_lembur.${fmt === "csv" ? "csv" : "xlsx"}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Berhasil mengunduh ${fmt === "csv" ? "CSV" : "Excel"}`);
    } catch (e) {
      toast.error("Gagal mengekspor data");
    }
  };

  const canEdit = (rec) => isAdmin || rec.employee_id === user.id;

  const StatusBadge = ({ rec }) =>
    rec.photo_path ? (
      <Badge variant="outline" className="text-emerald-700 border-emerald-200 bg-emerald-50 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800 gap-1">
        <Camera className="h-3 w-3" /> Ada Foto
      </Badge>
    ) : (
      <Badge variant="outline" className="text-slate-500 border-slate-200 gap-1">
        <ImageOff className="h-3 w-3" /> Belum
      </Badge>
    );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#090D16]">
      <HeaderNav onOpenEmployees={() => setEmpSheetOpen(true)} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl sm:text-3xl font-heading font-bold tracking-tight text-slate-900 dark:text-white">Rekap Lembur</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              {isAdmin ? "Kelola dan pantau lembur seluruh karyawan." : `Halo ${user.name}, ini daftar lembur Anda.`}
            </p>
          </div>
          {isAdmin && (
            <Button onClick={() => setAddOpen(true)} className="bg-blue-600 hover:bg-blue-700 text-white gap-2 shrink-0" data-testid="btn-open-add-overtime">
              <Plus className="h-4 w-4" /> Tambah Lembur
            </Button>
          )}
        </div>

        <StatsCards stats={stats} />

        {isAdmin && <MonthlyRecap />}

        {/* Filter bar */}
        <div className="flex flex-col lg:flex-row lg:items-end gap-3 p-4 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 text-slate-500 lg:hidden">
            <Filter className="h-4 w-4" /> <span className="text-sm font-medium">Filter</span>
          </div>
          {isAdmin && (
            <div className="flex-1 min-w-[160px] space-y-1">
              <label className="text-xs font-medium text-slate-500">Karyawan</label>
              <Select value={filters.employee_id} onValueChange={(v) => setFilters({ ...filters, employee_id: v })}>
                <SelectTrigger data-testid="filter-employee"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Semua Karyawan</SelectItem>
                  {employees.map((e) => <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="flex-1 min-w-[130px] space-y-1">
            <label className="text-xs font-medium text-slate-500">Dari Tanggal</label>
            <Input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} data-testid="input-date-from" />
          </div>
          <div className="flex-1 min-w-[130px] space-y-1">
            <label className="text-xs font-medium text-slate-500">Sampai Tanggal</label>
            <Input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} data-testid="input-date-to" />
          </div>
          <div className="flex-1 min-w-[160px] space-y-1">
            <label className="text-xs font-medium text-slate-500">Cari</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input placeholder="Keterangan / lokasi..." value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} className="pl-9" data-testid="input-search-overtime" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => handleExport("xlsx")} className="gap-2" data-testid="btn-export-excel">
              <FileSpreadsheet className="h-4 w-4 text-emerald-600" /> <span className="hidden sm:inline">Excel</span>
            </Button>
            <Button variant="outline" onClick={() => handleExport("csv")} className="gap-2" data-testid="btn-export-csv">
              <FileDown className="h-4 w-4 text-blue-600" /> <span className="hidden sm:inline">CSV</span>
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-slate-400" /></div>
        ) : records.length === 0 ? (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm py-20 text-center">
            <p className="text-slate-500">Belum ada data lembur.</p>
            {isAdmin && <p className="text-sm text-slate-400 mt-1">Klik "Tambah Lembur" untuk membuat rekap pertama.</p>}
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                      {["No", "Nama Karyawan", "Tanggal", "Mulai", "Akhir", "Total", "Lokasi / Hari", "Keterangan", "Foto", "Aksi"].map((h) => (
                        <th key={h} className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((rec, i) => (
                      <tr key={rec.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors" data-testid={`tr-overtime-row-${rec.id}`}>
                        <td className="px-4 py-3 text-sm text-slate-500 font-mono">{i + 1}</td>
                        <td className="px-4 py-3 text-sm font-semibold text-slate-800 dark:text-slate-100 whitespace-nowrap">{rec.employee_name}</td>
                        <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 whitespace-nowrap">{formatDate(rec.date)}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-700 dark:text-slate-200">{rec.start_time}</td>
                        <td className="px-4 py-3 text-sm font-mono text-slate-700 dark:text-slate-200">{rec.end_time}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400">{rec.total_label}</span>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 max-w-[160px] truncate">{rec.location || "-"}</td>
                        <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300 max-w-[200px] truncate">{rec.note || "-"}</td>
                        <td className="px-4 py-3">
                          {rec.photo_path ? (
                            <button onClick={() => setPhoto({ url: `${API}/files/${rec.photo_path}`, name: rec.employee_name })} data-testid={`img-photo-proof-${rec.id}`}>
                              <img src={`${API}/files/${rec.photo_path}`} alt="foto" className="h-10 w-10 rounded-md object-cover border border-slate-200 dark:border-slate-700 hover:ring-2 ring-blue-500 transition" />
                            </button>
                          ) : (
                            <StatusBadge rec={rec} />
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            {canEdit(rec) && (
                              <Button variant="ghost" size="icon" onClick={() => setEditRecord(rec)} data-testid={`btn-edit-overtime-${rec.id}`}>
                                <Pencil className="h-4 w-4" />
                              </Button>
                            )}
                            {isAdmin && (
                              <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(rec)} className="text-red-500 hover:text-red-600" data-testid={`btn-delete-overtime-${rec.id}`}>
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {records.map((rec, i) => (
                <div key={rec.id} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4" data-testid={`card-overtime-${rec.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{i + 1}. {rec.employee_name}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{formatDate(rec.date)}</p>
                    </div>
                    <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400 shrink-0">{rec.total_label}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-3 text-sm">
                    <div><span className="text-xs text-slate-400 block">Mulai</span><span className="font-mono text-slate-700 dark:text-slate-200">{rec.start_time}</span></div>
                    <div><span className="text-xs text-slate-400 block">Akhir</span><span className="font-mono text-slate-700 dark:text-slate-200">{rec.end_time}</span></div>
                    <div className="col-span-2"><span className="text-xs text-slate-400 block">Lokasi / Hari</span><span className="text-slate-700 dark:text-slate-200">{rec.location || "-"}</span></div>
                    <div className="col-span-2"><span className="text-xs text-slate-400 block">Keterangan</span><span className="text-slate-700 dark:text-slate-200">{rec.note || "-"}</span></div>
                  </div>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                    {rec.photo_path ? (
                      <button onClick={() => setPhoto({ url: `${API}/files/${rec.photo_path}`, name: rec.employee_name })} className="flex items-center gap-2" data-testid={`img-photo-proof-${rec.id}`}>
                        <img src={`${API}/files/${rec.photo_path}`} alt="foto" className="h-10 w-10 rounded-md object-cover border border-slate-200 dark:border-slate-700" />
                        <span className="text-xs text-blue-600">Lihat foto</span>
                      </button>
                    ) : (
                      <StatusBadge rec={rec} />
                    )}
                    <div className="flex gap-1">
                      {canEdit(rec) && (
                        <Button variant="outline" size="sm" onClick={() => setEditRecord(rec)} className="gap-1" data-testid={`btn-edit-overtime-${rec.id}`}>
                          <Pencil className="h-3.5 w-3.5" /> Edit
                        </Button>
                      )}
                      {isAdmin && (
                        <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(rec)} className="text-red-500" data-testid={`btn-delete-overtime-${rec.id}`}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      <OvertimeEditModal open={!!editRecord} onClose={() => setEditRecord(null)} record={editRecord} onSaved={loadData} />
      <OvertimeAddModal open={addOpen} onClose={() => setAddOpen(false)} employees={employees} onSaved={loadData} />
      <EmployeeManagementSheet open={empSheetOpen} onClose={() => setEmpSheetOpen(false)} onChanged={() => { loadEmployees(); loadData(); }} />
      <PhotoPreviewModal open={!!photo} onClose={() => setPhoto(null)} url={photo?.url} name={photo?.name} />

      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Hapus data lembur?</AlertDialogTitle>
            <AlertDialogDescription>
              Data lembur <strong>{deleteTarget?.employee_name}</strong> pada {deleteTarget && formatDate(deleteTarget.date)} akan dihapus permanen.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Batal</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700" data-testid="btn-confirm-delete-overtime">Hapus</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
