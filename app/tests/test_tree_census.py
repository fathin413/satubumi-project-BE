import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import unittest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.project import Project
from app.models.monitor import ProjectMember, TreeRecord
from app.models.user import User


class TestTreeCensusModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup in-memory SQLite database for isolated test execution
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.engine
        )
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        # Seed test users and project
        db = cls.TestingSessionLocal()

        # 1. Field Officer A (Creator)
        cls.user_officer_a = User(
            id=101,
            email="officer_a@satubumi.org",
            hashed_password="dummyhashedpwd",
            full_name="Budi Santoso",
            role="field_officer",
            is_active=True,
        )
        # 2. Field Officer B (Other Officer)
        cls.user_officer_b = User(
            id=102,
            email="officer_b@satubumi.org",
            hashed_password="dummyhashedpwd",
            full_name="Siti Rahma",
            role="field_officer",
            is_active=True,
        )
        # 3. Project Manager
        cls.user_pm = User(
            id=103,
            email="pm@satubumi.org",
            hashed_password="dummyhashedpwd",
            full_name="Agus PM",
            role="client",
            is_active=True,
        )
        # 4. Admin
        cls.user_admin = User(
            id=104,
            email="admin@satubumi.org",
            hashed_password="dummyhashedpwd",
            full_name="Super Admin",
            role="admin",
            is_active=True,
        )

        db.add_all([cls.user_officer_a, cls.user_officer_b, cls.user_pm, cls.user_admin])
        db.commit()

        # Project 1
        cls.project = Project(
            id=1,
            name="Restorasi Hutan Gambut Sebangau",
            description="Project test monitoring",
            location_name="Kalimantan Tengah",
            project_type="peatland",
            area_ha=500.0,
        )
        db.add(cls.project)
        db.commit()

        # Project Members
        db.add_all([
            ProjectMember(project_id=1, user_id=101, role="field_officer"),
            ProjectMember(project_id=1, user_id=102, role="field_officer"),
            ProjectMember(project_id=1, user_id=103, role="project_manager"),
            ProjectMember(project_id=1, user_id=104, role="admin"),
        ])
        db.commit()
        db.close()

        # Tokens
        cls.token_officer_a = create_access_token(subject="officer_a@satubumi.org")
        cls.token_officer_b = create_access_token(subject="officer_b@satubumi.org")
        cls.token_pm = create_access_token(subject="pm@satubumi.org")
        cls.token_admin = create_access_token(subject="admin@satubumi.org")

    def test_01_create_tree_record_with_census_fields(self):
        """Uji pembuatan data sensus pohon baru dengan kolom lokal, keliling, tag hilang, created_by."""
        headers = {"Authorization": f"Bearer {self.token_officer_a}"}
        payload = {
            "species": "Shorea balangeran",
            "local_name": "Belangeran Merah",
            "quantity": 1,
            "planting_date": "2026-03-01",
            "circumference_cm": 25.5,
            "is_tag_lost": False,
            "condition": "healthy",
            "height_cm": 150.0,
            "notes": "Pohon hasil sensus plot WK-01",
        }
        res = self.client.post("/api/v1/projects/1/trees", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["species"], "Shorea balangeran")
        self.assertEqual(data["local_name"], "Belangeran Merah")
        self.assertEqual(data["circumference_cm"], 25.5)
        self.assertEqual(data["is_tag_lost"], False)
        self.assertEqual(data["created_by"], 101)
        self.assertEqual(data["created_by_name"], "Budi Santoso")
        self.assertAlmostEqual(data["dbh_cm"], round(25.5 / 3.14159265, 2), places=1)
        self.__class__.tree_id_a = data["id"]

    def test_02_update_tree_by_creator_success(self):
        """Pembuat data (Officer A) berhak mengubah data sensus pohonnya sendiri."""
        headers = {"Authorization": f"Bearer {self.token_officer_a}"}
        payload = {
            "circumference_cm": 28.0,
            "condition": "stressed",
            "notes": "Kondisi mengering karena kemarau",
            "is_tag_lost": True,
        }
        res = self.client.put(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            json=payload,
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["circumference_cm"], 28.0)
        self.assertEqual(data["condition"], "stressed")
        self.assertEqual(data["is_tag_lost"], True)
        self.assertEqual(data["notes"], "Kondisi mengering karena kemarau")

    def test_03_update_tree_by_non_creator_forbidden(self):
        """Petugas lapangan lain (Officer B) DITOLAK saat mencoba mengubah data milik Officer A."""
        headers = {"Authorization": f"Bearer {self.token_officer_b}"}
        payload = {
            "circumference_cm": 35.0,
            "notes": "Coba ubah tanpa hak",
        }
        res = self.client.put(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            json=payload,
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            res.json()["detail"],
            "Anda hanya memiliki wewenang untuk mengubah data sensus yang Anda masukkan sendiri.",
        )

        # Coba juga via PATCH
        res_patch = self.client.patch(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            json=payload,
            headers=headers,
        )
        self.assertEqual(res_patch.status_code, 403)
        self.assertEqual(
            res_patch.json()["detail"],
            "Anda hanya memiliki wewenang untuk mengubah data sensus yang Anda masukkan sendiri.",
        )

    def test_04_update_tree_by_project_manager_allowed(self):
        """Project Manager diizinkan mengubah data sensus pohon milik petugas lapangan."""
        headers = {"Authorization": f"Bearer {self.token_pm}"}
        payload = {
            "notes": "Koreksi catatan dari Project Manager",
        }
        res = self.client.patch(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            json=payload,
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["notes"], "Koreksi catatan dari Project Manager")

    def test_05_update_tree_by_admin_allowed(self):
        """Admin diizinkan mengubah data sensus pohon milik siapapun."""
        headers = {"Authorization": f"Bearer {self.token_admin}"}
        payload = {
            "local_name": "Belangeran Super",
            "notes": "Divalidasi oleh Admin",
        }
        res = self.client.put(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            json=payload,
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["local_name"], "Belangeran Super")

    def test_06_delete_tree_by_non_creator_forbidden(self):
        """Petugas lapangan lain (Officer B) DITOLAK saat mencoba menghapus pohon milik Officer A."""
        headers = {"Authorization": f"Bearer {self.token_officer_b}"}
        res = self.client.delete(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(
            res.json()["detail"],
            "Anda hanya memiliki wewenang untuk menghapus data sensus yang Anda masukkan sendiri.",
        )

    def test_07_sync_batch_trees_global_endpoint(self):
        """Uji endpoint POST /api/v1/trees/sync-batch untuk sinkronisasi batch dari mobile app."""
        headers = {"Authorization": f"Bearer {self.token_officer_a}"}
        payload = {
            "project_id": 1,
            "trees": [
                {
                    "species": "Alstonia scholaris",
                    "local_name": "Pulai",
                    "tree_tag": "TR-101",
                    "circumference_cm": 42.0,
                    "height_cm": 300.0,
                    "is_tag_lost": False,
                    "condition": "healthy",
                    "notes": "Pohon A batch sync",
                },
                {
                    "species": "Dyera lowii",
                    "local_name": "Jelutung Gambut",
                    "tree_tag": "TR-102",
                    "circumference_cm": 15.0,
                    "height_cm": 120.0,
                    "is_tag_lost": True,
                    "condition": "healthy",
                    "notes": "Pohon B batch sync tag hilang",
                    "created_by_name": "Budi Santoso Field",
                },
            ],
        }
        res = self.client.post("/api/v1/trees/sync-batch", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["synced_count"], 2)
        self.assertEqual(len(data["items"]), 2)

        # Cek item 1
        item1 = data["items"][0]
        self.assertEqual(item1["species"], "Alstonia scholaris")
        self.assertEqual(item1["created_by"], 101)
        self.assertEqual(item1["created_by_name"], "Budi Santoso")
        self.assertEqual(item1["is_tag_lost"], False)

        # Cek item 2
        item2 = data["items"][1]
        self.assertEqual(item2["species"], "Dyera lowii")
        self.assertEqual(item2["created_by"], 101)
        self.assertEqual(item2["created_by_name"], "Budi Santoso Field")
        self.assertEqual(item2["is_tag_lost"], True)

        self.__class__.batch_tree_id = item1["id"]

    def test_08_get_trees_list_and_detail_contains_all_fields(self):
        """Uji GET /trees dan GET /trees/{id} mengembalikan semua 5 kolom sensus."""
        headers = {"Authorization": f"Bearer {self.token_officer_a}"}

        # List
        res_list = self.client.get("/api/v1/projects/1/trees", headers=headers)
        self.assertEqual(res_list.status_code, 200)
        trees = res_list.json()
        self.assertGreaterEqual(len(trees), 1)
        first_tree = trees[0]
        self.assertIn("local_name", first_tree)
        self.assertIn("circumference_cm", first_tree)
        self.assertIn("is_tag_lost", first_tree)
        self.assertIn("created_by", first_tree)
        self.assertIn("created_by_name", first_tree)

        # Detail
        res_detail = self.client.get(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            headers=headers,
        )
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.json()
        self.assertEqual(detail["id"], self.__class__.tree_id_a)
        self.assertEqual(detail["created_by"], 101)
        self.assertEqual(detail["created_by_name"], "Budi Santoso")
        self.assertEqual(detail["is_tag_lost"], True)

    def test_09_delete_tree_by_creator_allowed(self):
        """Pemilik data (Officer A) berhasil menghapus data sensus pohonnya sendiri."""
        headers = {"Authorization": f"Bearer {self.token_officer_a}"}
        res = self.client.delete(
            f"/api/v1/projects/1/trees/{self.__class__.batch_tree_id}",
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)

        # Verifikasi sudah terhapus
        res_check = self.client.get(
            f"/api/v1/projects/1/trees/{self.__class__.batch_tree_id}",
            headers=headers,
        )
        self.assertEqual(res_check.status_code, 404)

    def test_10_delete_tree_by_admin_allowed(self):
        """Admin berhasil menghapus data sensus pohon milik siapapun."""
        headers = {"Authorization": f"Bearer {self.token_admin}"}
        res = self.client.delete(
            f"/api/v1/projects/1/trees/{self.__class__.tree_id_a}",
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)

    def test_11_filter_trees_by_mine_and_creator(self):
        """Uji filter ?only_mine=true dan ?created_by=ID untuk tracking data tim."""
        # Officer A buat 1 pohon
        headers_a = {"Authorization": f"Bearer {self.token_officer_a}"}
        res_a = self.client.post(
            "/api/v1/projects/1/trees",
            json={
                "species": "Pohon A",
                "circumference_cm": 10.0,
                "planting_date": "2026-03-01",
            },
            headers=headers_a,
        )
        self.assertEqual(res_a.status_code, 201)

        # Officer B buat 1 pohon
        headers_b = {"Authorization": f"Bearer {self.token_officer_b}"}
        res_b = self.client.post(
            "/api/v1/projects/1/trees",
            json={
                "species": "Pohon B",
                "circumference_cm": 20.0,
                "planting_date": "2026-03-01",
            },
            headers=headers_b,
        )
        self.assertEqual(res_b.status_code, 201)

        # Officer A panggil ?only_mine=true -> hanya dapat pohon miliknya
        res_mine = self.client.get("/api/v1/projects/1/trees?only_mine=true", headers=headers_a)
        self.assertEqual(res_mine.status_code, 200)
        mine_trees = res_mine.json()
        self.assertTrue(all(t["created_by"] == 101 for t in mine_trees))

        # Project Manager cek pohon yang diinput Officer B (?created_by=102)
        headers_pm = {"Authorization": f"Bearer {self.token_pm}"}
        res_pm = self.client.get("/api/v1/projects/1/trees?created_by=102", headers=headers_pm)
        self.assertEqual(res_pm.status_code, 200)
        b_trees = res_pm.json()
        self.assertTrue(all(t["created_by"] == 102 for t in b_trees))

    def test_12_activity_logs_tracking(self):
        """Uji endpoint activity log untuk user sendiri dan tim proyek."""
        # Tim cek activity sendiri
        headers_a = {"Authorization": f"Bearer {self.token_officer_a}"}
        res_my_logs = self.client.get("/api/v1/activity/me", headers=headers_a)
        self.assertEqual(res_my_logs.status_code, 200)
        logs = res_my_logs.json()
        self.assertGreaterEqual(len(logs), 1)

        # PM cek activity seluruh tim dalam project
        headers_pm = {"Authorization": f"Bearer {self.token_pm}"}
        res_team_logs = self.client.get("/api/v1/activity/project/1", headers=headers_pm)
        self.assertEqual(res_team_logs.status_code, 200)
        team_logs = res_team_logs.json()
        self.assertGreaterEqual(len(team_logs), 1)


if __name__ == "__main__":
    unittest.main()
