import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiErrorDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Clock, Eye, EyeOff, Loader2, UserCircle, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const { login, loginEmployee } = useAuth();
  const [mode, setMode] = useState("employee"); // "admin" | "employee"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [employees, setEmployees] = useState([]);
  const [selectedEmp, setSelectedEmp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (mode === "employee") {
      api.get("/auth/employee-options").then(({ data }) => setEmployees(data)).catch(() => {});
    }
  }, [mode]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "employee" && !selectedEmp) {
      setError("Silakan pilih nama Anda terlebih dahulu");
      return;
    }
    setLoading(true);
    try {
      if (mode === "admin") await login(email, password);
      else await loginEmployee(selectedEmp);
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full grid lg:grid-cols-2 bg-slate-50 dark:bg-[#090D16]">
      <div className="relative hidden lg:flex flex-col justify-between p-12 bg-slate-900 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "radial-gradient(circle at 20% 30%, #2563EB 0, transparent 45%), radial-gradient(circle at 80% 70%, #0ea5e9 0, transparent 40%)" }} />
        <div className="relative flex items-center gap-3">
          <div className="h-11 w-11 rounded-xl bg-blue-600 flex items-center justify-center">
            <Clock className="h-6 w-6" />
          </div>
          <span className="text-lg font-heading font-bold tracking-tight">Rekap Lembur</span>
        </div>
        <div className="relative space-y-4">
          <h1 className="text-4xl font-heading font-bold leading-tight">Kelola rekap lembur karyawan dengan rapi & otomatis.</h1>
          <p className="text-slate-300 text-base max-w-md">Absen masuk & pulang real-time dengan foto kamera dan lokasi GPS. Total lembur dihitung otomatis. Bisa dibuka di HP maupun PC.</p>
        </div>
        <div className="relative text-sm text-slate-400">© {new Date().getFullYear()} Sistem Rekap Lembur Karyawan</div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md space-y-8">
          <div className="lg:hidden flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center text-white">
              <Clock className="h-5 w-5" />
            </div>
            <span className="text-lg font-heading font-bold tracking-tight text-slate-900 dark:text-white">Rekap Lembur</span>
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-heading font-bold tracking-tight text-slate-900 dark:text-white">Masuk</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Pilih peran Anda untuk melanjutkan.</p>
          </div>

          <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl" data-testid="login-role-tabs">
            <button
              type="button"
              onClick={() => { setMode("employee"); setError(""); }}
              data-testid="tab-login-employee"
              className={`flex items-center justify-center gap-2 h-11 rounded-lg text-sm font-semibold transition-all ${mode === "employee" ? "bg-white dark:bg-slate-900 shadow text-blue-600 dark:text-blue-400" : "text-slate-500"}`}
            >
              <UserCircle className="h-4 w-4" /> Karyawan
            </button>
            <button
              type="button"
              onClick={() => { setMode("admin"); setError(""); }}
              data-testid="tab-login-admin"
              className={`flex items-center justify-center gap-2 h-11 rounded-lg text-sm font-semibold transition-all ${mode === "admin" ? "bg-white dark:bg-slate-900 shadow text-blue-600 dark:text-blue-400" : "text-slate-500"}`}
            >
              <ShieldCheck className="h-4 w-4" /> Admin
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
            {mode === "employee" ? (
              <div className="space-y-2">
                <Label>Pilih Nama Anda</Label>
                <Select value={selectedEmp} onValueChange={setSelectedEmp}>
                  <SelectTrigger className="h-11" data-testid="select-employee-login">
                    <SelectValue placeholder="Pilih nama karyawan..." />
                  </SelectTrigger>
                  <SelectContent>
                    {employees.map((e) => (
                      <SelectItem key={e.id} value={e.id} data-testid={`option-employee-${e.id}`}>{e.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-400">Nama Anda tidak ada di daftar? Minta admin menambahkannya.</p>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="email">Email Admin</Label>
                  <Input id="email" type="email" data-testid="input-email-login" placeholder="admin@perusahaan.com" value={email} onChange={(e) => setEmail(e.target.value)} required className="h-11" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input id="password" type={showPass ? "text" : "password"} data-testid="input-password-login" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required className="h-11 pr-11" />
                    <button type="button" onClick={() => setShowPass((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" data-testid="btn-toggle-password">
                      {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </>
            )}

            {error && (
              <div className="text-sm text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg px-3 py-2" data-testid="login-error">
                {error}
              </div>
            )}

            <Button type="submit" disabled={loading} className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-semibold" data-testid="btn-submit-login">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "employee" ? "Masuk sebagai Karyawan" : "Masuk sebagai Admin"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
