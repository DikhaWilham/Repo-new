import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Clock, Moon, Sun, LogOut, Users } from "lucide-react";

export default function HeaderNav({ onOpenEmployees }) {
  const { user, logout, isAdmin } = useAuth();
  const [dark, setDark] = useState(document.documentElement.classList.contains("dark"));

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  const initials = (user?.name || "?")
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-slate-200 dark:border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center text-white">
            <Clock className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <p className="text-sm sm:text-base font-heading font-bold tracking-tight text-slate-900 dark:text-white">Rekap Lembur</p>
            <p className="hidden sm:block text-xs text-slate-400">Karyawan Kantor</p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {isAdmin && (
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenEmployees}
              data-testid="btn-open-employee-sheet"
              className="gap-2"
            >
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">Karyawan</span>
            </Button>
          )}
          <button
            onClick={toggleTheme}
            className="h-9 w-9 rounded-lg border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            data-testid="btn-toggle-theme"
            aria-label="Ganti tema"
          >
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          <div className="flex items-center gap-2 pl-1 sm:pl-2">
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-xs font-semibold">
              {initials}
            </div>
            <div className="hidden sm:block leading-tight">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 max-w-[140px] truncate">{user?.name}</p>
              <span
                data-testid="badge-user-role"
                className={`text-[10px] font-semibold uppercase tracking-wider ${isAdmin ? "text-blue-600" : "text-emerald-600"}`}
              >
                {isAdmin ? "Admin" : "Karyawan"}
              </span>
            </div>
          </div>

          <Button variant="ghost" size="sm" onClick={logout} data-testid="btn-logout" className="text-slate-500 hover:text-red-600 gap-2">
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Keluar</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
