import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiError } from "@/lib/api";
import { SKEMA_LABEL, STATUS_LABEL, PROGRES_MOU_LABEL, formatTanggal } from "@/lib/format";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Building2, LogOut } from "lucide-react";
import { toast } from "sonner";
import StatsCards from "@/components/app/StatsCards";
import ReminderBanner from "@/components/app/ReminderBanner";
import Toolbar from "@/components/app/Toolbar";
import DocTable from "@/components/app/DocTable";
import DocForm from "@/components/app/DocForm";
import DocDetail from "@/components/app/DocDetail";
import ImportDialog from "@/components/app/ImportDialog";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [skema, setSkema] = useState("all");
  const [status, setStatus] = useState("all");
  const [cv, setCv] = useState("all");
  const [progresMou, setProgresMou] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [sheetsConnected, setSheetsConnected] = useState(false);
  const [editing, setEditing] = useState(null);
  const [detail, setDetail] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 400);
    return () => clearTimeout(t);
  }, [search]);

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (debouncedSearch) params.search = debouncedSearch;
      if (skema !== "all") params.skema = skema;
      if (status !== "all") params.status = status;
      if (cv !== "all") params.nama_cv = cv;
      if (progresMou !== "all") params.progres_mou = progresMou;
      const { data } = await api.get("/documents", { params });
      setDocs(data);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch, skema, status, cv, progresMou]);

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await api.get("/documents/stats");
      setStats(data);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    api.get("/sheets/status").then(({ data }) => setSheetsConnected(!!data.configured && !data.error)).catch(() => {});
  }, []);

  const syncSheets = async () => {
    try {
      const { data: st } = await api.get("/sheets/status");
      if (!st.configured) {
        toast.error("Google Sheets belum terhubung. Hubungi admin untuk menghubungkan spreadsheet.");
        return;
      }
      toast.info("Menyinkronkan dengan Google Sheets...");
      const { data } = await api.post("/sheets/pull");
      await api.post("/sheets/push");
      toast.success(`Sync selesai: ${data.updated} diperbarui, ${data.created} ditambah dari Sheets`);
      fetchDocs();
      fetchStats();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const refreshDetail = async (id) => {
    try {
      const { data } = await api.get(`/documents/${id}`);
      setDetail(data);
      fetchDocs();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const openDetailById = async (id) => {
    try {
      const { data } = await api.get(`/documents/${id}`);
      setDetail(data);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const handleSave = async (payload, file) => {
    try {
      let saved;
      if (editing) {
        ({ data: saved } = await api.put(`/documents/${editing.id}`, payload));
      } else {
        ({ data: saved } = await api.post("/documents", payload));
      }
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        await api.post(`/documents/${saved.id}/attachments`, fd);
      }
      toast.success(editing ? "Dokumen berhasil diperbarui" : "Dokumen berhasil ditambahkan");
      setFormOpen(false);
      setEditing(null);
      fetchDocs();
      fetchStats();
    } catch (err) {
      throw formatApiError(err);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/documents/${deleting.id}`);
      toast.success(`Dokumen "${deleting.nama_counter}" dihapus`);
      setDeleting(null);
      if (detail?.id === deleting.id) setDetail(null);
      fetchDocs();
      fetchStats();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setDeleteLoading(false);
    }
  };

  const exportCSV = () => {
    if (docs.length === 0) {
      toast.error("Tidak ada data untuk diekspor");
      return;
    }
    const headers = [
      "Kode", "Nama Counter", "Alamat Counter", "Skema", "Nama Brand", "Nama CV",
      "Luasan (m2)", "Service Charge (Rp)", "Promo Levy (Rp)",
      "Tanggal Mulai Sewa", "Tanggal Akhir Sewa", "Reminder Date",
      "Status", "Hari Tersisa", "Progres MOU", "Keterangan",
    ];
    const rows = docs.map((d) => [
      d.kode || "", d.nama_counter, d.alamat_counter, SKEMA_LABEL[d.skema], d.nama_brand, d.nama_cv,
      d.luasan, d.service_charge, d.promo_levy,
      formatTanggal(d.tanggal_mulai), formatTanggal(d.tanggal_akhir), formatTanggal(d.reminder_date),
      STATUS_LABEL[d.status], d.hari_tersisa ?? "", PROGRES_MOU_LABEL[d.progres_mou] || d.progres_mou || "", d.keterangan || "",
    ]);
    const csv = "\ufeff" + [headers, ...rows]
      .map((r) => r.map((v) => `"${String(v ?? "").replaceAll('"', '""')}"`).join(";"))
      .join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dokumen-sewa-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`${docs.length} dokumen diekspor ke CSV`);
  };

  const resetFilters = () => {
    setSearch("");
    setSkema("all");
    setStatus("all");
    setCv("all");
    setProgresMou("all");
  };

  return (
    <div data-testid="dashboard-page" className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="font-headline text-base font-bold leading-tight tracking-tight text-slate-900">SewaKontrak Pro</h1>
              <p className="text-xs text-slate-500">Monitoring Dokumen Sewa Menyewa</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span data-testid="user-name" className="hidden text-sm font-medium text-slate-700 sm:block">{user?.name || user?.email}</span>
            <Button data-testid="logout-button" variant="outline" size="sm" onClick={logout} className="text-slate-600 hover:text-slate-900">
              <LogOut className="mr-2 h-4 w-4" />
              Keluar
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <ReminderBanner stats={stats} onOpenDetail={openDetailById} />
        <StatsCards stats={stats} />
        <Toolbar
          search={search}
          setSearch={setSearch}
          skema={skema}
          setSkema={setSkema}
          status={status}
          setStatus={setStatus}
          cv={cv}
          setCv={setCv}
          cvList={stats?.daftar_cv || []}
          progresMou={progresMou}
          setProgresMou={setProgresMou}
          onExport={exportCSV}
          onImport={() => setImportOpen(true)}
          onSyncSheets={syncSheets}
          sheetsConnected={sheetsConnected}
          onAdd={() => { setEditing(null); setFormOpen(true); }}
          onReset={resetFilters}
        />
        <DocTable
          docs={docs}
          loading={loading}
          onDetail={(doc) => openDetailById(doc.id)}
          onEdit={(doc) => { setEditing(doc); setFormOpen(true); }}
          onDelete={(doc) => setDeleting(doc)}
        />
      </main>

      <DocForm open={formOpen} onOpenChange={(o) => { setFormOpen(o); if (!o) setEditing(null); }} editing={editing} onSave={handleSave} />
      <ImportDialog open={importOpen} onOpenChange={setImportOpen} onDone={() => { fetchDocs(); fetchStats(); }} />
      <DocDetail
        doc={detail}
        onClose={() => setDetail(null)}
        onRefresh={refreshDetail}
        onEdit={(d) => { setDetail(null); setEditing(d); setFormOpen(true); }}
        onDelete={(d) => { setDetail(null); setDeleting(d); }}
      />

      <AlertDialog open={!!deleting} onOpenChange={(o) => !o && setDeleting(null)}>
        <AlertDialogContent data-testid="delete-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-headline">Hapus dokumen ini?</AlertDialogTitle>
            <AlertDialogDescription>
              Dokumen <span className="font-semibold text-slate-800">"{deleting?.nama_counter}"</span> beserta lampirannya akan dihapus permanen. Tindakan ini tidak dapat dibatalkan.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="delete-cancel-button">Batal</AlertDialogCancel>
            <AlertDialogAction
              data-testid="delete-confirm-button"
              onClick={handleDelete}
              disabled={deleteLoading}
              className="bg-rose-600 text-white hover:bg-rose-700"
            >
              {deleteLoading ? "Menghapus..." : "Ya, Hapus"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
