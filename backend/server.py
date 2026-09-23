from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import io
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

import bcrypt
import jwt
import requests
import pandas as pd
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict, EmailStr
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
api_router = APIRouter(prefix="/api")

JWT_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# Object storage
# ---------------------------------------------------------------------------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "rekap-lembur"
storage_key = None

MIME_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}


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
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
PyObjectId = Annotated[str, BeforeValidator(str)]


class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    nip: Optional[str] = ""
    jabatan: Optional[str] = ""
    active: bool = True


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    nip: Optional[str] = None
    jabatan: Optional[str] = None
    active: Optional[bool] = None


class OvertimeCreate(BaseModel):
    employee_id: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    location: Optional[str] = ""
    note: Optional[str] = ""


class OvertimeUpdate(BaseModel):
    employee_id: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    note: Optional[str] = None


class LoginInput(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(user_id: str, email: str, token_version: int = 0) -> str:
    payload = {"sub": user_id, "email": email, "ver": token_version, "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    payload = {"sub": user_id, "ver": token_version, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")


def public_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user.get("role", "employee"),
        "nip": user.get("nip", ""),
        "jabatan": user.get("jabatan", ""),
        "active": user.get("active", True),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Belum login")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token tidak valid")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User tidak ditemukan")
        if payload.get("ver", 0) != user.get("token_version", 0):
            raise HTTPException(status_code=401, detail="Sesi berakhir")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token kedaluwarsa")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token tidak valid")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Hanya admin yang dapat melakukan aksi ini")
    return user


# ---------------------------------------------------------------------------
# Brute force
# ---------------------------------------------------------------------------
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


async def is_locked(email: str, ip: str) -> bool:
    identifier = f"{ip}:{email}"
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOCK_MINUTES)
    count = await db.login_attempts.count_documents({"identifier": identifier, "created_at": {"$gt": cutoff.isoformat()}})
    return count >= MAX_ATTEMPTS


async def record_fail(email: str, ip: str):
    await db.login_attempts.insert_one({"identifier": f"{ip}:{email}", "email": email, "created_at": datetime.now(timezone.utc).isoformat()})


async def clear_attempts(email: str, ip: str):
    await db.login_attempts.delete_many({"identifier": f"{ip}:{email}"})


# ---------------------------------------------------------------------------
# Overtime calc
# ---------------------------------------------------------------------------
def calc_total_minutes(start: str, end: str) -> int:
    try:
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        diff = end_min - start_min
        if diff < 0:
            diff += 24 * 60  # crosses midnight
        return diff
    except Exception:
        return 0


def format_total(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h and m:
        return f"{h} Jam {m} Menit"
    if h:
        return f"{h} Jam"
    return f"{m} Menit"


def serialize_overtime(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "employee_id": doc.get("employee_id", ""),
        "employee_name": doc.get("employee_name", ""),
        "date": doc.get("date", ""),
        "start_time": doc.get("start_time", ""),
        "end_time": doc.get("end_time", ""),
        "total_minutes": doc.get("total_minutes", 0),
        "total_label": format_total(doc.get("total_minutes", 0)),
        "location": doc.get("location", ""),
        "note": doc.get("note", ""),
        "photo_path": doc.get("photo_path"),
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
    }


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@api_router.post("/auth/login")
async def login(payload: LoginInput, request: Request, response: Response):
    email = payload.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    if await is_locked(email, ip):
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan. Coba lagi dalam 15 menit.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        await record_fail(email, ip)
        raise HTTPException(status_code=401, detail="Email atau password salah")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Akun tidak aktif. Hubungi admin.")
    await clear_attempts(email, ip)
    ver = user.get("token_version", 0)
    set_auth_cookies(response, create_access_token(str(user["_id"]), email, ver), create_refresh_token(str(user["_id"]), ver))
    return public_user(user)


@api_router.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logout berhasil"}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@api_router.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Belum login")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token tidak valid")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user or payload.get("ver", 0) != user.get("token_version", 0):
            raise HTTPException(status_code=401, detail="Sesi berakhir")
        ver = user.get("token_version", 0)
        response.set_cookie(key="access_token", value=create_access_token(str(user["_id"]), user["email"], ver), httponly=True, secure=True, samesite="none", max_age=900, path="/")
        return public_user(user)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token tidak valid")


# ---------------------------------------------------------------------------
# Employee endpoints (admin managed)
# ---------------------------------------------------------------------------
@api_router.get("/employees")
async def list_employees(user: dict = Depends(get_current_user)):
    docs = await db.users.find({"role": "employee"}).sort("name", 1).to_list(1000)
    return [public_user(d) for d in docs]


@api_router.post("/employees")
async def create_employee(payload: EmployeeCreate, admin: dict = Depends(require_admin)):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "name": payload.name,
        "role": "employee",
        "nip": payload.nip or "",
        "jabatan": payload.jabatan or "",
        "active": payload.active,
        "token_version": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    return public_user(doc)


@api_router.put("/employees/{emp_id}")
async def update_employee(emp_id: str, payload: EmployeeUpdate, admin: dict = Depends(require_admin)):
    user = await db.users.find_one({"_id": ObjectId(emp_id), "role": "employee"})
    if not user:
        raise HTTPException(status_code=404, detail="Karyawan tidak ditemukan")
    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.email is not None:
        new_email = payload.email.lower().strip()
        existing = await db.users.find_one({"email": new_email, "_id": {"$ne": ObjectId(emp_id)}})
        if existing:
            raise HTTPException(status_code=400, detail="Email sudah terdaftar")
        updates["email"] = new_email
    if payload.nip is not None:
        updates["nip"] = payload.nip
    if payload.jabatan is not None:
        updates["jabatan"] = payload.jabatan
    if payload.active is not None:
        updates["active"] = payload.active
    if payload.password:
        updates["password_hash"] = hash_password(payload.password)
        updates["token_version"] = user.get("token_version", 0) + 1
    if updates:
        await db.users.update_one({"_id": ObjectId(emp_id)}, {"$set": updates})
    if "name" in updates:
        await db.overtime.update_many({"employee_id": emp_id}, {"$set": {"employee_name": updates["name"]}})
    fresh = await db.users.find_one({"_id": ObjectId(emp_id)})
    return public_user(fresh)


@api_router.delete("/employees/{emp_id}")
async def delete_employee(emp_id: str, admin: dict = Depends(require_admin)):
    res = await db.users.delete_one({"_id": ObjectId(emp_id), "role": "employee"})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Karyawan tidak ditemukan")
    await db.overtime.delete_many({"employee_id": emp_id})
    return {"message": "Karyawan dihapus"}


# ---------------------------------------------------------------------------
# Overtime endpoints
# ---------------------------------------------------------------------------
async def build_overtime_query(user: dict, employee_id: Optional[str], date_from: Optional[str], date_to: Optional[str], search: Optional[str]):
    query = {}
    if user.get("role") != "admin":
        query["employee_id"] = str(user["_id"])
    elif employee_id:
        query["employee_id"] = employee_id
    if date_from or date_to:
        dq = {}
        if date_from:
            dq["$gte"] = date_from
        if date_to:
            dq["$lte"] = date_to
        query["date"] = dq
    if search:
        query["$or"] = [
            {"note": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
            {"employee_name": {"$regex": search, "$options": "i"}},
        ]
    return query


@api_router.get("/overtime")
async def list_overtime(
    user: dict = Depends(get_current_user),
    employee_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
):
    query = await build_overtime_query(user, employee_id, date_from, date_to, search)
    docs = await db.overtime.find(query).sort("date", -1).to_list(2000)
    return [serialize_overtime(d) for d in docs]


@api_router.post("/overtime")
async def create_overtime(payload: OvertimeCreate, admin: dict = Depends(require_admin)):
    emp = await db.users.find_one({"_id": ObjectId(payload.employee_id)})
    if not emp:
        raise HTTPException(status_code=404, detail="Karyawan tidak ditemukan")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "employee_id": payload.employee_id,
        "employee_name": emp.get("name", ""),
        "date": payload.date,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "total_minutes": calc_total_minutes(payload.start_time, payload.end_time),
        "location": payload.location or "",
        "note": payload.note or "",
        "photo_path": None,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.overtime.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize_overtime(doc)


@api_router.put("/overtime/{ot_id}")
async def update_overtime(ot_id: str, payload: OvertimeUpdate, user: dict = Depends(get_current_user)):
    ot = await db.overtime.find_one({"_id": ObjectId(ot_id)})
    if not ot:
        raise HTTPException(status_code=404, detail="Data lembur tidak ditemukan")
    is_admin = user.get("role") == "admin"
    if not is_admin and ot.get("employee_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Anda hanya dapat mengedit data lembur milik sendiri")
    updates = {}
    # Fields both roles may edit
    for field in ["start_time", "end_time", "location", "note"]:
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val
    # Admin-only fields
    if is_admin:
        if payload.date is not None:
            updates["date"] = payload.date
        if payload.employee_id is not None and payload.employee_id != ot.get("employee_id"):
            emp = await db.users.find_one({"_id": ObjectId(payload.employee_id)})
            if not emp:
                raise HTTPException(status_code=404, detail="Karyawan tidak ditemukan")
            updates["employee_id"] = payload.employee_id
            updates["employee_name"] = emp.get("name", "")
    start = updates.get("start_time", ot.get("start_time"))
    end = updates.get("end_time", ot.get("end_time"))
    updates["total_minutes"] = calc_total_minutes(start, end)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.overtime.update_one({"_id": ObjectId(ot_id)}, {"$set": updates})
    fresh = await db.overtime.find_one({"_id": ObjectId(ot_id)})
    return serialize_overtime(fresh)


@api_router.delete("/overtime/{ot_id}")
async def delete_overtime(ot_id: str, admin: dict = Depends(require_admin)):
    res = await db.overtime.delete_one({"_id": ObjectId(ot_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Data lembur tidak ditemukan")
    return {"message": "Data lembur dihapus"}


@api_router.post("/overtime/{ot_id}/photo")
async def upload_photo(ot_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ot = await db.overtime.find_one({"_id": ObjectId(ot_id)})
    if not ot:
        raise HTTPException(status_code=404, detail="Data lembur tidak ditemukan")
    if user.get("role") != "admin" and ot.get("employee_id") != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Anda hanya dapat mengupload foto lembur milik sendiri")
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg").lower()
    if ext not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Format foto harus JPG, PNG, WEBP, atau GIF")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran foto maksimal 10MB")
    path = f"{APP_NAME}/uploads/{ot.get('employee_id')}/{uuid.uuid4()}.{ext}"
    content_type = file.content_type or MIME_TYPES[ext]
    result = put_object(path, data, content_type)
    stored = result["path"]
    await db.files.insert_one({
        "storage_path": stored,
        "content_type": content_type,
        "original_filename": file.filename,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.overtime.update_one({"_id": ObjectId(ot_id)}, {"$set": {"photo_path": stored, "updated_at": datetime.now(timezone.utc).isoformat()}})
    fresh = await db.overtime.find_one({"_id": ObjectId(ot_id)})
    return serialize_overtime(fresh)


@api_router.get("/files/{path:path}")
async def download_file(path: str, request: Request, auth: Optional[str] = Query(None)):
    # Auth via cookie (same-origin img) or optional query token
    try:
        await get_current_user(request)
    except HTTPException:
        if not auth:
            raise
        try:
            jwt.decode(auth, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token tidak valid")
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    data, content_type = get_object(path)
    return Response(content=data, media_type=record.get("content_type", content_type))


# ---------------------------------------------------------------------------
# Monthly recap per employee
# ---------------------------------------------------------------------------
@api_router.get("/overtime/monthly-recap")
async def monthly_recap(user: dict = Depends(get_current_user), month: Optional[str] = Query(None)):
    """Total overtime per employee for a given month (YYYY-MM). Defaults to current month."""
    now = datetime.now(timezone.utc)
    target = month if month and len(month) == 7 else now.strftime("%Y-%m")
    query = {"date": {"$regex": f"^{target}"}}
    if user.get("role") != "admin":
        query["employee_id"] = str(user["_id"])
    docs = await db.overtime.find(query).to_list(5000)

    by_employee = {}
    for d in docs:
        emp_id = d.get("employee_id", "")
        entry = by_employee.setdefault(emp_id, {"employee_name": d.get("employee_name", ""), "total_minutes": 0, "count": 0, "with_photo": 0})
        entry["total_minutes"] += d.get("total_minutes", 0)
        entry["count"] += 1
        if d.get("photo_path"):
            entry["with_photo"] += 1

    employees = [
        {
            "employee_id": emp_id,
            "employee_name": e["employee_name"],
            "total_minutes": e["total_minutes"],
            "total_hours": round(e["total_minutes"] / 60, 1),
            "total_label": format_total(e["total_minutes"]),
            "count": e["count"],
            "with_photo": e["with_photo"],
        }
        for emp_id, e in by_employee.items()
    ]
    employees.sort(key=lambda x: x["total_minutes"], reverse=True)
    return {
        "month": target,
        "employees": employees,
        "grand_total_minutes": sum(e["total_minutes"] for e in employees),
        "grand_total_label": format_total(sum(e["total_minutes"] for e in employees)),
        "total_employees": len(employees),
        "total_records": len(docs),
    }


# ---------------------------------------------------------------------------
# Stats & Export
# ---------------------------------------------------------------------------
@api_router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    query = {}
    if user.get("role") != "admin":
        query["employee_id"] = str(user["_id"])
    docs = await db.overtime.find(query).to_list(5000)
    now = datetime.now(timezone.utc)
    month_prefix = now.strftime("%Y-%m")
    today = now.strftime("%Y-%m-%d")
    total_month = sum(d.get("total_minutes", 0) for d in docs if str(d.get("date", "")).startswith(month_prefix))
    today_count = sum(1 for d in docs if d.get("date") == today)
    with_photo = sum(1 for d in docs if d.get("photo_path"))
    employees_month = len({d.get("employee_id") for d in docs if str(d.get("date", "")).startswith(month_prefix)})
    return {
        "total_month_label": format_total(total_month),
        "total_month_hours": round(total_month / 60, 1),
        "employees_month": employees_month,
        "today_count": today_count,
        "with_photo": with_photo,
        "total_records": len(docs),
    }


@api_router.get("/overtime/export")
async def export_overtime(
    request: Request,
    fmt: str = Query("xlsx"),
    employee_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    auth: Optional[str] = Query(None),
):
    # allow cookie or query token (download links can't set headers)
    try:
        user = await get_current_user(request)
    except HTTPException:
        if not auth:
            raise
        payload = jwt.decode(auth, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Token tidak valid")

    query = await build_overtime_query(user, employee_id, date_from, date_to, search)
    docs = await db.overtime.find(query).sort("date", -1).to_list(5000)
    rows = []
    for i, d in enumerate(docs, 1):
        rows.append({
            "No": i,
            "Nama Karyawan": d.get("employee_name", ""),
            "Tanggal Lembur": d.get("date", ""),
            "Jam Mulai": d.get("start_time", ""),
            "Jam Akhir": d.get("end_time", ""),
            "Total Lembur": format_total(d.get("total_minutes", 0)),
            "Lokasi / Hari": d.get("location", ""),
            "Keterangan": d.get("note", ""),
            "Ada Foto": "Ya" if d.get("photo_path") else "Tidak",
        })
    df = pd.DataFrame(rows, columns=["No", "Nama Karyawan", "Tanggal Lembur", "Jam Mulai", "Jam Akhir", "Total Lembur", "Lokasi / Hari", "Keterangan", "Ada Foto"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    if fmt == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=rekap_lembur_{stamp}.csv"})
    if fmt == "pdf":
        buf = io.BytesIO()
        styles = getSampleStyleSheet()
        cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
        cell_c = ParagraphStyle("cellc", parent=cell, alignment=1)
        head = ParagraphStyle("head", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
        bold = ParagraphStyle("bold", parent=cell, fontName="Helvetica-Bold")
        bold_c = ParagraphStyle("boldc", parent=bold, alignment=1)

        elements = []
        elements.append(Paragraph("Rekap Lembur Karyawan", ParagraphStyle("title2", parent=styles["Title"], fontSize=16, fontName="Helvetica-Bold")))
        info_parts = []
        if date_from or date_to:
            info_parts.append(f"Periode: {date_from or '...'} s/d {date_to or '...'}")
        info_parts.append(f"Dicetak: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC")
        elements.append(Paragraph(" &middot; ".join(info_parts), ParagraphStyle("meta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748B"))))
        elements.append(Spacer(1, 0.35 * cm))

        data_rows = [[Paragraph(h, head) for h in ["No", "Nama Karyawan", "Tanggal", "Mulai", "Akhir", "Total", "Lokasi / Hari", "Keterangan", "Foto"]]]
        photo_count = 0
        for i, d in enumerate(docs, 1):
            photo_cell = Paragraph("-", cell_c)
            if d.get("photo_path") and photo_count < 40:
                try:
                    img_bytes, _ = get_object(d["photo_path"])
                    iw, ih = ImageReader(io.BytesIO(img_bytes)).getSize()
                    w, h = 2.2 * cm, (2.2 * cm * ih / iw if iw else 1.6 * cm)
                    if h > 2.2 * cm:
                        h = 2.2 * cm
                        w = h * iw / ih
                    photo_cell = RLImage(io.BytesIO(img_bytes), width=w, height=h)
                    photo_count += 1
                except Exception as e:
                    logger.warning(f"PDF photo skipped: {e}")
            data_rows.append([
                Paragraph(str(i), cell_c),
                Paragraph(str(d.get("employee_name", "")), cell),
                Paragraph(str(d.get("date", "")), cell_c),
                Paragraph(str(d.get("start_time", "")), cell_c),
                Paragraph(str(d.get("end_time", "")), cell_c),
                Paragraph(format_total(d.get("total_minutes", 0)), cell_c),
                Paragraph(str(d.get("location", "") or "-"), cell),
                Paragraph(str(d.get("note", "") or "-"), cell),
                photo_cell,
            ])
        total_all = sum(d.get("total_minutes", 0) for d in docs)
        data_rows.append(["", Paragraph("TOTAL", bold), "", "", "", Paragraph(format_total(total_all), bold_c), Paragraph(f"{len(docs)} rekap", bold_c), "", ""])

        table = Table(data_rows, colWidths=[0.9*cm, 3.2*cm, 2.4*cm, 1.5*cm, 1.5*cm, 2.6*cm, 3.6*cm, 6.2*cm, 2.6*cm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        doc_pdf = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.2*cm, rightMargin=1.2*cm, topMargin=1.4*cm, bottomMargin=1.2*cm)
        doc_pdf.build(elements)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=rekap_lembur_{stamp}.pdf"})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rekap Lembur")
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=rekap_lembur_{stamp}.xlsx"})


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    admin_name = os.environ.get("ADMIN_NAME", "Admin")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "name": admin_name,
            "role": "admin",
            "nip": "",
            "jabatan": "Administrator",
            "active": True,
            "token_version": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Admin seeded")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}})


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("email")
    await db.overtime.create_index("employee_id")
    await db.overtime.create_index("date")
    await seed_admin()
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"), "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
