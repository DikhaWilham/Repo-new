import { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import LoginPage from "@/pages/LoginPage";
import Dashboard from "@/pages/Dashboard";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#090D16]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
          <p className="text-sm text-slate-500">Memuat...</p>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function LoginRoute() {
  const { user } = useAuth();
  if (user) return <Navigate to="/" replace />;
  return <LoginPage />;
}

function App() {
  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored === "dark") document.documentElement.classList.add("dark");
  }, []);

  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginRoute />} />
            <Route
              path="/"
              element={
                <Protected>
                  <Dashboard />
                </Protected>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </AuthProvider>
    </div>
  );
}

export default App;
