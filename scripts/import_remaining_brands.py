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
existing = {(norm(d["nama_counter"]), norm(d.get("nama_brand", ""))) for d in db.lease_docs.find({}, {"nama_counter": 1, "nama_brand": 1})}
print(f"Pasangan konter+brand yang sudah ada: {len(existing)}")

docs, skipped = [], []
now = datetime.now(timezone.utc).isoformat()
for sheet, cv_name, skema_col in SHEETS:
    df = pd.read_excel(xl, sheet_name=sheet, dtype=str)
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
        brand = str(row.get(c_brand) or "").strip() if c_brand else ""
        if brand.lower() == "nan":
            brand = ""
        awal = parse_date(row.get(c_awal)) if c_awal else None
        akhir = parse_date(row.get(c_akhir)) if c_akhir else None
        if not awal or not akhir:
            skipped.append((sheet, nama, brand, "tanggal tidak lengkap"))
            continue
        key = (norm(nama), norm(brand))
        if key in existing:
            skipped.append((sheet, nama, brand, "sudah ada"))
            continue
        existing.add(key)
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
        docs.append({
            "_id": str(uuid.uuid4()),
            "nama_counter": nama.title(),
            "alamat_counter": (str(row.get(c_area)).strip().title() if c_area and str(row.get(c_area)).strip().lower() != "nan" else ""),
            "skema": parse_skema(skema_text),
            "nama_brand": brand,
            "nama_cv": cv_name,
            "luasan": parse_luasan(row.get(c_luas)) if c_luas else 0.0,
            "service_charge": parse_money_first(sc_text),
            "promo_levy": 0,
            "tanggal_mulai": awal,
            "tanggal_akhir": akhir,
            "reminder_date": (date.fromisoformat(akhir) - timedelta(days=60)).isoformat(),
            "keterangan": " | ".join(ket_parts),
            "attachments": [],
            "created_by": "import-spreadsheet",
            "created_at": now,
            "updated_at": now,
        })

print(f"Tambahan siap import: {len(docs)}")
for d in docs:
    print("  +", d["nama_counter"], "|", d["nama_brand"])
print(f"Dilewati: {len(skipped)}")
for s in skipped:
    print("  -", s)
if docs:
    db.lease_docs.insert_many(docs)
    print(f"BERHASIL menambah {len(docs)} dokumen")
