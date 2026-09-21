import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Paperclip } from "lucide-react";
import { PROGRES_MOU_OPTIONS } from "@/lib/format";

const EMPTY = {
  nama_counter: "",
  alamat_counter: "",
  skema: "sewa",
  nama_brand: "",
  nama_cv: "",
  luasan: "",
  service_charge: "",
  promo_levy: "",
  tanggal_mulai: "",
  tanggal_akhir: "",
  reminder_date: "",
  keterangan: "",
  progres_mou: "",
};

export default function DocForm({ open, onOpenChange, editing, onSave }) {
  const [form, setForm] = useState(EMPTY);
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setError("");
      setFile(null);
      setForm(
        editing
          ? {
              nama_counter: editing.nama_counter || "",
              alamat_counter: editing.alamat_counter || "",
              skema: editing.skema || "sewa",
              nama_brand: editing.nama_brand || "",
              nama_cv: editing.nama_cv || "",
              luasan: editing.luasan ?? "",
              service_charge: editing.service_charge ?? "",
              promo_levy: editing.promo_levy ?? "",
              tanggal_mulai: editing.tanggal_mulai || "",
              tanggal_akhir: editing.tanggal_akhir || "",
              reminder_date: editing.reminder_date || "",
              keterangan: editing.keterangan || "",
              progres_mou: editing.progres_mou || "",
            }
          : EMPTY
      );
    }
  }, [open, editing]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e?.target ? e.target.value : e }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.tanggal_akhir < form.tanggal_mulai) {
      setError("Tanggal akhir sewa tidak boleh sebelum tanggal mulai");
      return;
    }
    setSaving(true);
    const payload = {
      ...form,
      luasan: parseFloat(form.luasan) || 0,
      service_charge: parseFloat(form.service_charge) || 0,
      promo_levy: parseFloat(form.promo_levy) || 0,
      reminder_date: form.reminder_date || null,
    };
    try {
      await onSave(payload, file);
    } catch (errMsg) {
      setError(errMsg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="doc-form-dialog" className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-headline">{editing ? "Edit Dokumen Sewa" : "Tambah Dokumen Sewa"}</DialogTitle>
          <DialogDescription>
            Lengkapi detail kontrak sewa counter. Kolom bertanda * wajib diisi.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div data-testid="doc-form-error" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="nama_counter">Nama Counter *</Label>
              <Input id="nama_counter" data-testid="doc-form-nama-counter" required value={form.nama_counter} onChange={set("nama_counter")} placeholder="cth: Counter Chatime Grand Indonesia" />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="alamat_counter">Alamat Counter *</Label>
              <Textarea id="alamat_counter" data-testid="doc-form-alamat-counter" required rows={2} value={form.alamat_counter} onChange={set("alamat_counter")} placeholder="Mall, lantai, unit, kota" />
            </div>
            <div className="space-y-2">
              <Label>Skema *</Label>
              <Select value={form.skema} onValueChange={(v) => setForm((f) => ({ ...f, skema: v }))}>
                <SelectTrigger data-testid="doc-form-skema">
                  <SelectValue placeholder="Pilih skema" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sewa">Sewa</SelectItem>
                  <SelectItem value="bagi_hasil">Bagi Hasil</SelectItem>
                  <SelectItem value="hybrid">Hybrid (Sewa + Bagi Hasil)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="nama_brand">Nama Brand *</Label>
              <Input id="nama_brand" data-testid="doc-form-nama-brand" required value={form.nama_brand} onChange={set("nama_brand")} placeholder="cth: Chatime" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nama_cv">Nama CV/PT *</Label>
              <Input id="nama_cv" data-testid="doc-form-nama-cv" required value={form.nama_cv} onChange={set("nama_cv")} placeholder="cth: CV Kawan Lama Sejahtera" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="luasan">Luasan (m²) *</Label>
              <Input id="luasan" data-testid="doc-form-luasan" type="number" step="0.1" min="0" required value={form.luasan} onChange={set("luasan")} placeholder="cth: 12.5" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="service_charge">Service Charge (Rp/bln)</Label>
              <Input id="service_charge" data-testid="doc-form-service-charge" type="number" min="0" value={form.service_charge} onChange={set("service_charge")} placeholder="cth: 2500000" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="promo_levy">Promo Levy (Rp/bln)</Label>
              <Input id="promo_levy" data-testid="doc-form-promo-levy" type="number" min="0" value={form.promo_levy} onChange={set("promo_levy")} placeholder="cth: 500000" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tanggal_mulai">Tanggal Mulai Sewa *</Label>
              <Input id="tanggal_mulai" data-testid="doc-form-tanggal-mulai" type="date" required value={form.tanggal_mulai} onChange={set("tanggal_mulai")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tanggal_akhir">Tanggal Akhir Sewa *</Label>
              <Input id="tanggal_akhir" data-testid="doc-form-tanggal-akhir" type="date" required value={form.tanggal_akhir} onChange={set("tanggal_akhir")} />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="reminder_date">Reminder Date</Label>
              <Input id="reminder_date" data-testid="doc-form-reminder-date" type="date" value={form.reminder_date} onChange={set("reminder_date")} />
              <p className="text-xs text-slate-500">Mulai tanggal ini kontrak ditandai "Hampir Berakhir" di dasbor. Kosongkan untuk otomatis 30 hari sebelum akhir sewa.</p>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="keterangan">Keterangan / Update Progres</Label>
              <Textarea id="keterangan" data-testid="doc-form-keterangan" rows={3} value={form.keterangan} onChange={set("keterangan")} placeholder="cth: Menunggu draft perpanjangan dari pihak mall" />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label>Progres MOU</Label>
              <Select value={form.progres_mou || "none"} onValueChange={(v) => setForm((f) => ({ ...f, progres_mou: v === "none" ? "" : v }))}>
                <SelectTrigger data-testid="doc-form-progres-mou">
                  <SelectValue placeholder="Pilih progres (opsional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— Tidak ada / kontrak berjalan normal —</SelectItem>
                  {PROGRES_MOU_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500">Gunakan untuk counter yang akan buka atau masih dalam proses, sebagai pengingat tahapan progresnya.</p>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="lampiran">Lampiran Dokumen (PDF/JPG/PNG, maks 10 MB)</Label>
              <div className="flex items-center gap-3">
                <Input
                  id="lampiran"
                  data-testid="doc-form-attachment-input"
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="cursor-pointer"
                />
                {file && <Paperclip className="h-4 w-4 shrink-0 text-slate-500" />}
              </div>
              {editing && <p className="text-xs text-slate-500">Lampiran yang sudah ada dapat dikelola dari halaman detail dokumen.</p>}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button data-testid="doc-form-cancel-button" type="button" variant="outline" onClick={() => onOpenChange(false)} className="text-slate-600 hover:text-slate-900">
              Batal
            </Button>
            <Button data-testid="doc-form-submit-button" type="submit" disabled={saving} className="bg-slate-900 text-white hover:bg-slate-800">
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {editing ? "Simpan Perubahan" : "Tambah Dokumen"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
