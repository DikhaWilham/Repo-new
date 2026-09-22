# PRD — SewaKontrak Pro (Import dari Repo-new)

## Original Problem Statement
Import project dari GitHub repository: https://github.com/DikhaWilham/Repo-new.git, branch main. Setup dan install semua dependencies-nya. Lanjutan: setup sampai 100% berjalan normal, konfigurasi EMERGENT_LLM_KEY, preview URL bisa diakses.

## Tentang Aplikasi
SewaKontrak Pro — monitoring dokumen sewa counter (mall/retail): masa sewa, reminder tanggal berakhir, service charge, promo levy, skema sewa/bagi hasil/hybrid. Stack: FastAPI + React 19 + MongoDB.

## Arsitektur Deployment
- Source: /app/repo-new (clone branch main)
- Symlink: /app/backend -> /app/repo-new/backend, /app/frontend -> /app/repo-new/frontend
- Template asli dipindah ke /app/backend-template & /app/frontend-template
- Supervisor (readonly config) tetap menunjuk /app/backend & /app/frontend
- Preview URL: https://repo-sync-deploy-4.preview.emergentagent.com
- DB: repo_new (MongoDB lokal), admin + 6 sample docs auto-seed saat startup

## Yang Sudah Diimplementasikan
- 2026-09-22: Clone repo, install deps backend (fix litellm sha256 fragment) & frontend (yarn), .env backend+frontend
- 2026-09-22: Konfigurasi EMERGENT_LLM_KEY + EMERGENT_EMAIL_KEY (universal key), FRONTEND_URL untuk CORS, ADMIN_EMAIL/ADMIN_PASSWORD (dikhawilham77@gmail.com / SewaKontrak123!)
- 2026-09-22: Symlink swap supervisor, storage init OK, testing agent e2e PASS (backend 11/11, frontend 9/9): login, dashboard 6 docs, CRUD, register, logout
- 2026-09-22: Import Excel "MONITORING MOU B.xlsx" → 148 dokumen (CV MITRA 93, CV MULIA 30, PT MITRA 14, INTERN 9, SSP 2); sheet ANALIST/Sertifikasi Air Coaster/Sertifikasi OSS & Area/BRAND di-skip; script: /app/repo-new/scripts/import_monitoring_mou.py
- 2026-09-22: Schema diperluas (no, area_name, skema_detail, bagi_hasil_persen, sewa_rupiah, luasan_text, service_charge_text) — backward compatible
- 2026-09-22: UI baru: halaman awal hanya daftar No + Nama Konter + ikon mata; klik mata → panel detail lengkap; form create/edit dengan input kondisional (Bagi Hasil → persen, Sewa → rupiah, Hybrid → keduanya); export CSV kolom baru
- 2026-09-22: Testing iterasi 2 PASS (backend 16/16, frontend semua E2E pass)
- 2026-09-22: Sorting daftar konter: reminder (hampir_berakhir/reminder_3_bulan) paling atas, lalu abjad A-Z, nomor urut 1..N dari atas
- 2026-09-22: Sinkronisasi otomatis App → Excel: endpoint GET /api/documents/export-excel selalu generate xlsx fresh dari DB (5 sheet per CV, kolom sama seperti Excel asli + SISA HARI) + tombol "Export Excel" di toolbar. User menolak setup Google Sheets → sync Sheets→App via tombol Import bila perlu
- 2026-09-22: Testing iterasi 3 PASS (backend 22/22 setelah fix data drift kode ADA BOGOR, frontend semua E2E pass)
- 2026-09-22: Badge reminder "N hari lagi" tampil di sebelah nama konter di daftar depan — hanya untuk konter dalam masa reminder (amber ≤30 hari, emerald ≤90 hari), data-testid reminder-badge-{id}

## Belum Dikonfigurasi (Opsional)
- Google Sheets sync: butuh service account JSON di /app/repo-new/backend/.google_sa.json (endpoint /api/sheets/* gracefully return configured=false)
- Email password reset: memakai universal key sebagai EMERGENT_EMAIL_KEY, belum terverifikasi end-to-end

## Backlog
- P1: Google Sheets sync (butuh kredensial service account dari user)
- P2: Verifikasi email password reset end-to-end
- P2: Refactor server.py (918 baris) ke modul terpisah bila app berkembang
