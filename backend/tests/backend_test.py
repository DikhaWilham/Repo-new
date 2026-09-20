"""SewaKontrak Pro backend API tests."""
import os
import io
import uuid
import time
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lease-management-hub-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "dikhawilham77@gmail.com"
ADMIN_PASSWORD = "SewaKontrak123!"


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["email"] == ADMIN_EMAIL
    # Verify httpOnly cookie
    assert "access_token" in s.cookies
    return s


# ---------- Auth ----------

class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200

    def test_me_unauth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-wrong"})
        assert r.status_code == 401

    def test_login_success(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_register_and_login(self):
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        pw = "TestPass123!"
        r = s.post(f"{API}/auth/register", json={"name": "TEST User", "email": email, "password": pw})
        assert r.status_code == 200, r.text
        assert r.json()["email"] == email
        # duplicate
        r2 = s.post(f"{API}/auth/register", json={"name": "TEST User", "email": email, "password": pw})
        assert r2.status_code == 400
        # login with new user
        s2 = requests.Session()
        r3 = s2.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert r3.status_code == 200
        # logout
        r4 = s2.post(f"{API}/auth/logout")
        assert r4.status_code == 200

    def test_forgot_password_generic(self):
        r1 = requests.post(f"{API}/auth/forgot-password", json={"email": ADMIN_EMAIL})
        r2 = requests.post(f"{API}/auth/forgot-password", json={"email": "nonexistent_xyz@example.com"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json() == r2.json(), "Response should be identical for registered and unregistered emails"


# ---------- Documents ----------

class TestDocuments:
    def test_stats_seed(self, admin_session):
        r = admin_session.get(f"{API}/documents/stats")
        assert r.status_code == 200
        stats = r.json()
        # Seed expects Total=6, Aktif=3, Hampir=2, Berakhir=1
        assert stats["total"] >= 6
        assert stats["berakhir"] >= 1
        assert stats["hampir_berakhir"] >= 2
        assert stats["aktif"] >= 3
        assert isinstance(stats["hampir_berakhir_list"], list)
        assert len(stats["hampir_berakhir_list"]) == stats["hampir_berakhir"]

    def test_list_and_filter(self, admin_session):
        r = admin_session.get(f"{API}/documents")
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 6
        # search
        r2 = admin_session.get(f"{API}/documents", params={"search": "Samsung"})
        assert r2.status_code == 200
        assert any("Samsung" in d["nama_brand"] for d in r2.json())
        # filter skema
        r3 = admin_session.get(f"{API}/documents", params={"skema": "sewa"})
        assert all(d["skema"] == "sewa" for d in r3.json())
        # filter status
        r4 = admin_session.get(f"{API}/documents", params={"status": "berakhir"})
        assert all(d["status"] == "berakhir" for d in r4.json())

    def test_crud_flow(self, admin_session):
        today = date.today()
        payload = {
            "nama_counter": "TEST_Counter_" + uuid.uuid4().hex[:6],
            "alamat_counter": "TEST Address",
            "skema": "sewa",
            "nama_brand": "TESTBrand",
            "nama_cv": "TEST CV",
            "luasan": 10.5,
            "service_charge": 1000000,
            "promo_levy": 200000,
            "tanggal_mulai": today.isoformat(),
            "tanggal_akhir": (today + timedelta(days=200)).isoformat(),
            "reminder_date": (today + timedelta(days=170)).isoformat(),
            "keterangan": "TEST",
        }
        # Create
        r = admin_session.post(f"{API}/documents", json=payload)
        assert r.status_code == 200, r.text
        created = r.json()
        doc_id = created["id"]
        assert created["nama_counter"] == payload["nama_counter"]
        assert created["status"] == "aktif"

        # Get
        r2 = admin_session.get(f"{API}/documents/{doc_id}")
        assert r2.status_code == 200
        assert r2.json()["nama_counter"] == payload["nama_counter"]

        # Update
        payload["keterangan"] = "TEST updated"
        payload["tanggal_akhir"] = (today + timedelta(days=10)).isoformat()
        r3 = admin_session.put(f"{API}/documents/{doc_id}", json=payload)
        assert r3.status_code == 200
        # 10 days left, no reminder in past -> aktif or hampir (reminder 170 days in future -> aktif since today < reminder). Days_left=10.
        # Actually reminder_date is today+170 (future) -> today < reminder -> aktif (regardless of days_left).
        updated = r3.json()
        assert updated["keterangan"] == "TEST updated"

        # Invalid date order
        bad = payload.copy()
        bad["tanggal_akhir"] = (today - timedelta(days=10)).isoformat()
        bad["tanggal_mulai"] = today.isoformat()
        r4 = admin_session.put(f"{API}/documents/{doc_id}", json=bad)
        assert r4.status_code == 400

        # Delete
        r5 = admin_session.delete(f"{API}/documents/{doc_id}")
        assert r5.status_code == 200
        r6 = admin_session.get(f"{API}/documents/{doc_id}")
        assert r6.status_code == 404

    def test_attachment_flow(self, admin_session):
        today = date.today()
        payload = {
            "nama_counter": "TEST_Att_" + uuid.uuid4().hex[:6],
            "alamat_counter": "TEST", "skema": "sewa", "nama_brand": "TEST", "nama_cv": "TEST",
            "luasan": 5, "service_charge": 100000, "promo_levy": 0,
            "tanggal_mulai": today.isoformat(), "tanggal_akhir": (today + timedelta(days=100)).isoformat(),
            "reminder_date": None, "keterangan": "",
        }
        r = admin_session.post(f"{API}/documents", json=payload)
        assert r.status_code == 200
        doc_id = r.json()["id"]

        # Upload PNG (1x1 pixel)
        png = bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
        files = {"file": ("test.png", io.BytesIO(png), "image/png")}
        r2 = admin_session.post(f"{API}/documents/{doc_id}/attachments", files=files)
        if r2.status_code == 502:
            pytest.skip(f"Storage service unavailable: {r2.text}")
        assert r2.status_code == 200, r2.text
        att = r2.json()
        assert att["filename"] == "test.png"

        # Verify appears
        r3 = admin_session.get(f"{API}/documents/{doc_id}")
        assert len(r3.json()["attachments"]) == 1

        # Bad extension
        files_bad = {"file": ("test.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
        r4 = admin_session.post(f"{API}/documents/{doc_id}/attachments", files=files_bad)
        assert r4.status_code == 400

        # Delete attachment
        r5 = admin_session.delete(f"{API}/documents/{doc_id}/attachments/{att['id']}")
        assert r5.status_code == 200
        r6 = admin_session.get(f"{API}/documents/{doc_id}")
        assert len(r6.json()["attachments"]) == 0

        # Cleanup
        admin_session.delete(f"{API}/documents/{doc_id}")

    def test_documents_unauth(self):
        r = requests.get(f"{API}/documents")
        assert r.status_code == 401
