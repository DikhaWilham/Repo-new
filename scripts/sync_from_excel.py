import re
import pandas as pd
from datetime import datetime, timezone, timedelta, date
from pymongo import MongoClient
import uuid

PATH = "/tmp/mou_new.xlsx"
db = MongoClient("mongodb://localhost:27017")["test_database"]

def norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())

def parse_date(val):
    if val is None or str(val).strip().lower() in ("", "nan", "nat"):
        return None
    ts = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return None if pd.isna(ts) else ts.date().isoformat()

def parse_skema(val):
    s = norm(val)
    has_bagi = "bagi" in s or "%" in s
    has_sewa = "sewa" in s
    if has_bagi and has_sewa:
        return "hybrid"
    if has_bagi:
        return "bagi_hasil"
    return "sewa"

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

SHEETS = [("CV MITRA", "CV Mitra"), ("CV MULIA", "CV Mulia"), ("PT MITRA", "PT Mitra"), ("INTERN", "Intern"), ("SSP", "SSP")]
xl = pd.ExcelFile(PATH)
now = datetime.now(timezone.utc).isoformat()

# Kumpulkan semua baris file
file_rows = []
for sheet, cv in SHEETS:
    df = pd.read_excel(xl, sheet_name=sheet, dtype=str)
    cols = {norm(c): c for c in df.columns}
    def col(*keys):
        for k in keys:
            for n, o in cols.items():
                if k in n:
                    return o
    c_nama, c_area, c_brand = col("nama konter", "counter"), col("area_name"), col("brand")
    c_skema, c_luas = col("sewa", "bagi hasil"), col("luasan")
    c_awal, c_akhir, c_ket = col("tanggal awal"), col("tanggal akhir"), col("keterangan")
    for _, row in df.iterrows():
        nama = str(row.get(c_nama) or "").strip() if c_nama else ""
        if not nama or nama.lower() == "nan":
            continue
        brand = str(row.get(c_brand) or "").strip() if c_brand else ""
        if brand.lower() == "nan":
            brand = ""
        file_rows.append({
            "sheet": sheet, "cv": cv, "nama": nama, "brand": brand,
            "area": str(row.get(c_area) or "").strip() if c_area else "",
            "skema_text": str(row.get(c_skema) or "").strip() if c_skema else "",
            "luasan": parse_luasan(row.get(c_luas)) if c_luas else 0.0,
            "awal": parse_date(row.get(c_awal)) if c_awal else None,
            "akhir": parse_date(row.get(c_akhir)) if c_akhir else None,
            "ket": str(row.get(c_ket) or "").strip() if c_ket else "",
        })

db_docs = list(db.lease_docs.find({}))
db_by_key = {(norm(d["nama_counter"]), norm(d.get("nama_brand", ""))): d for d in db_docs}
db_counters = {norm(d["nama_counter"]) for d in db_docs}

# BAGIAN 1: timpa tanggal dari Excel untuk baris yang cocok (keputusan pengguna: Excel yang benar)
# Dedup pasangan konter+brand di file: pakai baris dengan tanggal akhir paling baru
best = {}
for r in file_rows:
    key = (norm(r["nama"]), norm(r["brand"]))
    if key not in best or (r["akhir"] or "") > (best[key]["akhir"] or ""):
        best[key] = r
file_rows = list(best.values())

updated = 0
for r in file_rows:
    key = (norm(r["nama"]), norm(r["brand"]))
    doc = db_by_key.get(key)
    if not doc:
        continue
    if r["awal"] and r["akhir"] and (doc["tanggal_mulai"] != r["awal"] or doc["tanggal_akhir"] != r["akhir"]):
        reminder = (date.fromisoformat(r["akhir"]) - timedelta(days=60)).isoformat()
        db.lease_docs.update_one({"_id": doc["_id"]}, {"$set": {
            "tanggal_mulai": r["awal"], "tanggal_akhir": r["akhir"],
            "reminder_date": reminder, "updated_at": now,
        }})
        updated += 1
        print(f"  tanggal ditimpa: {r['nama']} | {r['brand']} -> {r['awal']} s/d {r['akhir']}")
print(f"BAGIAN 1 selesai: {updated} dokumen ditimpa mengikuti Excel")

# BAGIAN 2: baris tanpa tanggal -> masuk sebagai Proses MOU
# lewati yang nama konternya sudah ada di aplikasi (termasuk yang di-rename user: MTC Manado = Manado Trade Center)
ALIAS_SKIP = {"manado trade center": "mtc manado"}
inserted, dilewati = 0, []
for r in file_rows:
    if r["awal"] and r["akhir"]:
        continue  # punya tanggal = sudah ditangani
    n = norm(r["nama"])
    if n in db_counters or n in ALIAS_SKIP:
        dilewati.append((r["nama"], r["brand"], "sudah ada di aplikasi"))
        continue
    if not norm(r["brand"]):
        pass
    ket_parts = ["Status: Counter dalam proses MOU (tanggal perjanjian belum ditentukan)"]
    if r["skema_text"] and r["skema_text"].lower() != "nan":
        ket_parts.append(f"Skema: {r['skema_text']}")
    if r["ket"] and r["ket"].lower() != "nan":
        ket_parts.append(r["ket"])
    db.lease_docs.insert_one({
        "_id": str(uuid.uuid4()),
        "nama_counter": r["nama"].title(),
        "alamat_counter": (r["area"].title() if r["area"] and r["area"].lower() != "nan" else ""),
        "skema": parse_skema(r["skema_text"]),
        "nama_brand": r["brand"],
        "nama_cv": r["cv"],
        "luasan": r["luasan"],
        "service_charge": 0,
        "promo_levy": 0,
        "tanggal_mulai": r["awal"] or "",
        "tanggal_akhir": r["akhir"] or "",
        "reminder_date": None,
        "keterangan": " | ".join(ket_parts),
        "progres_mou": "proses_mou",
        "attachments": [],
        "created_by": "import-spreadsheet",
        "created_at": now,
        "updated_at": now,
    })
    db_counters.add(n)
    inserted += 1
    print(f"  + Proses MOU: {r['nama']} | {r['brand']} ({r['cv']})")
print(f"BAGIAN 2 selesai: {inserted} dokumen Proses MOU ditambahkan, {len(dilewati)} dilewati")
for d in dilewati:
    print("   dilewati:", d)
print("TOTAL AKHIR:", db.lease_docs.count_documents({}))
