import { useState, useEffect, useCallback } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Loader2, Plus, Pencil, Trash2, UserPlus } from "lucide-react";

const emptyForm = { name: "", jabatan: "", active: true };

export default function EmployeeManagementSheet({ open, onClose, onChanged }) {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(null); // null=closed, {} object=form
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/employees");
      setEmployees(data);
    } catch (e) {
      toast.error("Gagal memuat daftar karyawan");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const openAdd = () => {
    setForm(emptyForm);
    setEditing("new");
  };
  const openEdit = (emp) => {
    setForm({ name: emp.name, jabatan: emp.jabatan || "", active: emp.active });
    setEditing(emp);
  };

  const handleSave = async () => {
    if (!form.name) return toast.error("Nama wajib diisi");
    setSaving(true);
    try {
      if (editing === "new") {
        await api.post("/employees", form);
        toast.success("Karyawan ditambahkan");
      } else {
        await api.put(`/employees/${editing.id}`, form);
        toast.success("Data karyawan diperbarui");
      }
      setEditing(null);
      await load();
      onChanged?.();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || "Gagal menyimpan");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.delete(`/employees/${deleteTarget.id}`);
      toast.success("Karyawan dihapus");
      setDeleteTarget(null);
      await load();
      onChanged?.();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || "Gagal menghapus");
    }
  };

  return (
    <>
      <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto" data-testid="employee-sheet">
          <SheetHeader className="mb-4">
            <SheetTitle className="font-heading">Kelola Karyawan</SheetTitle>
          </SheetHeader>

          <Button onClick={openAdd} className="w-full mb-4 bg-blue-600 hover:bg-blue-700 text-white gap-2" data-testid="btn-add-employee">
            <UserPlus className="h-4 w-4" /> Tambah Karyawan
          </Button>

          {loading ? (
            <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
          ) : employees.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-10">Belum ada karyawan. Tambahkan karyawan pertama.</p>
          ) : (
            <div className="space-y-2">
              {employees.map((emp) => (
                <div key={emp.id} className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900" data-testid={`employee-row-${emp.id}`}>
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center text-white text-xs font-semibold shrink-0">
                    {emp.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{emp.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {emp.jabatan && <span className="text-[11px] text-slate-400">{emp.jabatan}</span>}
                      <Badge variant="outline" className={emp.active ? "text-emerald-600 border-emerald-200" : "text-slate-400 border-slate-200"}>
                        {emp.active ? "Aktif" : "Nonaktif"}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button variant="ghost" size="icon" onClick={() => openEdit(emp)} data-testid={`btn-edit-employee-${emp.id}`}><Pencil className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(emp)} className="text-red-500 hover:text-red-600" data-testid={`btn-delete-employee-${emp.id}`}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Add/Edit form dialog */}
      <Dialog open={editing !== null} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent className="max-w-md" data-testid="employee-form-dialog">
          <DialogHeader>
            <DialogTitle>{editing === "new" ? "Tambah Karyawan" : "Edit Karyawan"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-2">
              <Label>Nama Lengkap</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="input-employee-name" />
            </div>
            <div className="space-y-2">
              <Label>Jabatan</Label>
              <Input value={form.jabatan} onChange={(e) => setForm({ ...form, jabatan: e.target.value })} data-testid="input-employee-jabatan" />
            </div>
            <div className="flex items-center justify-between rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-2">
              <Label className="cursor-pointer">Status Aktif</Label>
              <Switch checked={form.active} onCheckedChange={(v) => setForm({ ...form, active: v })} data-testid="switch-employee-active" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)} disabled={saving}>Batal</Button>
            <Button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white gap-2" data-testid="btn-save-employee">
              {saving && <Loader2 className="h-4 w-4 animate-spin" />} Simpan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => !v && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Hapus karyawan?</AlertDialogTitle>
            <AlertDialogDescription>
              Menghapus <strong>{deleteTarget?.name}</strong> juga akan menghapus seluruh data lembur miliknya. Tindakan ini tidak dapat dibatalkan.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Batal</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700" data-testid="btn-confirm-delete-employee">Hapus</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
