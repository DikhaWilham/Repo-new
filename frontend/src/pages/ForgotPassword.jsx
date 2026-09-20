import { useState } from "react";
import { Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, Loader2, MailCheck } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="forgot-password-page" className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Building2 className="h-5 w-5" />
          </div>
          <span className="font-headline text-lg font-bold text-slate-900">SewaKontrak Pro</span>
        </div>

        {sent ? (
          <div data-testid="forgot-password-success" className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-center">
            <MailCheck className="mx-auto h-10 w-10 text-emerald-600" />
            <h2 className="mt-4 font-headline text-xl font-semibold text-slate-900">Periksa email Anda</h2>
            <p className="mt-2 text-sm text-slate-600">
              Jika email tersebut terdaftar, tautan pengaturan ulang kata sandi telah dikirim. Tautan berlaku 1 jam.
            </p>
          </div>
        ) : (
          <>
            <h2 className="font-headline text-2xl font-bold tracking-tight text-slate-900">Lupa kata sandi</h2>
            <p className="mt-2 text-sm text-slate-500">Masukkan email Anda untuk menerima tautan pengaturan ulang.</p>
            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              {error && (
                <div data-testid="forgot-password-error" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" data-testid="forgot-password-email-input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@perusahaan.com" />
              </div>
              <Button data-testid="forgot-password-submit-button" type="submit" disabled={loading} className="w-full bg-slate-900 text-white hover:bg-slate-800">
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Kirim tautan pengaturan ulang
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
