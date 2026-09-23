import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function PhotoPreviewModal({ open, onClose, url, name }) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl" data-testid="photo-preview-modal">
        <DialogHeader>
          <DialogTitle>Foto Kondisi Lembur {name ? `- ${name}` : ""}</DialogTitle>
        </DialogHeader>
        {url ? (
          <img src={url} alt="Foto kondisi lembur" className="w-full rounded-lg object-contain max-h-[70vh]" />
        ) : (
          <p className="text-sm text-slate-500 py-8 text-center">Tidak ada foto.</p>
        )}
      </DialogContent>
    </Dialog>
  );
}
