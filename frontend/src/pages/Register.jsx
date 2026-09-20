import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, Loader2 } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
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
      await register(name, email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="register-page" className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Building2 className="h-5 w-5" />
          </div>
          <span className="font-headline text-lg font-bold text-slate-900">SewaKontrak Pro</span>
        </div>
        <h2 className="font-headline text-2xl font-bold tracking-tight text-slate-900">Buat akun baru</h2>
        <p className="mt-2 text-sm text-slate-500">Daftar untuk mulai memantau dokumen sewa counter.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          {error && (
            <div data-testid="register-error-message" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="name">Nama Lengkap</Label>
            <Input id="name" data-testid="register-name-input" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Nama Anda" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" data-testid="register-email-input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@perusahaan.com" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Kata Sandi</Label>
            <Input id="password" data-testid="register-password-input" type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Minimal 6 karakter" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm">Konfirmasi Kata Sandi</Label>
            <Input id="confirm" data-testid="register-confirm-input" type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Ulangi kata sandi" />
          </div>
          <Button data-testid="register-submit-button" type="submit" disabled={loading} className="w-full bg-slate-900 text-white hover:bg-slate-800">
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Daftar
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Sudah punya akun?{" "}
          <Link data-testid="login-link" to="/login" className="font-medium text-blue-600 hover:text-blue-800">
            Masuk di sini
          </Link>
        </p>
      </div>
    </div>
  );
}
