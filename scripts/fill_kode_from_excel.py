import re
import pandas as pd
from datetime import datetime, timezone
from pymongo import MongoClient
import uuid
import sys
sys.path.insert(0, "/app/backend")
import sheets_sync

PATH = "/tmp/mou_b.xlsx"
db = MongoClient("mongodb://localhost:27017")["test_database"]

def norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())

def pdate(val):
    if val is None or str(val).strip().lower() in ("", "nan", "nat"):
        return None
    ts = pd.to_datetime(val, dayfirst=True, errors="coerce")
    return None if pd.isna(ts) else ts.date().isoformat()

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

def parse_money(val):
    s = str(val or "").strip()
    if not s or s.lower() == "nan":
        return 0.0
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)", s)
    return float(m.group(1).replace(".", "")) if m else 0.0

def parse_skema(val):
    s = norm(val)
    has_bagi = "bagi" in s or "%" in s
    has_sewa = "sewa" in s
    if has_bagi and has_sewa:
        return "hybrid"
    if has_bagi:
        return "bagi_hasil"
    return "sewa"

SHEETS = [("CV MITRA", "CV Mitra"), ("CV MULIA", "CV Mulia"), ("PT MITRA", "PT Mitra"), ("INTERN", "Intern"), ("SSP", "SSP")]
ALIAS = {
    "manado trade center": "mtc manado",
    "happy time sidoarjo": "happy time lippo sidoarjo",
}

xl = pd.ExcelFile(PATH)
file_rows = []
for sheet, cv in SHEETS:
    df = pd.read_excel(xl, sheet_name=sheet, dtype=str)
    cols = {norm(c): c for c in df.columns}
    def col(*keys):
        for k in keys:
            for n, o in cols.items():
                if k in n:
                    return o
    c_nama, c_brand, c_kode = col("nama konter", "counter"), col("brand"), col("kode")
    c_area, c_skema = col("area_name"), col("sewa", "bagi hasil")
    c_luas, c_sc = col("luasan"), col("service charge")
    c_awal, c_akhir, c_ket = col("tanggal awal"), col("tanggal akhir"), col("keterangan")
    for _, row in df.iterrows():
        nama = str(row.get(c_nama) or "").strip() if c_nama else ""
        if not nama or nama.lower() == "nan":
            continue
        brand = str(row.get(c_brand) or "").strip() if c_brand else ""
        if brand.lower() == "nan":
            brand = ""
        kode = str(row.get(c_kode) or "").strip() if c_kode else ""
        if kode.lower() == "nan":
            kode = ""
        file_rows.append({
            "cv": cv, "nama": nama, "brand": brand, "kode": kode,
            "area": str(row.get(c_area) or "").strip() if c_area else "",
            "skema_text": str(row.get(c_skema) or "").strip() if c_skema else "",
            "luasan": parse_luasan(row.get(c_luas)) if c_luas else 0.0,
            "sc": parse_money(row.get(c_sc)) if c_sc else 0.0,
            "awal": pdate(row.get(c_awal)) if c_awal else None,
            "akhir": pdate(row.get(c_akhir)) if c_akhir else None,
            "ket": str(row.get(c_ket) or "").strip() if c_ket else "",
        })

docs = list(db.lease_docs.find({}))
by_pair = {(norm(d["nama_counter"]), norm(d.get("nama_brand", ""))): d for d in docs}
by_counter = {}
for d in docs:
    by_counter.setdefault(norm(d["nama_counter"]), []).append(d)

now = datetime.now(timezone.utc).isoformat()
filled, inserted, untouched = [], [], []

for r in file_rows:
    key = (norm(r["nama"]), norm(r["brand"]))
    doc = by_pair.get(key)
    if not doc:
        # coba counter-only (brand kosong di salah satu sisi)
        cands = by_counter.get(norm(r["nama"]), [])
        if not cands and norm(r["nama"]) in ALIAS:
            cands = by_counter.get(ALIAS[norm(r["nama"])], [])
        if len(cands) == 1 and (not norm(cands[0].get("nama_brand", "")) or not norm(r["brand"]) or norm(cands[0].get("nama_brand", "")) == norm(r["brand"])):
            doc = cands[0]
    if doc:
        update = {}
        if not doc.get("kode") and r["kode"]:
            update["kode"] = r["kode"]
        if not doc.get("luasan") and r["luasan"]:
            update["luasan"] = r["luasan"]
        if not doc.get("service_charge") and r["sc"]:
            update["service_charge"] = r["sc"]
        if not doc.get("alamat_counter") and r["area"] and r["area"].lower() != "nan":
            update["alamat_counter"] = r["area"].title()
        if update:
            update["updated_at"] = now
            db.lease_docs.update_one({"_id": doc["_id"]}, {"$set": update})
            filled.append((doc["nama_counter"], doc.get("nama_brand", ""), update.get("kode", "-")))
        else:
            untouched.append(doc["nama_counter"])
        continue
    # baris belum ada di app -> tambahkan (jangan ubah nama/data asli)
    ket_parts = []
    if r["skema_text"] and r["skema_text"].lower() != "nan":
        ket_parts.append(f"Skema: {r['skema_text']}")
    if r["ket"] and r["ket"].lower() != "nan":
        ket_parts.append(r["ket"])
    if not (r["awal"] and r["akhir"]):
        ket_parts.insert(0, "Status: Counter dalam proses MOU (tanggal perjanjian belum ditentukan)")
    new_doc = {
        "_id": str(uuid.uuid4()),
        "kode": r["kode"],
        "nama_counter": r["nama"].title(),
        "alamat_counter": (r["area"].title() if r["area"] and r["area"].lower() != "nan" else ""),
        "skema": parse_skema(r["skema_text"]),
        "nama_brand": r["brand"],
        "nama_cv": r["cv"],
        "luasan": r["luasan"],
        "service_charge": r["sc"],
        "promo_levy": 0,
        "tanggal_mulai": r["awal"] or "",
        "tanggal_akhir": r["akhir"] or "",
        "reminder_date": None,
        "keterangan": " | ".join(ket_parts),
        "progres_mou": "" if (r["awal"] and r["akhir"]) else "proses_mou",
        "attachments": [],
        "created_by": "import-spreadsheet",
        "created_at": now,
        "updated_at": now,
    }
    db.lease_docs.insert_one(new_doc)
    inserted.append((new_doc["nama_counter"], new_doc["nama_brand"], new_doc["kode"]))

print(f"kode/field kosong diisi: {len(filled)}")
for f in filled[:20]:
    print("  isi:", f)
print(f"baris baru ditambahkan: {len(inserted)}")
for i in inserted:
    print("  +", i)
print(f"tanpa perubahan: {len(untouched)}")
print("total DB:", db.lease_docs.count_documents({}))

sheets_sync.push_all(list(db.lease_docs.find()))
print("Google Sheet ikut ter-update")
