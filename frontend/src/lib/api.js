import axios from "axios";

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

export function formatApiError(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return e?.message || "Terjadi kesalahan. Silakan coba lagi.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((err) => (err && typeof err.msg === "string" ? err.msg : JSON.stringify(err))).filter(Boolean).join(" ");
  }
  if (typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default api;
