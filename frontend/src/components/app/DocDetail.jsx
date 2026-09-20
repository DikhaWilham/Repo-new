import { useRef, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { FileText, Upload, Trash2, Loader2, Image as ImageIcon, Pencil } from "lucide-react";
import StatusBadge from "@/components/app/StatusBadge";
import { formatTanggal, formatRupiah, SKEMA_LABEL } from "@/lib/format";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function Row({ label, value, mono }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <span className={`text-right text-sm text-slate-900 ${mono ? "font-data" : "font-medium"}`}>{value}</span>
    </div>
  );
}

export default function DocDetail({ doc, onClose, onRefresh, onEdit, onDelete }) {
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  if (!doc) return null;

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.post(`/documents/${doc.id}/attachments`, fd);
      toast.success("Lampiran berhasil diunggah");
      onRefresh(doc.id);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (attId) => {
    setDeletingId(attId);
    try {
      await api.delete(`/documents/${doc.id}/attachments/${attId}`);
      toast.success("Lampiran dihapus");
      onRefresh(doc.id);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setDeletingId(null);
    }
  };

  const attachments = doc.attachments || [];

  return (
    <Sheet open={!!doc} onOpenChange={(open) => !open && onClose()}>
      <SheetContent data-testid="doc-detail-sheet" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="font-headline text-left text-lg">{doc.nama_counter}</SheetTitle>
        </SheetHeader>

        <div className="mt-2 flex items-center gap-3">
          <StatusBadge status={doc.status} testid="detail-status-badge" />
          {doc.hari_tersisa != null && (
            <span data-testid="detail-days-remaining" className={`font-data text-xs font-semibold ${doc.hari_tersisa < 0 ? "text-rose-600" : doc.hari_tersisa <= 30 ? "text-amber-600" : doc.hari_tersisa <= 90 ? "text-emerald-600" : "text-slate-600"}`}>
              {doc.hari_tersisa < 0 ? `Berakhir ${Math.abs(doc.hari_tersisa)} hari lalu` : `${doc.hari_tersisa} hari menuju akhir sewa`}
            </span>
          )}
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="font-headline text-sm font-semibold text-slate-900">Informasi Counter</h3>
          <Separator className="my-2" />
          <Row label="Alamat Counter" value={doc.alamat_counter} />
          <Row label="Skema" value={SKEMA_LABEL[doc.skema]} />
          <Row label="Nama Brand" value={doc.nama_brand} />
          <Row label="Nama CV/PT" value={doc.nama_cv} />
          <Row label="Luasan" value={`${doc.luasan} m²`} mono />
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="font-headline text-sm font-semibold text-slate-900">Biaya & Masa Sewa</h3>
          <Separator className="my-2" />
          <Row label="Service Charge / bln" value={formatRupiah(doc.service_charge)} mono />
          <Row label="Promo Levy / bln" value={formatRupiah(doc.promo_levy)} mono />
          <Row label="Tanggal Mulai Sewa" value={formatTanggal(doc.tanggal_mulai)} />
          <Row label="Tanggal Akhir Sewa" value={formatTanggal(doc.tanggal_akhir)} />
          <Row label="Reminder Date" value={formatTanggal(doc.reminder_date)} />
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="font-headline text-sm font-semibold text-slate-900">Keterangan / Progres</h3>
          <Separator className="my-2" />
          <p data-testid="detail-keterangan" className="text-sm leading-relaxed text-slate-700">
            {doc.keterangan || "Belum ada keterangan."}
          </p>
        </div>

        <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-headline text-sm font-semibold text-slate-900">Lampiran Dokumen</h3>
            <Button
              data-testid="upload-attachment-button"
              variant="outline"
              size="sm"
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
              className="text-slate-600 hover:text-slate-900"
            >
              {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              Unggah
            </Button>
            <input ref={fileRef} data-testid="upload-attachment-input" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" className="hidden" onChange={handleUpload} />
          </div>
          <Separator className="my-2" />
          {attachments.length === 0 ? (
            <p data-testid="attachment-empty" className="py-2 text-sm text-slate-500">Belum ada lampiran. Unggah PDF atau foto kontrak.</p>
          ) : (
            <ul className="space-y-2">
              {attachments.map((att) => (
                <li key={att.id} className="flex items-center justify-between gap-2 rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
                  <a
                    data-testid={`attachment-link-${att.id}`}
                    href={`${API}/files/${att.storage_path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex min-w-0 items-center gap-2 text-sm font-medium text-blue-700 hover:text-blue-900"
                  >
                    {att.content_type === "application/pdf" ? <FileText className="h-4 w-4 shrink-0" /> : <ImageIcon className="h-4 w-4 shrink-0" />}
                    <span className="truncate">{att.filename}</span>
                  </a>
                  <Button
                    data-testid={`attachment-delete-${att.id}`}
                    variant="ghost"
                    size="icon"
                    disabled={deletingId === att.id}
                    onClick={() => handleDelete(att.id)}
                    className="h-8 w-8 shrink-0 text-slate-400 hover:text-rose-700"
                  >
                    {deletingId === att.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="mt-6 flex gap-3 pb-2">
          <Button
            data-testid="detail-edit-button"
            variant="outline"
            className="flex-1 text-slate-600 hover:text-slate-900"
            onClick={() => onEdit(doc)}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Edit Dokumen
          </Button>
          <Button
            data-testid="detail-delete-button"
            variant="outline"
            className="flex-1 border-rose-200 text-rose-600 hover:bg-rose-50 hover:text-rose-700"
            onClick={() => onDelete(doc)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Hapus
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
