import { useState, useEffect } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { calcMinutes, minutesToLabel, todayStr } from "@/lib/overtime";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Loader2, Clock } from "lucide-react";

const empty = { employee_id: "", date: todayStr(), start_time: "17:00", end_time: "21:00", location: "", note: "" };

export default function OvertimeAddModal({ open, onClose, employees, onSaved }) {
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setForm(empty);
  }, [open]);

  const totalMin = calcMinutes(form.start_time, form.end_time);

  const handleSave = async () => {
    if (!form.employee_id) return toast.error("Pilih karyawan terlebih dahulu");
    if (!form.date || !form.start_time || !form.end_time) return toast.error("Tanggal & jam wajib diisi");
    setSaving(true);
    try {
      await api.post("/overtime", form);
      toast.success("Data lembur ditambahkan");
      onSaved();
      onClose();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || "Gagal menambahkan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="overtime-add-modal">
        <DialogHeader>
          <DialogTitle>Tambah Data Rekap Lembur</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label>Nama Karyawan</Label>
            <Select value={form.employee_id} onValueChange={(v) => setForm({ ...form, employee_id: v })}>
              <SelectTrigger data-testid="select-add-employee"><SelectValue placeholder="Pilih karyawan" /></SelectTrigger>
              <SelectContent>
                {employees.map((e) => (
                  <SelectItem key={e.id} value={e.id}>{e.name}{e.nip ? ` (${e.nip})` : ""}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Tanggal Lembur</Label>
            <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} data-testid="input-add-date" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Jam Mulai</Label>
              <Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} data-testid="input-add-start-time" />
            </div>
            <div className="space-y-2">
              <Label>Jam Akhir</Label>
              <Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} data-testid="input-add-end-time" />
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 px-4 py-3">
            <Clock className="h-4 w-4 text-blue-600" />
            <span className="text-sm text-slate-600 dark:text-slate-300">Total Lembur:</span>
            <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400">{minutesToLabel(totalMin)}</span>
          </div>

          <div className="space-y-2">
            <Label>Lokasi / Hari saat Lembur</Label>
            <Input placeholder="cth: Kantor Pusat / Hari Libur" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="input-add-location" />
          </div>

          <div className="space-y-2">
            <Label>Keterangan Lembur</Label>
            <Textarea placeholder="Deskripsikan pekerjaan lembur..." value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} data-testid="input-add-note" rows={3} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Batal</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white gap-2" data-testid="btn-save-add-overtime">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />} Tambah
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
