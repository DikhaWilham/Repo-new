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

## Belum Dikonfigurasi (Opsional)
- Google Sheets sync: butuh service account JSON di /app/repo-new/backend/.google_sa.json (endpoint /api/sheets/* gracefully return configured=false)
- Email password reset: memakai universal key sebagai EMERGENT_EMAIL_KEY, belum terverifikasi end-to-end

## Backlog
- P1: Google Sheets sync (butuh kredensial service account dari user)
- P2: Verifikasi email password reset end-to-end
- P2: Refactor server.py (918 baris) ke modul terpisah bila app berkembang
