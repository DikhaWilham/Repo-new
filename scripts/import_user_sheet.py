import re
import pandas as pd
from datetime import datetime, timezone, timedelta, date
from pymongo import MongoClient
import uuid

PATH = "/tmp/user_sheet.xlsx"
db = MongoClient("mongodb://localhost:27017")["test_database"]

def norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())

def parse_luasan(val):
    s = str(val or "").strip()
    if not s or s.lower() == "nan":
        return 0.0
    s = re.sub(r"(?i)m\s*2|m²|m$", "", s).replace(" ", "").strip()
    if not s:
        return 0.0
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0

def parse_money_first(val):
    s = str(val or "").strip()
    if not s or s.lower() == "nan":
        return 0.0
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)", s)
    if not m:
        return 0.0
    return float(m.group(1).replace(".", ""))

def parse_skema(val):
    s = norm(val)
    if not s:
        return "sewa"
    has_bagi = "bagi" in s or "%" in s
    has_sewa = "sewa" in s
    if has_bagi and has_sewa:
        return "hybrid"
    if has_bagi:
        return "bagi_hasil"
    return "sewa"

def parse_date(val):
    if val is None or str(val).strip().lower() in ("", "nan", "nat"):
        return None
    ts = pd.to_datetime(val, dayfirst=True, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.date().isoformat()

SHEETS = [
    ("CV MITRA", "CV Mitra", "BAGI HASIL / SEWA"),
    ("CV MULIA", "CV Mulia", "SEWA"),
    ("PT MITRA", "PT Mitra", "SEWA"),
    ("INTERN", "Intern", "SEWA"),
    ("SSP", "SSP", "SEWA"),
]

xl = pd.ExcelFile(PATH)
frames = {}
for sheet in xl.sheet_names:
    frames[sheet] = pd.read_excel(xl, sheet_name=sheet, dtype=str)

# cek overlap ANALIST dengan sheet utama
main_counters = set()
for sheet, _, _ in SHEETS:
    df = frames[sheet]
    col = next((c for c in df.columns if "KONTER" in c.upper() or "COUNTER" in c.upper()), None)
    if col:
        main_counters |= {norm(v) for v in df[col] if norm(v)}
an = frames.get("ANALIST")
if an is not None:
    an_col = next((c for c in an.columns if "KONTER" in c.upper() or "COUNTER" in c.upper()), None)
    an_counters = {norm(v) for v in an[an_col] if norm(v)}
    overlap = len(an_counters & main_counters)
    ratio = overlap / max(len(an_counters), 1)
    print(f"ANALIST: {len(an_counters)} counter unik, {overlap} sudah ada di sheet CV/PT/INTERN/SSP -> {'LEWATI (duplikat)' if ratio > 0.5 else 'SERTAKAN'}")

existing = {norm(d["nama_counter"]) for d in db.lease_docs.find({}, {"nama_counter": 1})}
print(f"Sudah ada di aplikasi: {existing}")

docs, skipped = [], []
now = datetime.now(timezone.utc).isoformat()
for sheet, cv_name, skema_col in SHEETS:
    df = frames[sheet]
    cols = {norm(c): c for c in df.columns}

    def col(*keys):
        for k in keys:
            for n, orig in cols.items():
                if k in n:
                    return orig
        return None

    c_nama = col("nama konter", "counter")
    c_area = col("area_name")
    c_brand = col("brand")
    c_skema = col(norm(skema_col)) or col("sewa", "bagi hasil")
    c_luas = col("luasan")
    c_sc = col("service charge")
    c_awal = col("tanggal awal")
    c_akhir = col("tanggal akhir")
    c_ket = col("keterangan")
    for i, row in df.iterrows():
        nama = str(row.get(c_nama) or "").strip() if c_nama else ""
        if not nama or nama.lower() == "nan":
            continue
        awal = parse_date(row.get(c_awal)) if c_awal else None
        akhir = parse_date(row.get(c_akhir)) if c_akhir else None
        if not awal or not akhir:
            skipped.append((sheet, nama, "tanggal tidak lengkap"))
            continue
        skema_text = str(row.get(c_skema) or "").strip() if c_skema else ""
        sc_text = str(row.get(c_sc) or "").strip() if c_sc else ""
        ket_parts = []
        if skema_text and skema_text.lower() != "nan":
            ket_parts.append(f"Skema: {skema_text}")
        if sc_text and sc_text.lower() != "nan" and not re.fullmatch(r"(?i)rp\.?\s*[\d.]+", sc_text):
            ket_parts.append(f"Service Charge: {sc_text}")
        ket_asli = str(row.get(c_ket) or "").strip() if c_ket else ""
        if ket_asli and ket_asli.lower() != "nan":
            ket_parts.append(ket_asli)
        reminder = (date.fromisoformat(akhir) - timedelta(days=60)).isoformat()
        key = norm(nama)
        if key in existing:
            skipped.append((sheet, nama, "sudah ada di aplikasi"))
            continue
        existing.add(key)
        docs.append({
            "_id": str(uuid.uuid4()),
            "nama_counter": nama.title(),
            "alamat_counter": (str(row.get(c_area)).strip().title() if c_area and str(row.get(c_area)).strip().lower() != "nan" else ""),
            "skema": parse_skema(skema_text),
            "nama_brand": (str(row.get(c_brand)).strip() if c_brand and str(row.get(c_brand)).strip().lower() != "nan" else ""),
            "nama_cv": cv_name,
            "luasan": parse_luasan(row.get(c_luas)) if c_luas else 0.0,
            "service_charge": parse_money_first(sc_text),
            "promo_levy": 0,
            "tanggal_mulai": awal,
            "tanggal_akhir": akhir,
            "reminder_date": reminder,
            "keterangan": " | ".join(ket_parts),
            "attachments": [],
            "created_by": "import-spreadsheet",
            "created_at": now,
            "updated_at": now,
        })

print(f"\nSiap diimport: {len(docs)} dokumen")
print(f"Dilewati: {len(skipped)}")
for s in skipped[:15]:
    print("  -", s)
if docs:
    db.lease_docs.insert_many(docs)
    print(f"\nBERHASIL: {len(docs)} dokumen masuk ke database")
