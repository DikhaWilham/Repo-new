import { useState, useEffect, useRef } from "react";
import api, { API, formatApiErrorDetail } from "@/lib/api";
import { calcMinutes, minutesToLabel } from "@/lib/overtime";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Loader2, Upload, Clock, ImageIcon } from "lucide-react";

export default function OvertimeEditModal({ open, onClose, record, onSaved }) {
  const [form, setForm] = useState({ start_time: "", end_time: "", location: "", note: "" });
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef();

  useEffect(() => {
    if (record) {
      setForm({
        start_time: record.start_time || "",
        end_time: record.end_time || "",
        location: record.location || "",
        note: record.note || "",
      });
      setFile(null);
      setPreviewUrl(record.photo_path ? `${API}/files/${record.photo_path}` : null);
    }
  }, [record]);

  const totalMin = calcMinutes(form.start_time, form.end_time);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  };

  const handleSave = async () => {
    if (!form.start_time || !form.end_time) {
      toast.error("Jam mulai dan jam akhir wajib diisi");
      return;
    }
    setSaving(true);
    try {
      await api.put(`/overtime/${record.id}`, form);
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        await api.post(`/overtime/${record.id}/photo`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      }
      toast.success("Data lembur berhasil disimpan");
      onSaved();
      onClose();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || "Gagal menyimpan");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="overtime-edit-modal">
        <DialogHeader>
          <DialogTitle>Edit Data Lembur {record?.employee_name ? `- ${record.employee_name}` : ""}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Jam Mulai Lembur</Label>
              <Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} data-testid="input-edit-start-time" />
            </div>
            <div className="space-y-2">
              <Label>Jam Akhir Lembur</Label>
              <Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} data-testid="input-edit-end-time" />
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 px-4 py-3">
            <Clock className="h-4 w-4 text-blue-600" />
            <span className="text-sm text-slate-600 dark:text-slate-300">Total Lembur:</span>
            <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400" data-testid="badge-calculated-total-time">
              {minutesToLabel(totalMin)}
            </span>
          </div>

          <div className="space-y-2">
            <Label>Lokasi / Hari saat Lembur</Label>
            <Input placeholder="cth: Kantor Pusat / Hari Libur" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="input-edit-location" />
          </div>

          <div className="space-y-2">
            <Label>Keterangan Lembur</Label>
            <Textarea placeholder="Deskripsikan pekerjaan lembur..." value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} data-testid="input-edit-note" rows={3} />
          </div>

          <div className="space-y-2">
            <Label>Foto Kondisi Lembur</Label>
            <div className="flex items-center gap-3">
              <div className="h-20 w-20 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 flex items-center justify-center overflow-hidden bg-slate-50 dark:bg-slate-800 shrink-0">
                {previewUrl ? (
                  <img src={previewUrl} alt="preview" className="h-full w-full object-cover" />
                ) : (
                  <ImageIcon className="h-6 w-6 text-slate-400" />
                )}
              </div>
              <div>
                <input ref={fileRef} type="file" accept="image/*" onChange={handleFile} className="hidden" data-testid="input-file-photo" />
                <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()} className="gap-2">
                  <Upload className="h-4 w-4" /> Pilih Foto
                </Button>
                <p className="text-xs text-slate-400 mt-1">JPG, PNG, WEBP. Maks 10MB.</p>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Batal</Button>
          <Button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700 text-white gap-2" data-testid="btn-save-overtime">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />} Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
