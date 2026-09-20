import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Konfirmasi kata sandi tidak cocok");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      toast.success("Kata sandi berhasil diperbarui. Silakan masuk.");
      navigate("/login", { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="reset-password-page" className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Building2 className="h-5 w-5" />
          </div>
          <span className="font-headline text-lg font-bold text-slate-900">SewaKontrak Pro</span>
        </div>

        {!token ? (
          <div data-testid="reset-password-invalid" className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
            Tautan pengaturan ulang tidak valid. Silakan minta tautan baru dari halaman lupa kata sandi.
          </div>
        ) : (
          <>
            <h2 className="font-headline text-2xl font-bold tracking-tight text-slate-900">Atur kata sandi baru</h2>
            <p className="mt-2 text-sm text-slate-500">Masukkan kata sandi baru untuk akun Anda.</p>
            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              {error && (
                <div data-testid="reset-password-error" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="password">Kata Sandi Baru</Label>
                <Input id="password" data-testid="reset-password-input" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Minimal 6 karakter" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm">Konfirmasi Kata Sandi Baru</Label>
                <Input id="confirm" data-testid="reset-password-confirm-input" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Ulangi kata sandi baru" />
              </div>
              <Button data-testid="reset-password-submit-button" type="submit" disabled={loading} className="w-full bg-slate-900 text-white hover:bg-slate-800">
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Simpan kata sandi baru
              </Button>
            </form>
          </>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link data-testid="back-to-login-link" to="/login" className="font-medium text-blue-600 hover:text-blue-800">
            Kembali ke halaman masuk
          </Link>
        </p>
      </div>
    </div>
  );
}
