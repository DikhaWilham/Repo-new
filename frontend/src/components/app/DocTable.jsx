import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Eye, Pencil, Trash2, FileSearch } from "lucide-react";
import StatusBadge from "@/components/app/StatusBadge";
import { formatTanggal, formatRupiah, SKEMA_LABEL } from "@/lib/format";

function ActionButtons({ doc, onDetail, onEdit, onDelete, compact }) {
  return (
    <div className="flex items-center gap-1">
      <Button data-testid={`doc-detail-button-${doc.id}`} variant="ghost" size="icon" onClick={() => onDetail(doc)} title="Detail" className="text-slate-500 hover:text-slate-900">
        <Eye className="h-4 w-4" />
      </Button>
      <Button data-testid={`doc-edit-button-${doc.id}`} variant="ghost" size="icon" onClick={() => onEdit(doc)} title="Edit" className="text-slate-500 hover:text-blue-700">
        <Pencil className="h-4 w-4" />
      </Button>
      <Button data-testid={`doc-delete-button-${doc.id}`} variant="ghost" size="icon" onClick={() => onDelete(doc)} title="Hapus" className="text-slate-500 hover:text-rose-700">
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

export default function DocTable({ docs, loading, onDetail, onEdit, onDelete }) {
  if (loading) {
    return (
      <div data-testid="doc-list-loading" className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div data-testid="doc-list-empty" className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white py-16">
        <FileSearch className="h-10 w-10 text-slate-300" />
        <p className="mt-4 font-headline text-base font-semibold text-slate-700">Tidak ada dokumen ditemukan</p>
        <p className="mt-1 text-sm text-slate-500">Coba ubah kata kunci atau filter, atau tambah dokumen baru.</p>
      </div>
    );
  }

  return (
    <>
      {/* Tabel desktop */}
      <div data-testid="doc-table" className="hidden overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left">
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500">Counter</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500">Brand / CV</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500">Skema</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500 text-right">Luasan</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500 text-right">Service Charge</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500 text-right">Promo Levy</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500">Masa Sewa</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500">Reminder</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
              <th className="px-4 py-3 font-headline text-xs font-semibold uppercase tracking-wide text-slate-500 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {docs.map((doc) => (
              <tr key={doc.id} data-testid={`doc-row-${doc.id}`} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60">
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-900">{doc.nama_counter}</p>
                  <p className="max-w-[220px] truncate text-xs text-slate-500">{doc.alamat_counter}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-slate-800">{doc.nama_brand}</p>
                  <p className="text-xs text-slate-500">{doc.nama_cv}</p>
                </td>
                <td className="px-4 py-3 text-slate-700">{SKEMA_LABEL[doc.skema]}</td>
                <td className="px-4 py-3 text-right font-data text-slate-800">{doc.luasan} m²</td>
                <td className="px-4 py-3 text-right font-data text-slate-800">{formatRupiah(doc.service_charge)}</td>
                <td className="px-4 py-3 text-right font-data text-slate-800">{formatRupiah(doc.promo_levy)}</td>
                <td className="px-4 py-3 text-xs text-slate-600">
                  {formatTanggal(doc.tanggal_mulai)} — {formatTanggal(doc.tanggal_akhir)}
                  {doc.hari_tersisa != null && (
                    <p className={`font-data font-medium ${doc.hari_tersisa < 0 ? "text-rose-600" : doc.hari_tersisa <= 30 ? "text-amber-600" : doc.hari_tersisa <= 90 ? "text-emerald-600" : "text-slate-500"}`}>
                      {doc.hari_tersisa < 0 ? `lewat ${Math.abs(doc.hari_tersisa)} hari` : `${doc.hari_tersisa} hari lagi`}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">{formatTanggal(doc.reminder_date)}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={doc.status} testid={`status-badge-${doc.id}`} />
                </td>
                <td className="px-4 py-3 text-right">
                  <ActionButtons doc={doc} onDetail={onDetail} onEdit={onEdit} onDelete={onDelete} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Daftar ringkas mobile */}
      <div data-testid="doc-card-list" className="space-y-2 md:hidden">
        {docs.map((doc) => (
          <div
            key={doc.id}
            data-testid={`doc-card-${doc.id}`}
            className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate font-headline text-sm font-semibold text-slate-900">{doc.nama_counter}</p>
              <p className="truncate text-xs text-slate-500">
                {doc.nama_brand}
                {doc.nama_cv ? ` · ${doc.nama_cv}` : ""}
              </p>
            </div>
            <StatusBadge status={doc.status} testid={`status-badge-card-${doc.id}`} />
            <Button
              data-testid={`doc-detail-button-${doc.id}`}
              variant="ghost"
              size="icon"
              onClick={() => onDetail(doc)}
              title="Lihat detail"
              className="shrink-0 text-slate-500 hover:text-slate-900"
            >
              <Eye className="h-5 w-5" />
            </Button>
          </div>
        ))}
      </div>
    </>
  );
}
