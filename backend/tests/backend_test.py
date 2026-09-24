"""Backend tests for Rekap Lembur app - schema v2 (employee name-only login + attendance)."""
import os
import io
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://worklog-mobile-14.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "dikhawilham77@gmail.com"
ADMIN_PASSWORD = "admin123"

# 1x1 PNG bytes (valid)
PNG_1x1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
)


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def temp_employee(admin):
    """Create a fresh employee (no email/password fields in schema v2)."""
    name = f"TEST_Emp_{int(time.time())}"
    r = admin.post(f"{API}/employees", json={"name": name, "jabatan": "QA", "active": True}, timeout=30)
    assert r.status_code == 200, r.text
    emp = r.json()
    yield emp
    admin.delete(f"{API}/employees/{emp['id']}", timeout=30)


@pytest.fixture(scope="module")
def emp_session(temp_employee):
    s = requests.Session()
    r = s.post(f"{API}/auth/employee-login", json={"employee_id": temp_employee["id"]}, timeout=30)
    assert r.status_code == 200, r.text
    return s


# ---------- Auth (admin) ----------
def test_auth_me_admin(admin):
    r = admin.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert body["email"] == ADMIN_EMAIL


def test_auth_login_wrong_password():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-xx"}, timeout=30)
    assert r.status_code == 401


def test_auth_no_cookie_returns_401():
    r = requests.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 401


# ---------- Employee login (name-only) ----------
def test_employee_options_public():
    """Endpoint must be accessible without auth for login page."""
    r = requests.get(f"{API}/auth/employee-options", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Each option must have only id + name (no sensitive info)
    for e in data:
        assert set(e.keys()) == {"id", "name"}


def test_employee_login_success(temp_employee):
    s = requests.Session()
    r = s.post(f"{API}/auth/employee-login", json={"employee_id": temp_employee["id"]}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "employee"
    assert body["name"] == temp_employee["name"]
    # cookie should be set
    r2 = s.get(f"{API}/auth/me", timeout=30)
    assert r2.status_code == 200


def test_employee_login_invalid_id():
    s = requests.Session()
    r = s.post(f"{API}/auth/employee-login", json={"employee_id": "not-a-valid-oid"}, timeout=30)
    assert r.status_code == 400


def test_employee_login_not_found():
    s = requests.Session()
    # valid ObjectId format but does not exist
    r = s.post(f"{API}/auth/employee-login", json={"employee_id": "000000000000000000000000"}, timeout=30)
    assert r.status_code == 404


# ---------- Employees CRUD (new simplified schema) ----------
def test_employees_list(admin):
    r = admin.get(f"{API}/employees", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_create_simplified_employee_and_persist(admin):
    """Schema v2: only name/jabatan/active; server auto-generates email."""
    name = f"TEST_Simplified_{int(time.time())}"
    r = admin.post(f"{API}/employees", json={"name": name, "jabatan": "Staff", "active": True}, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == name
    assert body["jabatan"] == "Staff"
    assert body["active"] is True
    assert body["role"] == "employee"
    assert body["email"].endswith("@lembur.local")  # auto-generated
    emp_id = body["id"]

    # GET verifies persistence
    r = admin.get(f"{API}/employees", timeout=30)
    assert any(e["id"] == emp_id for e in r.json())

    # Update jabatan
    r = admin.put(f"{API}/employees/{emp_id}", json={"jabatan": "Senior Staff"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["jabatan"] == "Senior Staff"

    # Delete
    r = admin.delete(f"{API}/employees/{emp_id}", timeout=30)
    assert r.status_code == 200


def test_employee_cannot_create_employee(emp_session):
    r = emp_session.post(f"{API}/employees", json={"name": "Hack", "jabatan": "x", "active": True}, timeout=30)
    assert r.status_code == 403


# ---------- Attendance (absen masuk/pulang) ----------
def test_attendance_flow_masuk_then_pulang(admin):
    """Full flow: create fresh emp, employee-login, absen masuk, absen pulang."""
    name = f"TEST_Att_{int(time.time())}"
    r = admin.post(f"{API}/employees", json={"name": name, "jabatan": "QA", "active": True}, timeout=30)
    assert r.status_code == 200
    emp = r.json()
    emp_id = emp["id"]

    try:
        s = requests.Session()
        r = s.post(f"{API}/auth/employee-login", json={"employee_id": emp_id}, timeout=30)
        assert r.status_code == 200

        # today = None initially
        r = s.get(f"{API}/attendance/today", timeout=30)
        assert r.status_code == 200
        assert r.json() is None

        # Absen masuk with lat/lng
        files = {"file": ("in.png", io.BytesIO(PNG_1x1), "image/png")}
        r = s.post(f"{API}/attendance/masuk", files=files, data={"lat": "-6.2", "lng": "106.8"}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["start_time"], "start_time must be recorded"
        assert body["photo_path"], "photo_path must be recorded"
        assert body["gps_start_lat"] == -6.2
        assert body["gps_start_lng"] == 106.8
        assert body["source"] == "absen"
        assert not body["end_time"]

        # Duplicate absen masuk -> 400
        files = {"file": ("in2.png", io.BytesIO(PNG_1x1), "image/png")}
        r = s.post(f"{API}/attendance/masuk", files=files, timeout=60)
        assert r.status_code == 400

        # Absen pulang
        files = {"file": ("out.png", io.BytesIO(PNG_1x1), "image/png")}
        r = s.post(f"{API}/attendance/pulang", files=files, data={"lat": "-6.3", "lng": "106.9"}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["end_time"]
        assert body["photo_end_path"]
        assert body["gps_end_lat"] == -6.3
        assert body["total_minutes"] >= 0

        # /attendance/today reflects
        r = s.get(f"{API}/attendance/today", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["start_time"] and d["end_time"]
        assert d["photo_path"] and d["photo_end_path"]
    finally:
        admin.delete(f"{API}/employees/{emp_id}", timeout=30)


def test_attendance_pulang_before_masuk_rejected(admin):
    name = f"TEST_NoMasuk_{int(time.time())}"
    r = admin.post(f"{API}/employees", json={"name": name, "active": True}, timeout=30)
    emp_id = r.json()["id"]
    try:
        s = requests.Session()
        s.post(f"{API}/auth/employee-login", json={"employee_id": emp_id}, timeout=30)
        files = {"file": ("out.png", io.BytesIO(PNG_1x1), "image/png")}
        r = s.post(f"{API}/attendance/pulang", files=files, timeout=60)
        assert r.status_code == 400
    finally:
        admin.delete(f"{API}/employees/{emp_id}", timeout=30)


def test_attendance_masuk_without_gps_still_works(admin):
    """Geolocation denied -> lat/lng omitted, absen still succeeds."""
    name = f"TEST_NoGPS_{int(time.time())}"
    r = admin.post(f"{API}/employees", json={"name": name, "active": True}, timeout=30)
    emp_id = r.json()["id"]
    try:
        s = requests.Session()
        s.post(f"{API}/auth/employee-login", json={"employee_id": emp_id}, timeout=30)
        files = {"file": ("in.png", io.BytesIO(PNG_1x1), "image/png")}
        r = s.post(f"{API}/attendance/masuk", files=files, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["start_time"]
        assert body["gps_start_lat"] is None
        assert body["gps_start_lng"] is None
    finally:
        admin.delete(f"{API}/employees/{emp_id}", timeout=30)


# ---------- Overtime admin still works ----------
def test_admin_create_overtime_manual_and_calc(admin, temp_employee):
    r = admin.post(f"{API}/overtime", json={
        "employee_id": temp_employee["id"], "date": "2026-06-10",
        "start_time": "17:00", "end_time": "21:30",
        "location": "Kantor", "note": "Deploy",
    }, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["total_minutes"] == 270
    assert body["total_label"] == "4 Jam 30 Menit"
    ot_id = body["id"]

    # midnight crossing
    r = admin.post(f"{API}/overtime", json={
        "employee_id": temp_employee["id"], "date": "2026-06-11",
        "start_time": "22:00", "end_time": "02:00",
    }, timeout=30)
    assert r.status_code == 200
    assert r.json()["total_minutes"] == 240
    ot2 = r.json()["id"]

    admin.delete(f"{API}/overtime/{ot_id}", timeout=30)
    admin.delete(f"{API}/overtime/{ot2}", timeout=30)


@pytest.mark.parametrize("start,end,exp_work,exp_ot,exp_work_lbl,exp_ot_lbl", [
    ("08:30", "16:30", 480, 0, "8 Jam", "0 Menit"),
    ("07:00", "18:00", 480, 180, "8 Jam", "3 Jam"),
    ("17:00", "21:30", 0, 270, "0 Menit", "4 Jam 30 Menit"),
    ("22:00", "02:00", 0, 240, "0 Menit", "4 Jam"),
])
def test_calc_split_via_api(admin, temp_employee, start, end, exp_work, exp_ot, exp_work_lbl, exp_ot_lbl):
    """Verify calc_split: kerja/lembur split for boundary cases including midnight crossing."""
    r = admin.post(f"{API}/overtime", json={
        "employee_id": temp_employee["id"], "date": "2026-09-01",
        "start_time": start, "end_time": end,
    }, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["work_minutes"] == exp_work, f"work_min for {start}-{end}"
    assert body["overtime_minutes"] == exp_ot, f"ot_min for {start}-{end}"
    assert body["work_label"] == exp_work_lbl
    assert body["overtime_label"] == exp_ot_lbl
    admin.delete(f"{API}/overtime/{body['id']}", timeout=30)


def test_monthly_recap_overtime_label(admin, temp_employee):
    """monthly-recap harus menyertakan overtime_label per karyawan + grand_overtime_label."""
    # create 07:00-18:00 (kerja 8 Jam, lembur 3 Jam) di bulan uji
    r = admin.post(f"{API}/overtime", json={
        "employee_id": temp_employee["id"], "date": "2026-09-20",
        "start_time": "07:00", "end_time": "18:00", "note": "Uji recap",
    }, timeout=30)
    assert r.status_code == 200, r.text
    ot_id = r.json()["id"]
    try:
        r = admin.get(f"{API}/overtime/monthly-recap", params={"month": "2026-09"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert "grand_overtime_label" in body
        # ensure our employee row present with overtime_label
        rows = [e for e in body["employees"] if e["employee_id"] == temp_employee["id"]]
        assert rows and "overtime_label" in rows[0]
    finally:
        admin.delete(f"{API}/overtime/{ot_id}", timeout=30)


def test_export_csv_has_new_columns(admin):
    r = admin.get(f"{API}/overtime/export", params={"fmt": "csv"}, timeout=60)
    assert r.status_code == 200
    text = r.text
    assert "Total Waktu" in text
    assert "Jam Kerja (08:30-16:30)" in text
    assert "Lembur" in text


def test_employee_cannot_create_overtime(emp_session, temp_employee):
    r = emp_session.post(f"{API}/overtime", json={
        "employee_id": temp_employee["id"], "date": "2026-06-15",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    assert r.status_code == 403


def test_employee_list_only_own(admin, emp_session, temp_employee):
    r = admin.post(f"{API}/overtime", json={
        "employee_id": temp_employee["id"], "date": "2026-06-14",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    ot_id = r.json()["id"]
    r = emp_session.get(f"{API}/overtime", timeout=30)
    assert r.status_code == 200
    for row in r.json():
        assert row["employee_id"] == temp_employee["id"]
    admin.delete(f"{API}/overtime/{ot_id}", timeout=30)


# ---------- Export & Stats ----------
def test_export_csv_and_xlsx(admin):
    r = admin.get(f"{API}/overtime/export", params={"fmt": "csv"}, timeout=60)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "Nama Karyawan" in r.text

    r = admin.get(f"{API}/overtime/export", params={"fmt": "xlsx"}, timeout=60)
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


def test_stats(admin):
    r = admin.get(f"{API}/stats", timeout=30)
    assert r.status_code == 200
    body = r.json()
    for key in ["total_month_label", "total_month_hours", "employees_month", "today_count", "with_photo", "total_records"]:
        assert key in body


# ---------- Monthly Recap ----------
def test_monthly_recap_default_current_month(admin):
    r = admin.get(f"{API}/overtime/monthly-recap", timeout=30)
    assert r.status_code == 200
    from datetime import datetime, timezone
    assert r.json()["month"] == datetime.now(timezone.utc).strftime("%Y-%m")


def test_monthly_recap_empty_month(admin):
    r = admin.get(f"{API}/overtime/monthly-recap", params={"month": "1999-01"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["employees"] == []
    assert body["total_records"] == 0


def test_logout(admin):
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    r = s.post(f"{API}/auth/logout", timeout=30)
    assert r.status_code == 200
    assert s.get(f"{API}/auth/me", timeout=30).status_code == 401
