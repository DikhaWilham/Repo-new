"""Backend tests for Rekap Lembur app."""
import os
import io
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://worklog-mobile-14.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "dikhawilham77@gmail.com"
ADMIN_PASSWORD = "admin123"
EMP_EMAIL = "budi.test@perusahaan.com"
EMP_PASSWORD = "budi123"


def _login(session: requests.Session, email: str, password: str):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = _login(s, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def employee(admin):
    # ensure employee exists
    r = admin.get(f"{API}/employees", timeout=30)
    assert r.status_code == 200
    emp = next((e for e in r.json() if e["email"] == EMP_EMAIL), None)
    if not emp:
        r = admin.post(f"{API}/employees", json={
            "name": "Budi Test", "email": EMP_EMAIL, "password": EMP_PASSWORD,
            "nip": "TEST001", "jabatan": "Staff Test", "active": True,
        }, timeout=30)
        assert r.status_code == 200, r.text
        emp = r.json()
    s = requests.Session()
    r = _login(s, EMP_EMAIL, EMP_PASSWORD)
    assert r.status_code == 200, r.text
    return {"session": s, "user": emp}


# ---------- Auth ----------
def test_auth_me(admin):
    r = admin.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert body["email"] == ADMIN_EMAIL


def test_auth_login_wrong_password():
    s = requests.Session()
    r = _login(s, ADMIN_EMAIL, "wrong-password-xx")
    assert r.status_code == 401


def test_auth_no_cookie_returns_401():
    r = requests.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 401


# ---------- Employees ----------
def test_employees_list(admin):
    r = admin.get(f"{API}/employees", timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_employee_cannot_create_employee(employee):
    r = employee["session"].post(f"{API}/employees", json={
        "name": "Hack", "email": "hack@x.com", "password": "pwpwpwpw",
    }, timeout=30)
    assert r.status_code == 403


def test_admin_create_update_employee(admin):
    email = f"test_temp_{int(time.time())}@x.com"
    r = admin.post(f"{API}/employees", json={
        "name": "Temp User", "email": email, "password": "pwpwpwpw",
        "nip": "T1", "jabatan": "QA", "active": True,
    }, timeout=30)
    assert r.status_code == 200, r.text
    emp_id = r.json()["id"]
    # update
    r = admin.put(f"{API}/employees/{emp_id}", json={"jabatan": "Senior QA"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["jabatan"] == "Senior QA"
    # delete
    r = admin.delete(f"{API}/employees/{emp_id}", timeout=30)
    assert r.status_code == 200


# ---------- Overtime calc ----------
def test_overtime_create_calc_and_midnight(admin, employee):
    emp_id = employee["user"]["id"]
    # normal
    r = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-10",
        "start_time": "17:00", "end_time": "21:30",
        "location": "Kantor Pusat", "note": "Deploy release",
    }, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_minutes"] == 270
    assert body["total_label"] == "4 Jam 30 Menit"
    ot_id_normal = body["id"]

    # midnight crossing
    r = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-11",
        "start_time": "22:00", "end_time": "02:00",
        "location": "Datacenter", "note": "Maintenance",
    }, timeout=30)
    assert r.status_code == 200
    assert r.json()["total_minutes"] == 240
    assert r.json()["total_label"] == "4 Jam"
    ot_id_mid = r.json()["id"]

    # cleanup
    admin.delete(f"{API}/overtime/{ot_id_normal}", timeout=30)
    admin.delete(f"{API}/overtime/{ot_id_mid}", timeout=30)


def test_employee_only_edits_own_and_restricted_fields(admin, employee):
    emp_id = employee["user"]["id"]
    # admin creates OT for employee
    r = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-12",
        "start_time": "18:00", "end_time": "20:00", "location": "L", "note": "N",
    }, timeout=30)
    assert r.status_code == 200
    ot_id = r.json()["id"]

    # employee edits allowed fields
    r = employee["session"].put(f"{API}/overtime/{ot_id}", json={
        "start_time": "18:30", "end_time": "21:00",
        "location": "New Loc", "note": "Updated",
        # attempt admin-only fields (should be ignored, not error)
        "date": "2030-01-01",
    }, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["start_time"] == "18:30"
    assert body["location"] == "New Loc"
    assert body["date"] == "2026-06-12", "employee must NOT be able to change date"

    # employee CANNOT delete
    r = employee["session"].delete(f"{API}/overtime/{ot_id}", timeout=30)
    assert r.status_code == 403

    # employee CANNOT edit another employee's OT (create temp employee OT)
    r = admin.post(f"{API}/employees", json={
        "name": "Other", "email": f"other_{int(time.time())}@x.com", "password": "pwpwpwpw",
    }, timeout=30)
    other_id = r.json()["id"]
    r = admin.post(f"{API}/overtime", json={
        "employee_id": other_id, "date": "2026-06-13",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    other_ot = r.json()["id"]
    r = employee["session"].put(f"{API}/overtime/{other_ot}", json={"note": "hack"}, timeout=30)
    assert r.status_code == 403

    # cleanup
    admin.delete(f"{API}/overtime/{ot_id}", timeout=30)
    admin.delete(f"{API}/overtime/{other_ot}", timeout=30)
    admin.delete(f"{API}/employees/{other_id}", timeout=30)


def test_employee_list_only_own(admin, employee):
    emp_id = employee["user"]["id"]
    # create one for this employee
    r = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-14",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    ot_id = r.json()["id"]
    # employee lists
    r = employee["session"].get(f"{API}/overtime", timeout=30)
    assert r.status_code == 200
    for row in r.json():
        assert row["employee_id"] == emp_id
    admin.delete(f"{API}/overtime/{ot_id}", timeout=30)


def test_employee_cannot_create_overtime(employee):
    r = employee["session"].post(f"{API}/overtime", json={
        "employee_id": employee["user"]["id"], "date": "2026-06-15",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    assert r.status_code == 403


# ---------- Filter, Export, Stats ----------
def test_export_excel_csv(admin):
    r = admin.get(f"{API}/overtime/export", params={"fmt": "csv"}, timeout=60)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "Nama Karyawan" in r.text

    r = admin.get(f"{API}/overtime/export", params={"fmt": "xlsx"}, timeout=60)
    assert r.status_code == 200
    assert "spreadsheet" in r.headers.get("content-type", "")
    assert r.content[:2] == b"PK"  # xlsx = zip


def test_filter_by_date_and_search(admin, employee):
    emp_id = employee["user"]["id"]
    r = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-16",
        "start_time": "17:00", "end_time": "19:00",
        "location": "UniqueLocXYZ", "note": "special-marker-abc",
    }, timeout=30)
    ot_id = r.json()["id"]
    r = admin.get(f"{API}/overtime", params={"search": "special-marker-abc"}, timeout=30)
    assert r.status_code == 200
    assert any(x["id"] == ot_id for x in r.json())
    r = admin.get(f"{API}/overtime", params={"date_from": "2026-06-16", "date_to": "2026-06-16"}, timeout=30)
    assert any(x["id"] == ot_id for x in r.json())
    admin.delete(f"{API}/overtime/{ot_id}", timeout=30)


def test_stats(admin):
    r = admin.get(f"{API}/stats", timeout=30)
    assert r.status_code == 200
    body = r.json()
    for key in ["total_month_label", "total_month_hours", "employees_month", "today_count", "with_photo", "total_records"]:
        assert key in body


# ---------- Photo upload ----------
def test_photo_upload_employee_own(admin, employee):
    emp_id = employee["user"]["id"]
    r = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-17",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    ot_id = r.json()["id"]
    # 1x1 PNG
    png = bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
    )
    files = {"file": ("proof.png", io.BytesIO(png), "image/png")}
    r = employee["session"].post(f"{API}/overtime/{ot_id}/photo", files=files, timeout=60)
    assert r.status_code == 200, r.text
    assert r.json()["photo_path"]
    admin.delete(f"{API}/overtime/{ot_id}", timeout=30)


def test_logout(admin):
    s = requests.Session()
    assert _login(s, ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200
    r = s.post(f"{API}/auth/logout", timeout=30)
    assert r.status_code == 200
    r = s.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 401



# ---------- Monthly Recap ----------
def test_monthly_recap_admin_aggregation(admin, employee):
    """2026-06: Budi (270m/4.5h) + E2E Karyawan (150m/2.5h) => 7 Jam."""
    emp_id = employee["user"]["id"]
    # create second employee
    other_email = f"e2e_recap_{int(time.time())}@x.com"
    r = admin.post(f"{API}/employees", json={
        "name": "E2E Karyawan", "email": other_email, "password": "pwpwpwpw",
    }, timeout=30)
    assert r.status_code == 200, r.text
    other_id = r.json()["id"]

    # Budi: 4h30m
    r1 = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-06-10",
        "start_time": "17:00", "end_time": "21:30",
    }, timeout=30)
    assert r1.status_code == 200
    # override employee_name to Budi Santoso for assertion match? use whatever seed already has
    ot1 = r1.json()["id"]
    # E2E: 2h30m
    r2 = admin.post(f"{API}/overtime", json={
        "employee_id": other_id, "date": "2026-06-11",
        "start_time": "18:00", "end_time": "20:30",
    }, timeout=30)
    assert r2.status_code == 200
    ot2 = r2.json()["id"]

    try:
        r = admin.get(f"{API}/overtime/monthly-recap", params={"month": "2026-06"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["month"] == "2026-06"
        # sorted desc by total_minutes: first Budi 270, then E2E 150
        emps = {e["employee_id"]: e for e in body["employees"]}
        assert emp_id in emps
        assert other_id in emps
        assert emps[emp_id]["total_minutes"] >= 270
        assert emps[other_id]["total_minutes"] == 150
        assert emps[other_id]["total_label"] == "2 Jam 30 Menit"
        assert emps[other_id]["total_hours"] == 2.5
        # ordering: first entry has highest minutes
        assert body["employees"][0]["total_minutes"] >= body["employees"][-1]["total_minutes"]
        # counts
        assert emps[other_id]["count"] == 1
        assert emps[other_id]["with_photo"] == 0
        assert body["total_records"] >= 2
        assert body["total_employees"] >= 2
        assert body["grand_total_minutes"] >= 420
    finally:
        admin.delete(f"{API}/overtime/{ot1}", timeout=30)
        admin.delete(f"{API}/overtime/{ot2}", timeout=30)
        admin.delete(f"{API}/employees/{other_id}", timeout=30)


def test_monthly_recap_default_current_month(admin):
    r = admin.get(f"{API}/overtime/monthly-recap", timeout=30)
    assert r.status_code == 200
    body = r.json()
    from datetime import datetime, timezone
    assert body["month"] == datetime.now(timezone.utc).strftime("%Y-%m")


def test_monthly_recap_empty_month(admin):
    r = admin.get(f"{API}/overtime/monthly-recap", params={"month": "1999-01"}, timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert body["employees"] == []
    assert body["total_records"] == 0
    assert body["total_employees"] == 0
    assert body["grand_total_minutes"] == 0


def test_monthly_recap_employee_scope(admin, employee):
    """Non-admin only sees own aggregation."""
    emp_id = employee["user"]["id"]
    # create OT for employee
    r1 = admin.post(f"{API}/overtime", json={
        "employee_id": emp_id, "date": "2026-07-05",
        "start_time": "17:00", "end_time": "19:00",
    }, timeout=30)
    ot1 = r1.json()["id"]
    # create OT for another employee
    other_email = f"e2e_scope_{int(time.time())}@x.com"
    r = admin.post(f"{API}/employees", json={
        "name": "Other Scope", "email": other_email, "password": "pwpwpwpw",
    }, timeout=30)
    other_id = r.json()["id"]
    r2 = admin.post(f"{API}/overtime", json={
        "employee_id": other_id, "date": "2026-07-06",
        "start_time": "17:00", "end_time": "20:00",
    }, timeout=30)
    ot2 = r2.json()["id"]

    try:
        r = employee["session"].get(f"{API}/overtime/monthly-recap", params={"month": "2026-07"}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        ids = {e["employee_id"] for e in body["employees"]}
        assert other_id not in ids, "employee must not see other employees' aggregation"
        assert emp_id in ids
    finally:
        admin.delete(f"{API}/overtime/{ot1}", timeout=30)
        admin.delete(f"{API}/overtime/{ot2}", timeout=30)
        admin.delete(f"{API}/employees/{other_id}", timeout=30)
