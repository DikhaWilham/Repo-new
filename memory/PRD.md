# PRD — Aplikasi Rekap Lembur Karyawan

## Problem Statement
Aplikasi rekap lembur karyawan kantor (Bahasa Indonesia), bisa dibuka di HP & PC. Mencatat Nomor, Nama Karyawan, Jam Mulai Lembur, Jam Akhir Lembur, Total Lembur (otomatis), Lokasi/Hari saat Lembur, Keterangan Lembur, dan foto kondisi lembur. Ada sheet untuk edit/tambah karyawan. Karyawan hanya dapat mengedit jam mulai, jam akhir, lokasi, keterangan, dan upload foto miliknya sendiri; selain itu hanya admin yang dapat mengedit.

## Architecture
- Backend: FastAPI + MongoDB (motor). Auth JWT via httpOnly cookies (access 15m, refresh 7d), bcrypt hashing, brute-force lockout.
- Object storage: Emergent object storage untuk foto lembur, disajikan via `/api/files/{path}` (cookie auth).
- Frontend: React 19 + Tailwind + shadcn/ui, AuthContext, react-router. Responsive: tabel di desktop, kartu di mobile.
- Export: pandas + openpyxl (xlsx) / csv.

## User Personas
- **Admin HR**: kelola master karyawan, input/edit/hapus seluruh data lembur, filter & export.
- **Karyawan**: lihat data lembur sendiri, edit jam/lokasi/keterangan + upload foto pada rekap miliknya.

## Core Requirements (static)
1. Login email/password untuk admin & karyawan (akun karyawan dibuat admin).
2. Tabel rekap lembur per tanggal dengan Total Lembur otomatis (menangani lewat tengah malam).
3. Sheet manajemen karyawan (tambah/edit/hapus) — admin only.
4. Role-based edit: karyawan hanya field & rekap miliknya; admin penuh.
5. Upload & preview foto kondisi lembur.
6. Export Excel/CSV data terfilter.

## Implemented (2026-06)
- [x] Auth JWT httpOnly cookie + admin seeding (dikhawilham77@gmail.com) — 2026-06
- [x] Employee CRUD (admin only) — 2026-06
- [x] Overtime CRUD + auto total (midnight-safe) + role restrictions — 2026-06
- [x] Photo upload (object storage) + thumbnail + lightbox — 2026-06
- [x] Filters (karyawan, rentang tanggal, pencarian) — 2026-06
- [x] Export XLSX & CSV — 2026-06
- [x] Stats cards, responsive table + mobile cards, dark mode — 2026-06
- Tested: backend 15/15 pytest pass, frontend all flows pass (iteration_1).
- [x] Rekap Bulanan: endpoint /api/overtime/monthly-recap + kartu grafik bar per karyawan (recharts), summary total jam/karyawan/rekap, selector 12 bulan, admin-only — 2026-06. Tested pass (iteration_2).
- [x] Export PDF siap cetak (reportlab, landscape A4, tabel zebra, foto lembur tersemat hingga 40, baris TOTAL, info periode & waktu cetak) via GET /api/overtime/export?fmt=pdf — 2026-06. Diverifikasi render PDF visual.
- [x] Penyederhanaan data karyawan: hapus NIP/email/password — admin cukup isi Nama, Jabatan, Status Aktif; karyawan login cukup pilih nama (tanpa password) via /api/auth/employee-login; admin tetap email+password — 2026-06
- [x] Absensi real-time: tombol Absen Masuk & Absen Pulang dengan foto kamera wajib (capture), jam otomatis tercatat WIB (UTC+7), GPS otomatis tercatat, link Google Maps di tabel; foto masuk & pulang tampil di rekap; penolakan absen ganda — 2026-06

## Backlog / Remaining
- P2: Ganti native date input dengan shadcn Calendar untuk lokal ID.
- P2: DialogDescription untuk a11y (radix warning).
- P2: Bump token_version saat admin ganti password (invalidate sesi lama).

## Test Credentials
Lihat `/app/memory/test_credentials.md`.
