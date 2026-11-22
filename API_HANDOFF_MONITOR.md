# 🌿 SATUBUMI MONITOR — FRONTEND INTEGRATION & API HANDOFF GUIDE

Dokumentasi lengkap integrasi API backend untuk developer Frontend (Web & Mobile).

---

## 📌 1. Informasi Umum & Autentikasi

- **Base URL API**: `http://localhost:8000/api/v1` (atau staging/production domain)
- **Format Payload**: `application/json`
- **Header Autentikasi**:
  ```http
  Authorization: Bearer <JWT_ACCESS_TOKEN>
  ```
- **Matriks Hak Akses & Pembatasan Project Member**:
  - `super_admin` / `admin`: Full akses ke **seluruh proyek** di sistem (CRUD Proyek, GEE Sync, Manual Alert, Tambah/Hapus Member).
  - `client` / `field_officer`:
    - `GET /api/v1/projects`: **HANYA** menampilkan daftar proyek tempat akun user terdaftar di tabel `project_members`.
    - `GET /api/v1/projects/{project_id}` dan seluruh sub-resource (`/dashboard`, `/plots`, `/trees`, `/map`, `/reports`, dll): **HANYA** dapat diakses jika user merupakan anggota dari proyek tersebut. Jika bukan anggota, server mengembalikan `403 Forbidden`.
    - `GET /api/v1/projects/compare`: Hanya mengomparasi proyek yang menjadi hak akses user (non-member dibatasi, return `403` jika tidak memiliki akses sama sekali).
    - Tidak dapat membuat, mengupdate, menghapus proyek, atau meng-assign member (Admin only).

---

## 🗺️ 2. Konsep Alur Sistem

```
PROJECT ➔ MAP ➔ MONITOR ➔ MEASURE ➔ COMPARE ➔ ALERT ➔ REPORT (MRV)
```

---

## 📦 3. Daftar Endpoint Lengkap per Modul

### 🏢 MODUL 1: Project & Target vs Actual Progress

#### A. Ambil Daftar Proyek (Pagination & Filter)
- **Method / URL**: `GET /api/v1/projects`
- **Akses**:
  - `admin` & `super_admin`: Mengambil seluruh proyek.
  - `client` & `field_officer`: Mengambil hanya proyek yang di-assign ke user di `project_members`.
- **Query Params**:
  - `page`: int (default `1`)
  - `limit`: int (default `20`, max `100`)
  - `status`: string (`active`, `completed`, `suspended`)
  - `project_type`: string (`reforestation`, `mangrove`, `peatland`, `agroforestry`, `blue_carbon`)
  - `search`: string (cari nama/lokasi)
- **Response `200 OK`**:
  ```json
  [
    {
      "id": 1,
      "name": "Restorasi Gambut Sebangau",
      "description": "Proyek restorasi hidrologis gambut dan penanaman pohon endemik",
      "location_name": "Palangkaraya, Kalimantan Tengah",
      "project_type": "peatland",
      "area_ha": 1500.0,
      "status": "active",
      "start_date": "2023-01-01",
      "end_date": "2030-12-31",
      "country": "Indonesia",
      "province": "Kalimantan Tengah",
      "district": "Palangkaraya",
      "boundary_geojson": { "type": "Polygon", "coordinates": [...] },
      "targets_json": { "tree_planting": 100000, "restoration_ha": 1000 },
      "created_at": "2026-01-10T08:00:00Z"
    }
  ]
  ```

#### B. Ambil Kalkulasi Progress Target vs Actual
- **Method / URL**: `GET /api/v1/projects/{project_id}/progress`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "project_name": "Restorasi Gambut Sebangau",
    "status": "active",
    "overall_progress_pct": 65.5,
    "tree_summary": {
      "planted": 50000,
      "survived": 48500,
      "survival_rate": 97.0
    },
    "activity_summary": [
      {
        "activity_type": "tree_planting",
        "total_target": 100000,
        "total_realization": 50000,
        "unit": "trees",
        "progress_pct": 50.0
      },
      {
        "activity_type": "canal_blocking",
        "total_target": 50,
        "total_realization": 45,
        "unit": "units",
        "progress_pct": 90.0
      }
    ],
    "target_progress": [
      {
        "target_key": "tree_planting",
        "target_value": 100000,
        "actual_value": 50000,
        "progress_pct": 50.0,
        "unit": "trees"
      }
    ]
  }
  ```

#### C. Project Members (Assign, List, Remove)
- **Role Akses**: `admin`, `super_admin`
- **1. List Member Proyek**: `GET /api/v1/projects/{project_id}/members`
- **2. Assign User ke Proyek**: `POST /api/v1/projects/{project_id}/members`
  - **Payload Body**:
    ```json
    {
      "user_id": 3,
      "role": "field_officer"
    }
    ```
  - **Pilihan `role`**: `"project_manager"`, `"field_officer"`, `"viewer"`
- **3. Hapus Member dari Proyek**: `DELETE /api/v1/projects/{project_id}/members/{user_id}`

#### D. Daftar User (Untuk Dropdown Pilih User saat Assign Member)
- **Method / URL**: `GET /api/v1/users`
- **Role Akses**: `admin`, `super_admin`
- **Query Params (Opsional)**:
  - `role`: string (`admin`, `field_officer`, `client`, etc.)
  - `is_active`: boolean (`true` / `false`)
- **Response `200 OK`** (Tanpa `hashed_password`):
  ```json
  [
    {
      "id": 1,
      "email": "budi@satubumi.org",
      "full_name": "Budi Santoso",
      "phone_number": "08123456789",
      "role": "field_officer",
      "profile_image": "/static/profile/user_1.png",
      "is_active": true,
      "created_at": "2026-01-15T09:00:00Z"
    }
  ]
  ```

---

### 🗺️ MODUL 2: Spatial GIS Multi-Layer Map & Satelit

#### A. Ambil 7 Layer Spasial Lengkap (Siap Render di Leaflet/Mapbox)
- **Method / URL**: `GET /api/v1/projects/{project_id}/map/layers`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "project_name": "Restorasi Gambut Sebangau",
    "boundary": {
      "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "properties": { "name": "Restorasi Gambut Sebangau", "area_ha": 1500.0 }
    },
    "plots": { "type": "FeatureCollection", "total_features": 4, "features": [...] },
    "activities": { "type": "FeatureCollection", "total_features": 8, "features": [...] },
    "tree_locations": { "type": "FeatureCollection", "total_features": 12, "features": [...] },
    "alerts": { "type": "FeatureCollection", "total_features": 1, "features": [...] },
    "field_reports": { "type": "FeatureCollection", "total_features": 15, "features": [...] },
    "biodiversity": { "type": "FeatureCollection", "total_features": 6, "features": [...] },
    "summary": {
      "has_boundary": true,
      "total_plots": 4,
      "total_activities": 8,
      "total_tree_batches": 12,
      "total_alerts": 1,
      "total_field_reports": 15,
      "total_biodiversity": 6,
      "center_coordinates": [113.854, -2.235]
    }
  }
  ```

#### B. Konfigurasi Tile Satelit & Indeks NDVI
- **Method / URL**: `GET /api/v1/projects/{project_id}/map/satellite`
- **Query Params**: `layer_type` (`true_color`, `ndvi`, `swir`)
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "tile_url_template": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "attribution": "Copernicus Sentinel-2 / Google Earth Engine",
    "layer_type": "true_color",
    "acquisition_date": "2026-02-15",
    "cloud_coverage_pct": 1.8,
    "available_layers": ["true_color", "ndvi", "swir", "tree_cover_loss"],
    "latest_ndvi_metrics": {
      "mean": 0.78,
      "min": 0.45,
      "max": 0.91,
      "date": "2026-02-15"
    }
  }
  ```

#### C. Sinkronisasi Telemetri Google Earth Engine (GEE Sync)
- **Method / URL**: `POST /api/v1/projects/{project_id}/gee/sync`
- **Auth**: `admin` only
- **Response `200 OK`**:
  ```json
  {
    "status": "success",
    "message": "Sinkronisasi data satelit GEE berhasil.",
    "snapshot_id": 12,
    "snapshot_date": "2026-02-28",
    "data_source": "Sentinel-2 & Hansen GFC",
    "metrics": {
      "forest_cover_ha": 1150.0,
      "deforestation_ha": 0.0,
      "ndvi_mean": 0.78
    },
    "alerts_generated": []
  }
  ```

---

### 🌳 MODUL 3: Monitoring Plots & Tree Growth Tracking

#### A. CRUD Monitoring Plot
- **Buat Plot**: `POST /api/v1/projects/{project_id}/plots`
  ```json
  {
    "plot_code": "PL-SBG-01",
    "plot_name": "Plot Permanen Belangeran 01",
    "plot_type": "permanent_plot",
    "area_ha": 2.0,
    "location_geojson": { "type": "Point", "coordinates": [113.854, -2.235] },
    "notes": "Plot sampling kerapatan kanopi"
  }
  ```
- **Daftar Plot**: `GET /api/v1/projects/{project_id}/plots`

#### B. Tambah, Update, Hapus & Sinkronisasi Sensus Pohon

##### 1. Tambah Data Sensus Pohon
- **Method / URL**: `POST /api/v1/projects/{project_id}/trees`
- **Auth**: `Bearer Token` (`field_officer`, `admin`, `super_admin`)
- **Catatan**: `created_by` otomatis diisi dari ID user token yang login, dan `created_by_name` otomatis terisi dari profil user jika tidak dikirim spesifik.
- **Request Body**:
  ```json
  {
    "species": "Shorea balangeran",
    "local_name": "Belangeran Merah",
    "tree_tag": "TR-001",
    "plot_id": "PL-SBG-01",
    "quantity": 1,
    "planting_date": "2026-03-01",
    "circumference_cm": 25.5,
    "height_cm": 150.0,
    "is_tag_lost": false,
    "condition": "healthy",
    "notes": "Hasil sensus barcode pohon"
  }
  ```

##### 2. Update / Koreksi Data Sensus Pohon
- **Method / URL**: `PUT /api/v1/projects/{project_id}/trees/{tree_id}` atau `PATCH /api/v1/projects/{project_id}/trees/{tree_id}`
- **Auth**: `Bearer Token`
- **Aturan Otorisasi (Authorization Rule)**:
  * Pembuat data (`user.id === tree.created_by`) berhak mengubah datanya.
  * User ber-role `admin`, `super_admin`, atau `project_manager` (di sistem atau di proyek) berhak mengubah.
  * Petugas lapangan lain yang bukan pembuat data akan ditolak dengan **`HTTP 403 Forbidden`**:
    `"detail": "Anda hanya memiliki wewenang untuk mengubah data sensus yang Anda masukkan sendiri."`
- **Field yang dapat diubah**: `species`, `local_name`, `height_cm`, `dbh_cm`, `circumference_cm`, `condition`, `notes`, `is_tag_lost`.
- **Request Body** (Semua field opsional, hanya kirim field yang ingin diupdate):
  ```json
  {
    "local_name": "Belangeran Super",
    "circumference_cm": 28.0,
    "height_cm": 160.0,
    "condition": "healthy",
    "is_tag_lost": true,
    "notes": "Tag barcode fisik terlepas karena angin kencang"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "id": 10,
    "project_id": 1,
    "plot_id": "PL-SBG-01",
    "tree_tag": "TR-001",
    "species": "Shorea balangeran",
    "local_name": "Belangeran Super",
    "quantity": 1,
    "planting_date": "2026-03-01",
    "location_geojson": null,
    "condition": "healthy",
    "height_cm": 160.0,
    "dbh_cm": 8.91,
    "circumference_cm": 28.0,
    "is_tag_lost": true,
    "is_alive": true,
    "photo_urls": [],
    "notes": "Tag barcode fisik terlepas karena angin kencang",
    "last_monitored": "2026-03-01T15:10:00Z",
    "created_by": 101,
    "created_by_name": "Budi Santoso",
    "created_at": "2026-03-01T08:00:00Z",
    "updated_at": "2026-03-01T15:10:00Z"
  }
  ```

##### 3. Hapus Data Sensus Pohon
- **Method / URL**: `DELETE /api/v1/projects/{project_id}/trees/{tree_id}`
- **Auth**: `Bearer Token`
- **Aturan Otorisasi**:
  * Hanya pembuat data (`user.id === tree.created_by`) atau `admin` / `super_admin` yang diizinkan menghapus.
  * Petugas lapangan lain akan ditolak dengan **`HTTP 403 Forbidden`**:
    `"detail": "Anda hanya memiliki wewenang untuk menghapus data sensus yang Anda masukkan sendiri."`

##### 4. Sinkronisasi Batch Sensus Pohon (Mobile Offline-First)
- **Method / URL**: `POST /api/v1/trees/sync-batch` atau `POST /api/v1/projects/{project_id}/trees/sync-batch`
- **Auth**: `Bearer Token` (`field_officer`, `admin`, `super_admin`)
- **Request Body**:
  ```json
  {
    "project_id": 1,
    "trees": [
      {
        "species": "Alstonia scholaris",
        "local_name": "Pulai",
        "tree_tag": "TR-101",
        "circumference_cm": 42.0,
        "is_tag_lost": false,
        "condition": "healthy",
        "notes": "Sensus offline batch 1"
      }
    ]
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "success": true,
    "synced_count": 1,
    "items": [...],
    "message": "Berhasil menyinkronkan 1 data sensus pohon."
  }
  ```

##### 5. Daftar & Pelacakan Sensus Pohon Tim
- **Method / URL**: `GET /api/v1/projects/{project_id}/trees`
- **Query Params**:
  * `only_mine=true`: *(Untuk petugas lapangan)* Hanya mengambil data pohon yang diinput oleh diri sendiri.
  * `created_by={user_id}`: *(Untuk Project Manager / Admin)* Melacak pohon yang diinput oleh anggota tim tertentu.
  * `plot_id={code}`: Filter berdasarkan kode plot.
  * `species={name}`: Filter berdasarkan nama spesies pohon.

##### 6. Pelacakan Log Aktivitas Monitoring (Activity Logs)
- **Log Aktivitas Diri Sendiri**: `GET /api/v1/activity/me`
  * Menampilkan riwayat aksi (`CREATE`, `UPDATE`, `DELETE`, `SYNC_BATCH`) yang dilakukan oleh user login.
- **Log Aktivitas Tim Proyek (Untuk Project Manager / Admin)**: `GET /api/v1/activity/project/{project_id}`
  * Parameter opsional: `?user_id={id}` untuk memfilter aktivitas anggota tim spesifik.

#### C. Catat Pengukuran Berkala Pohon
- **Method / URL**: `POST /api/v1/projects/{project_id}/trees/{tree_id}/measurements`

- **Request Body**:
  ```json
  {
    "measurement_date": "2025-06-10",
    "height_cm": 140.0,
    "dbh_cm": 8.5,
    "condition": "healthy",
    "is_alive": true,
    "photo_url": "https://storage.satubumi.org/evidence/tree_01.jpg",
    "measured_by": "Rina Petugas Lapangan",
    "notes": "Pertumbuhan daun lebat"
  }
  ```

#### C. Analisis Kurva & Delta Pertumbuhan Pohon
- **Method / URL**: `GET /api/v1/projects/{project_id}/trees/{tree_id}/growth`
- **Response `200 OK`**:
  ```json
  {
    "tree_id": 10,
    "species": "Shorea balangeran",
    "initial_planting_date": "2023-01-10",
    "initial_height_cm": 50.0,
    "initial_dbh_cm": 3.0,
    "current_height_cm": 140.0,
    "current_dbh_cm": 8.5,
    "height_growth_delta_cm": 90.0,
    "dbh_growth_delta_cm": 5.5,
    "current_condition": "healthy",
    "is_alive": true,
    "total_measurements": 3,
    "timeline": [
      { "date": "2023-01-10", "height_cm": 50.0, "dbh_cm": 3.0, "condition": "healthy", "is_alive": true },
      { "date": "2024-01-10", "height_cm": 95.0, "dbh_cm": 5.8, "condition": "healthy", "is_alive": true },
      { "date": "2025-06-10", "height_cm": 140.0, "dbh_cm": 8.5, "condition": "healthy", "is_alive": true }
    ]
  }
  ```

---

### 📷 MODUL 4: Field Monitoring & Evidence Feed

#### A. Feed Multimedia Timeline Bukti Lapangan
- **Method / URL**: `GET /api/v1/projects/{project_id}/evidence/timeline`
- **Query Params**:
  - `page`: int (default `1`)
  - `limit`: int (default `20`)
  - `source_type`: string (`field_report`, `activity`, `tree_record`, `biodiversity`)
  - `media_type`: string (`all`, `photo`, `video`)
  - `start_date` / `end_date`: `YYYY-MM-DD`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "total_items": 35,
    "page": 1,
    "limit": 20,
    "items": [
      {
        "id": "field_report_5",
        "source_type": "field_report",
        "source_id": 5,
        "title": "Laporan Patroli: Keanekaragaman Hayati",
        "description": "Ditemukan jejak bekantan dan orangutan di zona restorasi",
        "event_date": "2026-01-20",
        "author": "Budi Lapangan",
        "location_geojson": { "type": "Point", "coordinates": [113.854, -2.235] },
        "photo_urls": ["https://storage.satubumi.org/evidence/photo1.jpg"],
        "video_urls": ["https://storage.satubumi.org/evidence/camtrap1.mp4"],
        "media_type": "video",
        "metadata": { "report_type": "biodiversity", "plot_id": 2 }
      }
    ]
  }
  ```

#### B. GeoJSON Map Bukti Lapangan
- **Method / URL**: `GET /api/v1/projects/{project_id}/evidence/map`
- **Response `200 OK`**: Mengembalikan standar GeoJSON `FeatureCollection` dengan properties metadata untuk popup card di peta.

---

### 📈 MODUL 5: Performance Indicators & Baseline Comparison

#### A. Ringkasan Indikator Kesehatan Ekologis & Sosial
- **Method / URL**: `GET /api/v1/projects/{project_id}/indicators`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "project_name": "Restorasi Gambut Sebangau",
    "overall_health_score": 88.5,
    "health_category": "Sangat Sehat",
    "vegetation_health": {
      "ndvi_mean": 0.78,
      "status": "Sangat Baik",
      "description": "Kerapatan dan kehijauan kanopi vegetasi sangat lebat dan sehat."
    },
    "tree_performance": {
      "trees_planted": 50000,
      "trees_survived": 48500,
      "survival_rate_pct": 97.0,
      "status": "Optimal",
      "avg_height_growth_cm": 60.0,
      "avg_dbh_growth_cm": 3.5
    },
    "carbon": {
      "carbon_stock_tco2e": 45000.0,
      "estimated_co2e": 165000.0,
      "carbon_density_tco2e_per_ha": 30.0,
      "methodology": "IPCC Tier 2 Wetland Supplement"
    },
    "biodiversity": {
      "unique_species_count": 8,
      "fauna_count": 5,
      "flora_count": 3,
      "richness_index": "Sedang"
    },
    "community": {
      "total_beneficiaries": 350,
      "total_villages": 3,
      "total_investment_usd": 25000.0
    }
  }
  ```

#### B. Komparasi Kondisi Saat Ini vs Baseline Awal Tanam
- **Method / URL**: `GET /api/v1/projects/{project_id}/compare/baseline`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "project_name": "Restorasi Gambut Sebangau",
    "baseline_date": "2023-01-10",
    "current_date": "2026-08-31",
    "summary_narrative": "Sejak baseline (2023-01-10), proyek 'Restorasi Gambut Sebangau' mencatatkan peningkatan pada 5 dari 5 indikator utama.",
    "metrics": [
      {
        "metric_name": "Tutupan Hutan (Forest Cover)",
        "unit": "ha",
        "baseline_value": 800.0,
        "current_value": 1150.0,
        "change_value": 350.0,
        "change_pct": 43.8,
        "status": "improved"
      },
      {
        "metric_name": "Indeks Vegetasi (NDVI)",
        "unit": "index",
        "baseline_value": 0.55,
        "current_value": 0.78,
        "change_value": 0.23,
        "change_pct": 41.8,
        "status": "improved"
      },
      {
        "metric_name": "Rata-rata Tinggi Pohon",
        "unit": "cm",
        "baseline_value": 50.0,
        "current_value": 110.0,
        "change_value": 60.0,
        "change_pct": 120.0,
        "status": "improved"
      }
    ]
  }
  ```

---

### 📊 MODUL 6: Multi-Project Comparison Matrix

- **Method / URL**: `GET /api/v1/projects/compare?project_ids=1,2,3`
- **Response `200 OK`**:
  ```json
  {
    "total_projects": 2,
    "projects": [
      {
        "project_id": 1,
        "name": "Restorasi Gambut Sebangau",
        "location_name": "Palangkaraya, Kalteng",
        "project_type": "peatland",
        "area_ha": 1500.0,
        "status": "active",
        "overall_progress_pct": 65.5,
        "trees_planted": 50000,
        "survival_rate_pct": 97.0,
        "carbon_stock_tco2e": 45000.0,
        "species_recorded": 8,
        "active_alerts_count": 0
      },
      {
        "project_id": 2,
        "name": "Konservasi Mangrove Teluk Bintuni",
        "location_name": "Teluk Bintuni, Papua Barat",
        "project_type": "mangrove",
        "area_ha": 3000.0,
        "status": "active",
        "overall_progress_pct": 30.0,
        "trees_planted": 120000,
        "survival_rate_pct": 92.0,
        "carbon_stock_tco2e": 85000.0,
        "species_recorded": 14,
        "active_alerts_count": 1
      }
    ],
    "benchmarks": {
      "highest_tree_survival": { "project_id": 1, "project_name": "Restorasi Gambut Sebangau", "value": "97.0%" },
      "most_trees_planted": { "project_id": 2, "project_name": "Konservasi Mangrove Teluk Bintuni", "value": "120,000 pohon" },
      "highest_species_richness": { "project_id": 2, "project_name": "Konservasi Mangrove Teluk Bintuni", "value": "14 spesies" }
    }
  }
  ```

---

### 🚨 MODUL 7: Early Warning Alert System

#### A. Trigger Evaluasi 5 Aturan Alert Dini
- **Method / URL**: `POST /api/v1/projects/{project_id}/alerts/check`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "evaluated_rules": 5,
    "new_alerts_created": ["monitoring_overdue"],
    "total_active_alerts": 1,
    "message": "Evaluasi 5 aturan alert selesai. 1 alert baru dibuat."
  }
  ```

#### B. Ringkasan Statistik Alert & Resolution Rate
- **Method / URL**: `GET /api/v1/projects/{project_id}/alerts/summary`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "total_alerts": 4,
    "active_alerts": 1,
    "resolved_alerts": 3,
    "resolution_rate_pct": 75.0,
    "by_severity": { "critical": 0, "high": 1, "medium": 3, "low": 0 },
    "by_type": {
      "deforestation": 0,
      "fire": 0,
      "land_cover_change": 0,
      "monitoring_overdue": 3,
      "low_tree_survival": 1
    },
    "latest_alerts": [...]
  }
  ```

#### C. Resolve Alert (Tandai Selesai)
- **Method / URL**: `PUT /api/v1/projects/{project_id}/alerts/{alert_id}`
- **Request Body**:
  ```json
  {
    "is_resolved": true,
    "is_read": true
  }
  ```

---

### 📄 MODUL 8: MRV Executive Summary & Export

#### A. Ringkasan Eksekutif MRV (Measurement, Reporting, Verification)
- **Method / URL**: `GET /api/v1/projects/{project_id}/report/summary`
- **Response `200 OK`**:
  ```json
  {
    "project_id": 1,
    "project_name": "Restorasi Gambut Sebangau",
    "location_name": "Palangkaraya, Kalteng",
    "project_type": "peatland",
    "area_ha": 1500.0,
    "start_date": "2023-01-01",
    "status": "active",
    "generated_at": "2026-08-31T11:45:00Z",
    "measurement": {
      "trees_planted": 50000,
      "trees_survived": 48500,
      "survival_rate_pct": 97.0,
      "avg_height_growth_cm": 60.0,
      "avg_dbh_growth_cm": 3.5,
      "forest_cover_ha": 1150.0,
      "deforestation_ha": 0.0,
      "ndvi_mean": 0.78,
      "carbon_stock_tco2e": 45000.0,
      "estimated_co2e": 165000.0,
      "unique_species_count": 8
    },
    "reporting": {
      "overall_progress_pct": 65.5,
      "targets": { "tree_planting": 100000, "restoration_ha": 1000 },
      "total_activities": 8,
      "activities_by_type": { ... },
      "total_field_reports": 15,
      "latest_field_report_date": "2026-01-20T10:00:00Z"
    },
    "verification": {
      "total_photos_count": 28,
      "total_videos_count": 4,
      "gps_verified_points_count": 35,
      "satellite_snapshots_count": 6,
      "total_alerts": 4,
      "active_alerts": 1,
      "resolved_alerts": 3,
      "resolution_rate_pct": 75.0
    },
    "executive_summary": "Laporan MRV untuk proyek 'Restorasi Gambut Sebangau' (Palangkaraya, Kalteng). Proyek telah menanam 50,000 pohon dengan survival rate 97.0% dan progress keseluruhan 65.5%."
  }
  ```

#### B. Download PDF Laporan Monitoring Resmi
- **Method / URL**: `GET /api/v1/projects/{project_id}/report/pdf`
- **Response Headers**:
  - `Content-Type`: `application/pdf`
  - `Content-Disposition`: `attachment; filename="satubumi_monitor_report_1_20260831.pdf"`

#### C. Export Data Tabular ke CSV
- **Method / URL**: `GET /api/v1/projects/{project_id}/export/csv?data_type=trees`
- **Query Params**: `data_type` (`trees`, `activities`, `field_reports`, `biodiversity`, `carbon`, `overview`)
- **Response Headers**:
  - `Content-Type`: `text/csv; charset=utf-8`

#### D. Export Multi-Layer Spasial ke GeoJSON
- **Method / URL**: `GET /api/v1/projects/{project_id}/export/geojson`
- **Response Headers**:
  - `Content-Type`: `application/geo+json`

---

## 🛠️ 4. TypeScript Interface Definitions (Siap Copas ke Frontend)

```typescript
// ── GeoJSON Interfaces ──
export interface GeoJSONGeometry {
  type: 'Point' | 'Polygon' | 'MultiPolygon' | 'LineString';
  coordinates: any;
}

export interface GeoJSONFeature<T = Record<string, any>> {
  type: 'Feature';
  geometry: GeoJSONGeometry;
  properties: T;
}

export interface GeoJSONFeatureCollection<T = Record<string, any>> {
  type: 'FeatureCollection';
  total_features: number;
  features: GeoJSONFeature<T>[];
}

// ── GIS Map Layers ──
export interface ProjectMapLayersResponse {
  project_id: number;
  project_name: string;
  boundary: GeoJSONFeature | null;
  plots: GeoJSONFeatureCollection;
  activities: GeoJSONFeatureCollection;
  tree_locations: GeoJSONFeatureCollection;
  alerts: GeoJSONFeatureCollection;
  field_reports: GeoJSONFeatureCollection;
  biodiversity: GeoJSONFeatureCollection;
  summary: {
    has_boundary: boolean;
    total_plots: number;
    total_activities: number;
    total_tree_batches: number;
    total_alerts: number;
    total_field_reports: number;
    total_biodiversity: number;
    center_coordinates: [number, number] | null; // [lng, lat]
  };
}

// ── Project Indicators ──
export interface ProjectIndicatorsResponse {
  project_id: number;
  project_name: string;
  project_type: string | null;
  evaluated_at: string;
  overall_health_score: number; // 0.0 - 100.0
  health_category: 'Sangat Sehat' | 'Sehat' | 'Perlu Perhatian' | 'Kritis';
  vegetation_health: {
    ndvi_mean: number | null;
    status: string;
    description: string;
  };
  tree_performance: {
    trees_planted: number;
    trees_survived: number;
    survival_rate_pct: number;
    status: 'Optimal' | 'Waspada' | 'Kritis';
    avg_height_growth_cm: number | null;
    avg_dbh_growth_cm: number | null;
  };
  carbon: {
    carbon_stock_tco2e: number | null;
    estimated_co2e: number | null;
    carbon_density_tco2e_per_ha: number | null;
    methodology: string | null;
  };
  biodiversity: {
    unique_species_count: number;
    fauna_count: number;
    flora_count: number;
    richness_index: 'Tinggi' | 'Sedang' | 'Rendah';
  };
  community: {
    total_beneficiaries: number;
    total_villages: number;
    total_investment_usd: number;
  };
}

// ── Tree Growth Timeline ──
export interface TreeGrowthResponse {
  tree_id: number;
  species: string;
  initial_planting_date: string | null;
  initial_height_cm: number | null;
  initial_dbh_cm: number | null;
  current_height_cm: number | null;
  current_dbh_cm: number | null;
  height_growth_delta_cm: number | null;
  dbh_growth_delta_cm: number | null;
  current_condition: string;
  is_alive: boolean;
  total_measurements: number;
  timeline: Array<{
    date: string;
    height_cm: number | null;
    dbh_cm: number | null;
    condition: string;
    is_alive: boolean;
    measured_by?: string;
  }>;
}

// ── Tree Record & Update ──
export interface TreeRecordUpdatePayload {
  plot_id?: string;
  species?: string;
  quantity?: number;
  planting_date?: string; // YYYY-MM-DD
  location_geojson?: {
    type: 'Point';
    coordinates: [number, number]; // [lng, lat]
  };
  condition?: 'healthy' | 'stressed' | 'dead';
  height_cm?: number;
  dbh_cm?: number;
  is_alive?: boolean;
  photo_urls?: string[];
  notes?: string;
}

// ── MRV Summary ──
export interface MRVSummaryResponse {
  project_id: number;
  project_name: string;
  location_name: string;
  project_type: string | null;
  area_ha: number | null;
  start_date: string | null;
  status: string;
  generated_at: string;
  measurement: {
    trees_planted: number;
    trees_survived: number;
    survival_rate_pct: number;
    avg_height_growth_cm: number | null;
    avg_dbh_growth_cm: number | null;
    forest_cover_ha: number | null;
    deforestation_ha: number | null;
    ndvi_mean: number | null;
    carbon_stock_tco2e: number | null;
    estimated_co2e: number | null;
    unique_species_count: number;
  };
  reporting: {
    overall_progress_pct: number;
    targets: Record<string, any>;
    total_activities: number;
    activities_by_type: Record<string, any>;
    total_field_reports: number;
    latest_field_report_date: string | null;
  };
  verification: {
    total_photos_count: number;
    total_videos_count: number;
    gps_verified_points_count: number;
    satellite_snapshots_count: number;
    total_alerts: number;
    active_alerts: number;
    resolved_alerts: number;
    resolution_rate_pct: number;
  };
  executive_summary: string;
}
```
