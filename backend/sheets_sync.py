import json
import os
import re
import logging
from datetime import date

logger = logging.getLogger(__name__)

SA_FILE = os.path.join(os.path.dirname(__file__), ".google_sa.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "sheets_config.json")

ENTITY_TABS = ["CV MITRA", "CV MULIA", "PT MITRA", "INTERN", "SSP", "LAINNYA"]
ENTITY_MAP = {"cv mitra": "CV MITRA", "cv mulia": "CV MULIA", "pt mitra": "PT MITRA", "intern": "INTERN", "ssp": "SSP"}

HEADERS = [
    "ID", "Nama Counter", "Alamat Counter", "Skema", "Nama Brand", "Nama CV/PT",
    "Luasan (m2)", "Service Charge (Rp)", "Promo Levy (Rp)",
    "Tanggal Mulai Sewa", "Tanggal Akhir Sewa", "Reminder Date",
    "Status", "Hari Tersisa", "Progres MOU", "Keterangan", "Terakhir Diupdate",
]

SKEMA_LABEL = {"sewa": "Sewa", "bagi_hasil": "Bagi Hasil", "hybrid": "Hybrid"}
PROGRES_LABEL = {
    "proses_mou": "Proses MOU",
    "mou_ditandatangani": "MOU Ditandatangani",
    "proses_fit_out": "Proses Fit Out / Renovasi",
    "akan_buka": "Akan Buka",
    "sudah_beroperasi": "Sudah Beroperasi",
}
PROGRES_FROM_LABEL = {v.lower(): k for k, v in PROGRES_LABEL.items()}


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def get_sheet_id():
    try:
        with open(CONFIG_FILE) as f:
            sid = json.load(f).get("sheet_id")
            if sid:
                return sid
    except Exception:
        pass
    return os.environ.get("GOOGLE_SHEETS_ID")


def set_sheet_id(sheet_id):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"sheet_id": sheet_id}, f)


def extract_sheet_id(url):
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", url or "")
    if m:
        return m.group(1)
    s = (url or "").strip()
    return s if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", s) else None


def get_client():
    import gspread
    return gspread.service_account(filename=SA_FILE)


def sheet_info(sid=None):
    sid = sid or get_sheet_id()
    sh = get_client().open_by_key(sid)
    return {"title": sh.title, "url": sh.url}


def verify_access(sid):
    get_client().open_by_key(sid)


def _entity_tab(nama_cv):
    return ENTITY_MAP.get(_norm(nama_cv), "LAINNYA")


def _status_days(tanggal_akhir):
    if not tanggal_akhir:
        return "Proses MOU", ""
    try:
        akhir = date.fromisoformat(str(tanggal_akhir)[:10])
    except Exception:
        return "Aktif", ""
    days = (akhir - date.today()).days
    if days < 0:
        return "Berakhir", days
    if days <= 30:
        return "Hampir Berakhir", days
    if days <= 90:
        return "Reminder 3 Bulan", days
    return "Aktif", days


def _doc_to_row(d):
    status_label, days = _status_days(d.get("tanggal_akhir"))
    return [
        d.get("_id", ""),
        d.get("nama_counter", ""),
        d.get("alamat_counter", ""),
        SKEMA_LABEL.get(d.get("skema", ""), d.get("skema", "")),
        d.get("nama_brand", ""),
        d.get("nama_cv", ""),
        d.get("luasan", 0),
        d.get("service_charge", 0),
        d.get("promo_levy", 0),
        d.get("tanggal_mulai", ""),
        d.get("tanggal_akhir", ""),
        d.get("reminder_date") or "",
        status_label,
        days,
        PROGRES_LABEL.get(d.get("progres_mou", ""), d.get("progres_mou", "")),
        d.get("keterangan", ""),
        str(d.get("updated_at", ""))[:19].replace("T", " "),
    ]


def push_all(docs):
    sid = get_sheet_id()
    if not sid:
        raise RuntimeError("Spreadsheet belum dikonfigurasi")
    sh = get_client().open_by_key(sid)
    by_tab = {t: [] for t in ENTITY_TABS}
    for d in docs:
        by_tab[_entity_tab(d.get("nama_cv", ""))].append(_doc_to_row(d))
    for tab in ENTITY_TABS:
        try:
            ws = sh.worksheet(tab)
        except Exception:
            ws = sh.add_worksheet(title=tab, rows=300, cols=20)
        ws.clear()
        ws.update(range_name="A1", values=[HEADERS] + by_tab[tab])
    return {"pushed": len(docs)}


def pull_all():
    sid = get_sheet_id()
    if not sid:
        raise RuntimeError("Spreadsheet belum dikonfigurasi")
    sh = get_client().open_by_key(sid)
    rows = []
    for tab in ENTITY_TABS:
        try:
            ws = sh.worksheet(tab)
        except Exception:
            continue
        values = ws.get_all_values()
        if len(values) < 2:
            continue
        headers = [str(h).strip() for h in values[0]]
        for r in values[1:]:
            if not any(str(c).strip() for c in r):
                continue
            rows.append({headers[i]: (r[i] if i < len(r) else "") for i in range(len(headers))})
    return rows


def _pdate(v):
    import pandas as pd
    s = str(v or "").strip()
    if not s:
        return ""
    ts = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return "" if pd.isna(ts) else ts.date().isoformat()


def _pnum(v):
    s = str(v or "").strip()
    if not s:
        return 0.0
    s = re.sub(r"(?i)rp", "", s).replace(" ", "").strip()
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = re.sub(r"[^\d,.\-]", "", s).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def row_to_doc_fields(r):
    skema_s = _norm(r.get("Skema", ""))
    if "bagi" in skema_s and "sewa" in skema_s:
        skema = "hybrid"
    elif "bagi" in skema_s:
        skema = "bagi_hasil"
    elif "hybrid" in skema_s:
        skema = "hybrid"
    else:
        skema = "sewa"
    progres_s = _norm(r.get("Progres MOU", ""))
    if progres_s in ("", "-"):
        progres = ""
    else:
        progres = PROGRES_FROM_LABEL.get(progres_s, str(r.get("Progres MOU", "")).strip())
    return {
        "nama_counter": str(r.get("Nama Counter", "")).strip(),
        "alamat_counter": str(r.get("Alamat Counter", "")).strip(),
        "skema": skema,
        "nama_brand": str(r.get("Nama Brand", "")).strip(),
        "nama_cv": str(r.get("Nama CV/PT", "")).strip(),
        "luasan": _pnum(r.get("Luasan (m2)", 0)),
        "service_charge": _pnum(r.get("Service Charge (Rp)", 0)),
        "promo_levy": _pnum(r.get("Promo Levy (Rp)", 0)),
        "tanggal_mulai": _pdate(r.get("Tanggal Mulai Sewa", "")),
        "tanggal_akhir": _pdate(r.get("Tanggal Akhir Sewa", "")),
        "reminder_date": _pdate(r.get("Reminder Date", "")) or None,
        "progres_mou": progres,
        "keterangan": str(r.get("Keterangan", "")).strip(),
    }
