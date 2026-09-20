# PRD — SewaKontrak Pro

## Problem Statement (asli)
"Bikinin aplikasi monitoring dokumen sewa menyewa yang meliputi, Nama Counter, Alamat Counter, Bagi Hasil atau Sewa, Nama Brand, Nama CV, Luasan, Service Charge, Promo Levy, Tanggal Mulai Sewa, Tanggal Akhir Sewa, sertakan remider date supaya dapat memantau kapan berakhir dan Keterangan untuk update progres, harus login dan dapat dibuka dari HP dan Web."

## Pilihan Pengguna
- Login email + password (JWT, httpOnly cookie)
- Reminder hanya tampilan di dashboard (badge & banner)
- Satu role saja (semua user full akses)
- Fitur tambahan: pencarian & filter, export CSV/Excel, upload lampiran dokumen
- Bahasa Indonesia penuh

## Arsitektur
- **Backend**: FastAPI (`/app/backend/server.py`), MongoDB (motor), koleksi: `users`, `lease_docs`, `login_attempts`, `password_reset_tokens`, `password_reset_requests`. Auth JWT (access 15 mnt + refresh 7 hari, httpOnly cookie, SameSite=None), bcrypt, brute-force lockout, forgot/reset password via email Emergent (EMERGENT_EMAIL_KEY), upload lampiran ke Emergent Object Storage (EMERGENT_LLM_KEY). Status kontrak dihitung server-side (aktif/hampir_berakhir/berakhir) berdasarkan reminder_date & tanggal_akhir. Seed: admin + 6 dokumen contoh saat startup.
- **Frontend**: React + Tailwind + shadcn/ui. Halaman: Login, Register, ForgotPassword, ResetPassword, Dashboard (statistik, banner reminder, toolbar filter/search/export, tabel desktop + kartu mobile, modal form, drawer detail + lampiran). Font: Plus Jakarta Sans (headline), IBM Plex Sans (body), JetBrains Mono (angka).

## Persona Pengguna
- Pemilik/pengelola usaha counter retail di mall yang perlu memantau masa sewa banyak counter sekaligus, dari HP maupun laptop.

## Kebutuhan Inti
1. Login wajib sebelum akses aplikasi.
2. CRUD dokumen sewa dengan field lengkap sesuai problem statement.
3. Reminder date + badge status untuk memantau kontrak yang akan berakhir.
4. Keterangan untuk update progres.
5. Responsif HP & web.

## Terimplementasi (Juni 2026)
- [x] Auth lengkap: register, login, logout, refresh token, forgot/reset password (email), lockout brute-force
- [x] Dashboard statistik: total/aktif/hampir berakhir/berakhir (kartu Total Luasan & Total Service Charge dihilangkan atas permintaan pengguna)
- [x] Banner reminder kontrak yang memasuki masa reminder
- [x] Pencarian (counter/brand/CV/alamat) + filter skema & status + reset filter
- [x] Export CSV (data terfilter, separator `;` kompatibel Excel id-ID, BOM UTF-8)
- [x] Upload/hapus/preview lampiran PDF & foto (object storage, maks 10 MB)
- [x] Form tambah/edit lengkap dengan validasi tanggal
- [x] Drawer detail: semua field, hari tersisa, keterangan, lampiran
- [x] Tabel desktop + kartu mobile, 6 data contoh realistis
- [x] Import massal dari spreadsheet CSV/Excel/.xls (preview, validasi per baris, template unduh, parsing tanggal & angka format Indonesia)
- [x] Fix: kata sandi admin sempat terganti via alur lupa kata sandi sehingga semua aksi gagal ("Tidak terautentikasi"); dikembalikan ke default dan tercatat di test_credentials.md
- [x] PWA: installable ke layar utama HP (manifest.json, service worker, ikon aplikasi kustom), judul & favicon aplikasi
- [x] Testing E2E: backend 11/11 pytest lulus, frontend semua alur terverifikasi (iteration_1.json)

## Backlog Prioritas
- **P0**: (kosong — semua kebutuhan inti terpenuhi)
- **P1**: Notifikasi email otomatis menjelang tanggal berakhir (butuh integrasi Resend terpisah); export Excel (.xlsx) native
- **P2**: Role Admin/Staff, riwayat perubahan keterangan (audit trail), pagination tabel, dark mode toggle, lampiran multi-file sekaligus di form tambah

## Next Tasks
- Kumpulkan feedback pengguna setelah pemakaian awal
- Jika diminta: pengingat email terjadwal (lihat skill scheduled-recurring-tasks + integrasi Resend)

## Import Data Pengguna (Sep 2026)
- File: inbound341833393433663285.xlsx (9 sheet) — diimport via script `/app/scripts/import_user_sheet.py` + `import_remaining_brands.py`
- Sheet diimport: CV MITRA, CV MULIA, PT MITRA, INTERN, SSP → **135 dokumen total** (124 + 11 konter multi-brand). Sheet ANALIST dilewati (duplikat 119/124), sheet Sertifikasi & BRAND bukan data sewa.
- Kunci dedup: nama konter + brand. Reminder date default: 60 hari sebelum tanggal akhir. Detail skema & service charge bertingkat disimpan di Keterangan.
- 10 baris dilewati karena tanggal tidak lengkap: HT Batam (Happy Time Junior), Happy Time Sidoarjo (Happy Train), Luwes Salatiga, HT Bontang (Mini Train), Paris Van Java (Funtopia), Manado Trade Center, Lippo Mall Manado, Artos Magelang, Lawu Plaza Madiun, Ramai Manyaran, Nakamura Semarang.

## Kredensial
Lihat `/app/memory/test_credentials.md` (admin: dikhawilham77@gmail.com).
