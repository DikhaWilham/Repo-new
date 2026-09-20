import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, FileDown, Plus, RotateCcw } from "lucide-react";

export default function Toolbar({ search, setSearch, skema, setSkema, status, setStatus, onExport, onAdd, onReset }) {
  return (
    <div data-testid="filter-toolbar" className="flex flex-col gap-3 md:flex-row md:items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          data-testid="search-input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cari nama counter, brand, CV, atau alamat..."
          className="pl-9"
        />
      </div>
      <div className="grid grid-cols-2 gap-3 md:flex md:items-center">
        <Select value={skema} onValueChange={setSkema}>
          <SelectTrigger data-testid="filter-skema-select" className="w-full md:w-[150px]">
            <SelectValue placeholder="Skema" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua Skema</SelectItem>
            <SelectItem value="sewa">Sewa</SelectItem>
            <SelectItem value="bagi_hasil">Bagi Hasil</SelectItem>
            <SelectItem value="hybrid">Hybrid</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger data-testid="filter-status-select" className="w-full md:w-[170px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua Status</SelectItem>
            <SelectItem value="aktif">Aktif</SelectItem>
            <SelectItem value="hampir_berakhir">Hampir Berakhir</SelectItem>
            <SelectItem value="berakhir">Berakhir</SelectItem>
          </SelectContent>
        </Select>
        <Button data-testid="reset-filter-button" variant="outline" onClick={onReset} className="text-slate-600 hover:text-slate-900">
          <RotateCcw className="mr-2 h-4 w-4" />
          Reset
        </Button>
        <Button data-testid="export-csv-button" variant="outline" onClick={onExport} className="text-slate-600 hover:text-slate-900">
          <FileDown className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
        <Button data-testid="add-document-button" onClick={onAdd} className="col-span-2 bg-slate-900 text-white hover:bg-slate-800 md:col-span-1">
          <Plus className="mr-2 h-4 w-4" />
          Tambah Dokumen
        </Button>
      </div>
    </div>
  );
}
