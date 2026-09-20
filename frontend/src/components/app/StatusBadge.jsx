import { Badge } from "@/components/ui/badge";
import { STATUS_LABEL } from "@/lib/format";

const STATUS_CLS = {
  aktif: "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-50",
  hampir_berakhir: "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-50 animate-pulse",
  berakhir: "bg-rose-50 text-rose-700 border-rose-200 hover:bg-rose-50",
};

export default function StatusBadge({ status, testid }) {
  return (
    <Badge data-testid={testid || `status-badge-${status}`} variant="outline" className={`whitespace-nowrap ${STATUS_CLS[status] || ""}`}>
      {STATUS_LABEL[status] || status}
    </Badge>
  );
}
