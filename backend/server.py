from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import hashlib
import secrets
import logging
import re
from datetime import datetime, timezone, timedelta, date
from html import escape
from urllib.parse import urlparse

import bcrypt
import jwt
import httpx
import requests
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks, UploadFile, File
from fastapi.responses import Response as RawResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Optional, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_ALGORITHM = "HS256"

EMAIL_BASE_URL = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip().rstrip("/") or "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME") or "SewaKontrak Pro"

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "sewakontrak-pro"
storage_key = None


def init_storage(force: bool = False):
    global storage_key
    if storage_key and not force:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------- Auth helpers ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, token_version: int = 0) -> str:
    payload = {"sub": user_id, "email": email, "ver": token_version,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    payload = {"sub": user_id, "ver": token_version,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")


def public_user(user: dict) -> dict:
    return {"id": user["_id"], "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "user")}


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Tidak terautentikasi")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Tipe token tidak valid")
        user = await db.users.find_one({"_id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="Pengguna tidak ditemukan")
        if payload.get("ver", 0) != user.get("token_version", 0):
            raise HTTPException(status_code=401, detail="Sesi berakhir")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token kedaluwarsa")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token tidak valid")


# ---------- Models ----------

class RegisterInput(BaseModel):
    name: str
    email: str
    password: str


class LoginInput(BaseModel):
    email: str
    password: str


class ForgotPasswordInput(BaseModel):
    email: str


class ResetPasswordInput(BaseModel):
    token: str
    password: str


class DocumentInput(BaseModel):
    nama_counter: str
    alamat_counter: str
    skema: str  # sewa | bagi_hasil | hybrid
    nama_brand: str
    nama_cv: str
    luasan: float
    service_charge: float
    promo_levy: float
    tanggal_mulai: str
    tanggal_akhir: str
    reminder_date: Optional[str] = None
    keterangan: Optional[str] = ""
    progres_mou: Optional[str] = ""


# ---------- Status computation ----------

def compute_status(doc: dict):
    today = date.today()
    try:
        akhir = date.fromisoformat(doc["tanggal_akhir"])
    except Exception:
        return "aktif", None
    days_left = (akhir - today).days
    if days_left < 0:
        return "berakhir", days_left
    if days_left <= 30:
        return "hampir_berakhir", days_left
    if days_left <= 90:
        return "reminder_3_bulan", days_left
    return "aktif", days_left


def serialize_doc(doc: dict) -> dict:
    status, days_left = compute_status(doc)
    attachments = [a for a in doc.get("attachments", []) if not a.get("is_deleted")]
    return {
        "id": doc["_id"],
        "nama_counter": doc["nama_counter"],
        "alamat_counter": doc["alamat_counter"],
        "skema": doc["skema"],
        "nama_brand": doc["nama_brand"],
        "nama_cv": doc["nama_cv"],
        "luasan": doc["luasan"],
        "service_charge": doc["service_charge"],
        "promo_levy": doc["promo_levy"],
        "tanggal_mulai": doc["tanggal_mulai"],
        "tanggal_akhir": doc["tanggal_akhir"],
        "reminder_date": doc.get("reminder_date"),
        "keterangan": doc.get("keterangan", ""),
        "progres_mou": doc.get("progres_mou", ""),
        "attachments": attachments,
        "status": status,
        "hari_tersisa": days_left,
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


# ---------- Auth endpoints ----------

@api_router.post("/auth/register")
async def register(input: RegisterInput, response: Response):
    email = input.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    if len(input.password) < 6:
        raise HTTPException(status_code=400, detail="Kata sandi minimal 6 karakter")
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "_id": user_id, "email": email, "name": input.name.strip(),
        "password_hash": hash_password(input.password), "role": "user",
        "token_version": 0, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    set_auth_cookies(response, create_access_token(user_id, email), create_refresh_token(user_id))
    return {"id": user_id, "email": email, "name": input.name.strip(), "role": "user"}


@api_router.post("/auth/login")
async def login(input: LoginInput, request: Request, response: Response):
    email = input.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    attempts = await db.login_attempts.count_documents({
        "identifier": identifier,
        "created_at": {"$gt": (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()},
    })
    if attempts >= 5:
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Coba lagi dalam 15 menit.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(input.password, user["password_hash"]):
        await db.login_attempts.insert_one({"identifier": identifier, "email": email, "created_at": datetime.now(timezone.utc).isoformat()})
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    await db.login_attempts.delete_many({"identifier": identifier})
    ver = user.get("token_version", 0)
    set_auth_cookies(response, create_access_token(user["_id"], email, ver), create_refresh_token(user["_id"], ver))
    return public_user(user)


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Berhasil keluar"}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@api_router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Tidak ada refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Tipe token tidak valid")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token tidak valid")
    user = await db.users.find_one({"_id": payload["sub"]})
    if not user or payload.get("ver", 0) != user.get("token_version", 0):
        raise HTTPException(status_code=401, detail="Sesi tidak valid")
    ver = user.get("token_version", 0)
    response.set_cookie(key="access_token", value=create_access_token(user["_id"], user["email"], ver),
                        httponly=True, secure=True, samesite="none", max_age=900, path="/")
    return {"message": "Token diperbarui"}


async def send_password_reset_email(to_email: str, token: str) -> bool:
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    link = f"{base}/reset-password?token={token}"
    if not EMAIL_KEY or EMAIL_KEY.startswith("{") or not base.startswith("https://"):
        if urlparse(base).hostname in ("localhost", "127.0.0.1", "::1"):
            logger.warning("Email not configured; password reset link: %s", link)
        else:
            logger.error("Password reset email not configured (EMERGENT_EMAIL_KEY / FRONTEND_URL)")
        return False
    brand = escape(EMAIL_FROM_NAME)
    html = (
        f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        f'<p>Kami menerima permintaan untuk mengatur ulang kata sandi akun {brand} Anda.</p>'
        f'<p><a href="{escape(link)}">Atur ulang kata sandi</a></p>'
        f'<p>Tautan ini berlaku 1 jam dan hanya dapat digunakan sekali. Jika Anda tidak memintanya, '
        f'abaikan email ini — kata sandi Anda tidak berubah.</p>'
        f'<p style="font-size:12px;color:#888">Dikirim oleh {brand}. Kami tidak pernah meminta kata sandi melalui email.</p>'
        f'</td></tr></table>'
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client_http:
            resp = await client_http.post(
                f"{EMAIL_BASE_URL}/api/v1/email/send",
                headers={"X-Email-Key": EMAIL_KEY},
                json={"to": [to_email], "subject": f"Atur ulang kata sandi {EMAIL_FROM_NAME} Anda",
                      "html": html, "from_name": EMAIL_FROM_NAME},
            )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        return False


@api_router.post("/auth/forgot-password")
async def forgot_password(input: ForgotPasswordInput, background_tasks: BackgroundTasks):
    generic = {"message": "Jika email tersebut terdaftar, tautan pengaturan ulang telah dikirim."}
    email = input.email.strip().lower()
    now = datetime.now(timezone.utc)
    recent = await db.password_reset_requests.count_documents({
        "email": email, "created_at": {"$gt": (now - timedelta(minutes=15)).isoformat()},
    })
    if recent >= 5:
        return generic
    await db.password_reset_requests.insert_one({"email": email, "created_at": now.isoformat()})
    user = await db.users.find_one({"email": email})
    if not user:
        return generic
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "user_id": user["_id"], "email": email,
        "expires_at": now + timedelta(hours=1), "used": False,
    })
    background_tasks.add_task(send_password_reset_email, user["email"], token)
    return generic


@api_router.post("/auth/reset-password")
async def reset_password(input: ResetPasswordInput):
    h = hashlib.sha256(input.token.encode()).hexdigest()
    claimed = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": h, "used": False, "expires_at": {"$gt": datetime.now(timezone.utc)}},
        {"$set": {"used": True}},
    )
    if not claimed:
        raise HTTPException(status_code=400, detail="Tautan tidak valid atau sudah kedaluwarsa")
    if len(input.password) < 6:
        raise HTTPException(status_code=400, detail="Kata sandi minimal 6 karakter")
    await db.users.update_one(
        {"_id": claimed["user_id"]},
        {"$set": {"password_hash": hash_password(input.password)}, "$inc": {"token_version": 1}},
    )
    await db.password_reset_tokens.delete_many({"user_id": claimed["user_id"], "used": False})
    await db.login_attempts.delete_many({"email": claimed["email"]})
    return {"message": "Kata sandi berhasil diperbarui"}


# ---------- Document endpoints ----------

@api_router.get("/documents")
async def list_documents(search: str = "", skema: str = "", status: str = "", nama_cv: str = "", user: dict = Depends(get_current_user)):
    query = {}
    if skema and skema != "all":
        query["skema"] = skema
    if nama_cv and nama_cv != "all":
        query["nama_cv"] = nama_cv
    if search:
        import re
        rx = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [{"nama_counter": rx}, {"nama_brand": rx}, {"nama_cv": rx}, {"alamat_counter": rx}]
    docs = await db.lease_docs.find(query).sort("tanggal_akhir", 1).to_list(2000)
    result = [serialize_doc(d) for d in docs]
    if status and status != "all":
        result = [d for d in result if d["status"] == status]
    return result


@api_router.get("/documents/stats")
async def document_stats(user: dict = Depends(get_current_user)):
    docs = await db.lease_docs.find().to_list(2000)
    serialized = [serialize_doc(d) for d in docs]
    stats = {
        "total": len(serialized),
        "aktif": sum(1 for d in serialized if d["status"] == "aktif"),
        "reminder_3_bulan": sum(1 for d in serialized if d["status"] == "reminder_3_bulan"),
        "hampir_berakhir": sum(1 for d in serialized if d["status"] == "hampir_berakhir"),
        "berakhir": sum(1 for d in serialized if d["status"] == "berakhir"),
        "total_luasan": sum(d["luasan"] for d in serialized),
        "total_service_charge": sum(d["service_charge"] for d in serialized),
        "daftar_cv": sorted({d["nama_cv"] for d in serialized if d["nama_cv"]}),
        "hampir_berakhir_list": [
            {"id": d["id"], "nama_counter": d["nama_counter"], "nama_brand": d["nama_brand"],
             "tanggal_akhir": d["tanggal_akhir"], "hari_tersisa": d["hari_tersisa"], "status": d["status"]}
            for d in serialized if d["status"] in ("hampir_berakhir", "reminder_3_bulan")
        ],
    }
    return stats


@api_router.post("/documents")
async def create_document(input: DocumentInput, user: dict = Depends(get_current_user)):
    if input.skema not in ("sewa", "bagi_hasil", "hybrid"):
        raise HTTPException(status_code=400, detail="Skema tidak valid")
    try:
        if date.fromisoformat(input.tanggal_akhir) < date.fromisoformat(input.tanggal_mulai):
            raise HTTPException(status_code=400, detail="Tanggal akhir tidak boleh sebelum tanggal mulai")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid")
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = input.model_dump()
    doc.update({"_id": doc_id, "attachments": [], "created_by": user["_id"], "created_at": now, "updated_at": now})
    await db.lease_docs.insert_one(doc)
    created = await db.lease_docs.find_one({"_id": doc_id})
    return serialize_doc(created)


@api_router.get("/documents/{doc_id}")
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.lease_docs.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return serialize_doc(doc)


@api_router.put("/documents/{doc_id}")
async def update_document(doc_id: str, input: DocumentInput, user: dict = Depends(get_current_user)):
    if input.skema not in ("sewa", "bagi_hasil", "hybrid"):
        raise HTTPException(status_code=400, detail="Skema tidak valid")
    try:
        if date.fromisoformat(input.tanggal_akhir) < date.fromisoformat(input.tanggal_mulai):
            raise HTTPException(status_code=400, detail="Tanggal akhir tidak boleh sebelum tanggal mulai")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format tanggal tidak valid")
    update = input.model_dump()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.lease_docs.update_one({"_id": doc_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    doc = await db.lease_docs.find_one({"_id": doc_id})
    return serialize_doc(doc)


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    result = await db.lease_docs.delete_one({"_id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return {"message": "Dokumen dihapus"}


# ---------- Spreadsheet import ----------

IMPORT_COLUMN_MAP = {
    "nama counter": "nama_counter", "counter": "nama_counter",
    "alamat counter": "alamat_counter", "alamat": "alamat_counter",
    "skema": "skema", "bagi hasil atau sewa": "skema", "jenis sewa": "skema", "jenis": "skema",
    "nama brand": "nama_brand", "brand": "nama_brand",
    "nama cv": "nama_cv", "nama cv/pt": "nama_cv", "cv": "nama_cv", "cv/pt": "nama_cv",
    "luasan": "luasan", "luasan m2": "luasan", "luas": "luasan", "luas m2": "luasan",
    "service charge": "service_charge", "service charge rp": "service_charge",
    "promo levy": "promo_levy", "promo levy rp": "promo_levy",
    "tanggal mulai sewa": "tanggal_mulai", "tanggal mulai": "tanggal_mulai", "mulai sewa": "tanggal_mulai",
    "tanggal akhir sewa": "tanggal_akhir", "tanggal akhir": "tanggal_akhir", "akhir sewa": "tanggal_akhir",
    "reminder date": "reminder_date", "reminder": "reminder_date",
    "keterangan": "keterangan", "keterangan / update progres": "keterangan", "keterangan progres": "keterangan",
    "progres mou": "progres_mou", "progres": "progres_mou",
}


def _norm_header(h):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/ ]", " ", str(h).strip().lower())).strip()


def _parse_skema(val):
    s = str(val or "").strip().lower()
    if not s:
        return "sewa", None
    if "bagi" in s:
        return "bagi_hasil", None
    if "hybrid" in s or "campur" in s:
        return "hybrid", None
    if "sewa" in s:
        return "sewa", None
    return "sewa", f"Skema '{val}' tidak dikenali"


def _parse_number(val):
    s = str(val or "").strip()
    if not s:
        return 0.0
    s = re.sub(r"(?i)rp", "", s)
    s = re.sub(r"(?i)m\s*2|m²", "", s).replace(" ", "").strip()
    if not s:
        return 0.0
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(val):
    import pandas as pd
    s = str(val or "").strip()
    if not s:
        return None
    ts = pd.to_datetime(s, dayfirst=True, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.date().isoformat()


@api_router.post("/documents/import")
async def import_documents(file: UploadFile = File(...), dry: bool = False, user: dict = Depends(get_current_user)):
    import io as _io
    import pandas as pd
    filename = file.filename or ""
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 5 MB untuk import. Bagi file menjadi beberapa bagian.")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    df = None

    def _try_csv():
        nonlocal df
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(_io.BytesIO(data), sep=None, engine="python", dtype=str, encoding=enc)
                return True
            except Exception:
                continue
        return False

    def _try_excel():
        nonlocal df
        try:
            df = pd.read_excel(_io.BytesIO(data), dtype=str)
            return True
        except Exception:
            return False

    if ext in ("xlsx", "xls"):
        ok = _try_excel() or _try_csv()
    elif ext == "csv":
        ok = _try_csv() or _try_excel()
    else:
        ok = _try_excel() or _try_csv()
    if not ok or df is None:
        raise HTTPException(status_code=400, detail="File tidak dapat dibaca. Simpan sebagai CSV atau Excel (.xlsx), atau gunakan template yang disediakan.")
    if len(df) > 2000:
        raise HTTPException(status_code=400, detail=f"File berisi {len(df)} baris. Maksimal 2000 baris per import — bagi file menjadi beberapa bagian.")

    df = df.fillna("")
    colmap = {}
    for col in df.columns:
        field = IMPORT_COLUMN_MAP.get(_norm_header(col))
        if field and field not in colmap.values():
            colmap[col] = field
    if "nama_counter" not in colmap.values():
        raise HTTPException(status_code=400, detail="Kolom 'Nama Counter' tidak ditemukan. Sesuaikan nama kolom dengan template.")

    now = datetime.now(timezone.utc).isoformat()
    docs, errors, total = [], [], 0
    for idx, row in df.iterrows():
        rec = {}
        for col, field in colmap.items():
            v = row[col]
            rec[field] = "" if v is None else str(v).strip()
        if not rec.get("nama_counter"):
            continue
        total += 1
        mulai = _parse_date(rec.get("tanggal_mulai"))
        akhir = _parse_date(rec.get("tanggal_akhir"))
        reminder = _parse_date(rec.get("reminder_date"))
        skema, skema_err = _parse_skema(rec.get("skema"))
        problems = []
        if not mulai:
            problems.append("Tanggal Mulai kosong/tidak valid")
        if not akhir:
            problems.append("Tanggal Akhir kosong/tidak valid")
        if skema_err:
            problems.append(skema_err)
        if mulai and akhir and akhir < mulai:
            problems.append("Tanggal Akhir sebelum Tanggal Mulai")
        if problems:
            errors.append({"row": int(idx) + 2, "nama_counter": rec["nama_counter"], "message": "; ".join(problems)})
            continue
        docs.append({
            "_id": str(uuid.uuid4()),
            "nama_counter": rec["nama_counter"],
            "alamat_counter": rec.get("alamat_counter", ""),
            "skema": skema,
            "nama_brand": rec.get("nama_brand", ""),
            "nama_cv": rec.get("nama_cv", ""),
            "luasan": _parse_number(rec.get("luasan")) or 0,
            "service_charge": _parse_number(rec.get("service_charge")) or 0,
            "promo_levy": _parse_number(rec.get("promo_levy")) or 0,
            "tanggal_mulai": mulai,
            "tanggal_akhir": akhir,
            "reminder_date": reminder,
            "keterangan": rec.get("keterangan", ""),
            "attachments": [],
            "created_by": user["_id"],
            "created_at": now,
            "updated_at": now,
        })

    imported = 0
    if not dry and docs:
        await db.lease_docs.insert_many(docs)
        imported = len(docs)
    return {
        "total_rows": total,
        "valid": len(docs),
        "imported": imported,
        "errors": errors,
        "preview": [
            {k: v for k, v in d.items() if k not in ("_id", "attachments", "created_by", "created_at", "updated_at")}
            for d in docs[:20]
        ],
    }


ALLOWED_EXT = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@api_router.post("/documents/{doc_id}/attachments")
async def upload_attachment(doc_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    doc = await db.lease_docs.find_one({"_id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Format file tidak didukung (PDF/JPG/PNG/WEBP)")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 10 MB")
    path = f"{APP_NAME}/uploads/{doc_id}/{uuid.uuid4()}.{ext}"
    try:
        result = put_object(path, data, ALLOWED_EXT[ext])
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=502, detail="Gagal mengunggah file ke penyimpanan")
    attachment = {
        "id": str(uuid.uuid4()), "storage_path": result["path"],
        "filename": file.filename, "content_type": ALLOWED_EXT[ext],
        "size": result["size"], "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.lease_docs.update_one({"_id": doc_id}, {"$push": {"attachments": attachment}})
    return attachment


@api_router.delete("/documents/{doc_id}/attachments/{att_id}")
async def delete_attachment(doc_id: str, att_id: str, user: dict = Depends(get_current_user)):
    result = await db.lease_docs.update_one(
        {"_id": doc_id, "attachments.id": att_id},
        {"$set": {"attachments.$.is_deleted": True}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lampiran tidak ditemukan")
    return {"message": "Lampiran dihapus"}


@api_router.get("/files/{path:path}")
async def download_file(path: str, user: dict = Depends(get_current_user)):
    record = await db.lease_docs.find_one({"attachments.storage_path": path, "attachments.is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    try:
        data, content_type = get_object(path)
    except Exception:
        raise HTTPException(status_code=404, detail="File tidak ditemukan di penyimpanan")
    return RawResponse(content=data, media_type=content_type)


@api_router.get("/")
async def root():
    return {"message": "SewaKontrak Pro API"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Startup ----------

async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "_id": str(uuid.uuid4()), "email": admin_email, "name": "Admin",
            "password_hash": hash_password(admin_password), "role": "admin",
            "token_version": 0, "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})


async def seed_sample_docs():
    if await db.lease_docs.count_documents({}) > 0:
        return
    today = date.today()

    def d(offset):
        return (today + timedelta(days=offset)).isoformat()

    samples = [
        {
            "nama_counter": "Counter Chatime Grand Indonesia",
            "alamat_counter": "Grand Indonesia Mall, Lt. 3A Unit 12, Jakarta Pusat",
            "skema": "sewa", "nama_brand": "Chatime", "nama_cv": "CV Kawan Lama Sejahtera",
            "luasan": 12.5, "service_charge": 2500000, "promo_levy": 500000,
            "tanggal_mulai": d(-340), "tanggal_akhir": d(25), "reminder_date": d(-5),
            "keterangan": "Menunggu draft perpanjangan dari pihak mall.",
        },
        {
            "nama_counter": "Counter Wardah Beauty Mall Kelapa Gading",
            "alamat_counter": "Mall Kelapa Gading 2, Lt. G Unit B-07, Jakarta Utara",
            "skema": "bagi_hasil", "nama_brand": "Wardah", "nama_cv": "CV Cahaya Kosmetik",
            "luasan": 8.0, "service_charge": 1200000, "promo_levy": 300000,
            "tanggal_mulai": d(-200), "tanggal_akhir": d(165), "reminder_date": d(135),
            "keterangan": "Bagi hasil 12% dari omzet bulanan. Performa stabil.",
        },
        {
            "nama_counter": "Counter Erigo Summarecon Bekasi",
            "alamat_counter": "Summarecon Mall Bekasi, Lt. 1 Unit F-21, Bekasi",
            "skema": "hybrid", "nama_brand": "Erigo", "nama_cv": "CV Busana Nusantara",
            "luasan": 15.0, "service_charge": 3000000, "promo_levy": 750000,
            "tanggal_mulai": d(-100), "tanggal_akhir": d(18), "reminder_date": d(-12),
            "keterangan": "Negosiasi perpanjangan, minta peninjauan service charge.",
        },
        {
            "nama_counter": "Counter Janji Jiwa Tunjungan Plaza",
            "alamat_counter": "Tunjungan Plaza 4, Lt. 2 Unit C-05, Surabaya",
            "skema": "sewa", "nama_brand": "Janji Jiwa", "nama_cv": "CV Jiwa Kopi Abadi",
            "luasan": 10.0, "service_charge": 1800000, "promo_levy": 400000,
            "tanggal_mulai": d(-30), "tanggal_akhir": d(335), "reminder_date": d(305),
            "keterangan": "Kontrak baru, deposit sudah dibayar.",
        },
        {
            "nama_counter": "Counter Samsung Experience Plaza Senayan",
            "alamat_counter": "Plaza Senayan, Lt. 2 Unit E-11, Jakarta Selatan",
            "skema": "sewa", "nama_brand": "Samsung", "nama_cv": "CV Elektronik Prima",
            "luasan": 20.0, "service_charge": 5500000, "promo_levy": 1000000,
            "tanggal_mulai": d(-400), "tanggal_akhir": d(-35), "reminder_date": d(-65),
            "keterangan": "Kontrak berakhir. Proses serah terima unit ke pihak mall.",
        },
        {
            "nama_counter": "Counter Dum Dum Thai Drinks Pakuwon Mall",
            "alamat_counter": "Pakuwon Mall, Lt. 2 Unit D-03, Surabaya Barat",
            "skema": "bagi_hasil", "nama_brand": "Dum Dum", "nama_cv": "CV Minuman Sehati",
            "luasan": 6.5, "service_charge": 900000, "promo_levy": 250000,
            "tanggal_mulai": d(-150), "tanggal_akhir": d(215), "reminder_date": d(185),
            "keterangan": "Bagi hasil 10%. Evaluasi omzet per kuartal.",
        },
    ]
    now = datetime.now(timezone.utc).isoformat()
    for s in samples:
        s.update({"_id": str(uuid.uuid4()), "attachments": [], "created_at": now, "updated_at": now})
    await db.lease_docs.insert_many(samples)


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.login_attempts.create_index("email")
    await db.login_attempts.create_index("identifier")
    await db.password_reset_requests.create_index("email")
    await db.password_reset_requests.create_index("created_at", expireAfterSeconds=900)
    await db.lease_docs.create_index("nama_counter")
    await seed_admin()
    await seed_sample_docs()
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
