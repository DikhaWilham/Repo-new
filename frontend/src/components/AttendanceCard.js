import { useState, useEffect, useCallback, useRef } from "react";
import api, { formatApiErrorDetail } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { LogIn, LogOut, Camera, MapPin, Loader2, CheckCircle2, Clock } from "lucide-react";

function getPosition() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve(null),
      { timeout: 8000, maximumAge: 60000 }
    );
  });
}

export default function AttendanceCard({ user, onChanged }) {
  const [today, setToday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null); // "masuk" | "pulang"
  const masukRef = useRef();
  const pulangRef = useRef();

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/attendance/today");
      setToday(data);
    } catch (e) {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submit = async (kind, file) => {
    if (!file) return;
    setBusy(kind);
    try {
      toast.info("Mengambil lokasi GPS...");
      const pos = await getPosition();
      const fd = new FormData();
      fd.append("file", file);
      if (pos) {
        fd.append("lat", String(pos.lat));
        fd.append("lng", String(pos.lng));
      }
      const { data } = await api.post(`/attendance/${kind}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setToday(data);
      if (pos) toast.success(`Absen ${kind} tercatat dengan lokasi GPS`);
      else toast.success(`Absen ${kind} tercatat (lokasi GPS tidak tersedia)`);
      onChanged?.();
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || "Gagal absen");
    } finally {
      setBusy(null);
      if (masukRef.current) masukRef.current.value = "";
      if (pulangRef.current) pulangRef.current.value = "";
    }
  };

  const handlePick = (kind) => (e) => {
    const f = e.target.files?.[0];
    if (f) submit(kind, f);
  };

  const masukDone = !!today?.start_time;
  const pulangDone = !!today?.end_time;

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 sm:p-6" data-testid="attendance-card">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-9 w-9 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 flex items-center justify-center">
          <Clock className="h-4 w-4 text-emerald-600" />
        </div>
        <div>
          <h2 className="text-lg font-heading font-semibold tracking-tight text-slate-800 dark:text-slate-100">Absen Lembur Hari Ini</h2>
          <p className="text-xs text-slate-500">Foto diambil langsung dari kamera, jam & lokasi GPS tercatat otomatis</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="h-6 w-6 animate-spin text-slate-400" /></div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className={`rounded-lg p-3 border ${masukDone ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900" : "bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700"}`}>
              <p className="text-xs text-slate-500 flex items-center gap-1"><LogIn className="h-3 w-3" /> Absen Masuk</p>
              <p className="text-lg font-heading font-bold font-mono text-slate-900 dark:text-white mt-1" data-testid="text-masuk-time">
                {masukDone ? today.start_time : "--:--"}
              </p>
              {masukDone && today.gps_start_lat != null && (
                <a href={`https://www.google.com/maps?q=${today.gps_start_lat},${today.gps_start_lng}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 flex items-center gap-1 mt-1" data-testid="link-gps-masuk">
                  <MapPin className="h-3 w-3" /> Lihat lokasi
                </a>
              )}
            </div>
            <div className={`rounded-lg p-3 border ${pulangDone ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-900" : "bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700"}`}>
              <p className="text-xs text-slate-500 flex items-center gap-1"><LogOut className="h-3 w-3" /> Absen Pulang</p>
              <p className="text-lg font-heading font-bold font-mono text-slate-900 dark:text-white mt-1" data-testid="text-pulang-time">
                {pulangDone ? today.end_time : "--:--"}
              </p>
              {pulangDone && today.gps_end_lat != null && (
                <a href={`https://www.google.com/maps?q=${today.gps_end_lat},${today.gps_end_lng}`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 flex items-center gap-1 mt-1" data-testid="link-gps-pulang">
                  <MapPin className="h-3 w-3" /> Lihat lokasi
                </a>
              )}
            </div>
          </div>

          {pulangDone && (
            <div className="flex items-center gap-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 px-4 py-3">
              <CheckCircle2 className="h-4 w-4 text-blue-600" />
              <span className="text-sm text-slate-600 dark:text-slate-300">Total Lembur Hari Ini:</span>
              <span className="text-sm font-semibold font-mono text-blue-700 dark:text-blue-400" data-testid="text-total-today">{today.total_label}</span>
            </div>
          )}

          <input ref={masukRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handlePick("masuk")} data-testid="input-photo-masuk" />
          <input ref={pulangRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handlePick("pulang")} data-testid="input-photo-pulang" />

          <div className="grid grid-cols-2 gap-3">
            <Button
              onClick={() => masukRef.current?.click()}
              disabled={masukDone || busy !== null}
              className="h-12 gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold disabled:opacity-50"
              data-testid="btn-absen-masuk"
            >
              {busy === "masuk" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              Absen Masuk
            </Button>
            <Button
              onClick={() => pulangRef.current?.click()}
              disabled={!masukDone || pulangDone || busy !== null}
              className="h-12 gap-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold disabled:opacity-50"
              data-testid="btn-absen-pulang"
            >
              {busy === "pulang" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              Absen Pulang
            </Button>
          </div>
          <p className="text-xs text-slate-400 text-center">Menekan tombol akan membuka kamera untuk mengambil foto bukti lembur.</p>
        </div>
      )}
    </div>
  );
}
