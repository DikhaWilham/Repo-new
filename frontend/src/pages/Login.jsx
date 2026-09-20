import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, Loader2 } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="login-page" className="min-h-screen grid lg:grid-cols-2 bg-slate-50">
      <div className="hidden lg:block relative">
        <img
          src="https://images.unsplash.com/photo-1441986300917-64674bd600d8?crop=entropy&cs=srgb&fm=jpg&q=85"
          alt="Counter retail modern"
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-slate-900/70" />
        <div className="relative z-10 flex h-full flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 backdrop-blur">
              <Building2 className="h-5 w-5" />
            </div>
            <span className="font-headline text-lg font-bold tracking-tight">SewaKontrak Pro</span>
          </div>
          <div>
            <h1 className="font-headline text-4xl font-bold leading-tight tracking-tight">
              Pantau seluruh dokumen sewa counter Anda dalam satu dasbor.
            </h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-300">
              Kelola masa sewa, reminder tanggal berakhir, service charge, promo levy, dan progres setiap counter — dari HP maupun web.
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Building2 className="h-5 w-5" />
            </div>
            <span className="font-headline text-lg font-bold text-slate-900">SewaKontrak Pro</span>
          </div>
          <h2 className="font-headline text-2xl font-bold tracking-tight text-slate-900">Masuk ke akun Anda</h2>
          <p className="mt-2 text-sm text-slate-500">Kelola dokumen sewa menyewa counter Anda.</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div data-testid="login-error-message" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                data-testid="login-email-input"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nama@perusahaan.com"
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Kata Sandi</Label>
                <Link data-testid="forgot-password-link" to="/forgot-password" className="text-xs font-medium text-blue-600 hover:text-blue-800">
                  Lupa kata sandi?
                </Link>
              </div>
              <Input
                id="password"
                data-testid="login-password-input"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            <Button data-testid="login-submit-button" type="submit" disabled={loading} className="w-full bg-slate-900 text-white hover:bg-slate-800">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Masuk
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Belum punya akun?{" "}
            <Link data-testid="register-link" to="/register" className="font-medium text-blue-600 hover:text-blue-800">
              Daftar sekarang
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
