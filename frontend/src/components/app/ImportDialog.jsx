import { useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FileSpreadsheet, FileDown, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";

const TEMPLATE_HEADERS = [
  "Nama Counter", "Alamat Counter", "Skema", "Nama Brand", "Nama CV",
  "Luasan (m2)", "Service Charge (Rp)", "Promo Levy (Rp)",
  "Tanggal Mulai Sewa", "Tanggal Akhir Sewa", "Reminder Date", "Keterangan",
];
const TEMPLATE_EXAMPLE = [
  "Counter Chatime Grand Indonesia", "Grand Indonesia Mall Lt. 3A Unit 12, Jakarta Pusat", "Sewa",
  "Chatime", "CV Kawan Lama Sejahtera", "12,5", "2500000", "500000",
  "15/10/2025", "15/10/2026", "15/09/2026", "Menunggu draft perpanjangan dari pihak mall",
];

function downloadTemplate() {
  const csv = "\ufeff" + [TEMPLATE_HEADERS, TEMPLATE_EXAMPLE]
    .map((r) => r.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(";"))
    .join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "template-import-dokumen-sewa.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function friendlyUploadError(err) {
  if (err?.response) return formatApiError(err);
  return "Koneksi terputus saat mengunggah file. Pastikan internet stabil lalu coba lagi — jika file besar, bagi menjadi beberapa file lebih kecil.";
}

export default function ImportDialog({ open, onOpenChange, onDone }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);

  const reset = () => {
    setFile(null);
    setResult(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleClose = (o) => {
    if (!o) reset();
    onOpenChange(o);
  };

  const analyze = async (f) => {
    setLoading(true);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post("/documents/import?dry=true", fd, { timeout: 120000 });
      setResult(data);
    } catch (err) {
      toast.error(friendlyUploadError(err));
      setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } finally {
      setLoading(false);
    }
  };

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    analyze(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setCommitting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/documents/import", fd, { timeout: 120000 });
      toast.success(`${data.imported} dokumen berhasil diimpor${data.errors.length ? `, ${data.errors.length} baris dilewati` : ""}`);
      onDone();
      handleClose(false);
    } catch (err) {
      toast.error(friendlyUploadError(err));
    } finally {
      setCommitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent data-testid="import-dialog" className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-headline">Import dari Spreadsheet</DialogTitle>
          <DialogDescription>
            Unggah file <span className="font-medium">CSV</span> atau <span className="font-medium">Excel (.xlsx)</span>. Nama kolom akan dikenali otomatis (misal: Nama Counter, Nama Brand, Tanggal Mulai Sewa). Tanggal boleh berformat 15/10/2026 atau 2026-10-15.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button data-testid="import-template-button" variant="outline" onClick={downloadTemplate} className="text-slate-600 hover:text-slate-900">
              <FileDown className="mr-2 h-4 w-4" />
              Unduh Template CSV
            </Button>
            <Button
              data-testid="import-choose-file-button"
              variant="outline"
              onClick={() => fileRef.current?.click()}
              className="text-slate-600 hover:text-slate-900"
            >
              <FileSpreadsheet className="mr-2 h-4 w-4" />
              Pilih File
            </Button>
            <input
              ref={fileRef}
              data-testid="import-file-input"
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={handleFile}
            />
            {file && <span className="text-xs text-slate-500">{file.name}</span>}
          </div>

          {loading && (
            <div data-testid="import-loading" className="flex items-center gap-2 py-6 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Menganalisis file...
            </div>
          )}

          {result && (
            <div data-testid="import-result" className="space-y-3">
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="font-data text-xl font-semibold text-slate-900">{result.total_rows}</p>
                  <p className="text-xs text-slate-500">Total Baris</p>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <p data-testid="import-valid-count" className="font-data text-xl font-semibold text-emerald-700">{result.valid}</p>
                  <p className="text-xs text-emerald-700">Siap Diimpor</p>
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p data-testid="import-error-count" className="font-data text-xl font-semibold text-amber-700">{result.errors.length}</p>
                  <p className="text-xs text-amber-700">Dilewati</p>
                </div>
              </div>

              {result.errors.length > 0 && (
                <div data-testid="import-error-list" className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                  <p className="flex items-center gap-2 text-xs font-semibold text-amber-800">
                    <AlertTriangle className="h-4 w-4" /> Baris bermasalah (tidak akan diimpor):
                  </p>
                  <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto text-xs text-amber-800">
                    {result.errors.map((e, i) => (
                      <li key={i}>
                        Baris {e.row} — <span className="font-medium">{e.nama_counter}</span>: {e.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.preview.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table data-testid="import-preview-table" className="w-full text-xs">
                    <thead>
                      <tr className="border-b bg-slate-50 text-left">
                        <th className="px-3 py-2 font-semibold text-slate-600">Counter</th>
                        <th className="px-3 py-2 font-semibold text-slate-600">Brand</th>
                        <th className="px-3 py-2 font-semibold text-slate-600">Skema</th>
                        <th className="px-3 py-2 font-semibold text-slate-600">Mulai</th>
                        <th className="px-3 py-2 font-semibold text-slate-600">Akhir</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.preview.slice(0, 8).map((r, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="px-3 py-2 text-slate-800">{r.nama_counter}</td>
                          <td className="px-3 py-2 text-slate-600">{r.nama_brand}</td>
                          <td className="px-3 py-2 text-slate-600">{r.skema}</td>
                          <td className="px-3 py-2 font-data text-slate-600">{r.tanggal_mulai}</td>
                          <td className="px-3 py-2 font-data text-slate-600">{r.tanggal_akhir}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {result.preview.length > 8 && (
                    <p className="border-t bg-slate-50 px-3 py-1.5 text-xs text-slate-500">
                      +{result.valid - 8} dokumen lainnya
                    </p>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-1">
                <Button data-testid="import-cancel-button" variant="outline" onClick={() => handleClose(false)} className="text-slate-600 hover:text-slate-900">
                  Batal
                </Button>
                <Button
                  data-testid="import-submit-button"
                  disabled={committing || result.valid === 0}
                  onClick={handleImport}
                  className="bg-slate-900 text-white hover:bg-slate-800"
                >
                  {committing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                  Impor {result.valid} Dokumen
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
