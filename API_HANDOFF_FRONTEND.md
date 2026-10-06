# Panduan Integrasi API Backend Satubumi (Frontend Handoff Guide)

**Base API URL (Development):** `http://localhost:8000/api/v1`  
**Interactive Swagger Docs:** `http://localhost:8000/docs`  
**GitHub Repository:** [https://github.com/fru33er/satubumi-project-BE.git](https://github.com/fru33er/satubumi-project-BE.git)

---

## 🚀 Cara Menjalankan Backend di Komputer Developer Frontend

Developer Frontend dapat menjalankan backend ini di komputer lokal dengan 3 langkah mudah:

```bash
# 1. Clone repositori backend
git clone https://github.com/fru33er/satubumi-project-BE.git
cd satubumi-project-BE

# 2. Install dependensi
pip install -r requirements.txt

# 3. Jalankan server FastAPI
python -m uvicorn app.main:app --reload --port 8000
```
Server akan aktif di `http://localhost:8000`. Dokumentasi interaktif Swagger dapat diakses langsung di `http://localhost:8000/docs`.

---

## 📡 Daftar Endpoint API yang Tersedia

### 1. Engine Rapid-FS (Carbon Feasibility Calculator)

#### a. Hitung Skor Rapid-FS (JSON Input)
* **Endpoint:** `POST /api/v1/rapid-fs/calculate`
* **Content-Type:** `application/json`
* **Request Body:**
  ```json
  {
    "location_name": "Proyek Hutan Kalimantan",
    "area_ha": 50000.0,
    "ecosystem_type": "hutan_tropis",
    "project_duration_years": 30,
    "carbon_price_usd": 10.0
  }
  ```
  *(Catatan: Tipe ekosistem yang didukung: `hutan_tropis`, `mangrove`, `agroforestri`, `gambut`, `lahan_terdegradasi`)*

* **Response (`200 OK`):**
  ```json
  {
    "location_name": "Proyek Hutan Kalimantan",
    "area_ha": 50000.0,
    "ecosystem_type": "hutan_tropis",
    "project_duration_years": 30,
    "carbon_price_usd": 10.0,
    "carbon_factor": 150.0,
    "emission_reduction_rate": 5.0,
    "agb_ton": 7500000.0,
    "carbon_stock_tc": 3525000.0,
    "co2e_ton": 12936750.0,
    "annual_emission_reduction": 250000.0,
    "acc_total_credits": 7500000.0,
    "gross_revenue_usd": 75000000.0,
    "cost_breakdown": {
      "development_cost_usd": 150000.0,
      "mrv_cost_usd": 75000.0,
      "validation_cost_usd": 50000.0,
      "operational_cost_usd": 100000.0,
      "total_cost_usd": 7875000.0
    },
    "net_revenue_usd": 67125000.0,
    "feasibility_score": 73.65,
    "feasibility_category": "Potensi Sedang",
    "component_scores": {
      "carbon_score": 50.0,
      "legality_score": 90.0,
      "biodiversity_score": 85.0,
      "social_score": 75.0,
      "economy_score": 89.5
    },
    "recommendations": [
      "Proyek potensial namun memerlukan optimalisasi luas area atau integrasi skema agroforestri/restorasi.",
      "Lakukan penilaian ulang variabel biaya operasional dan negosiasi harga kredit karbon minimal USD 12-15/tCO2e."
    ]
  }
  ```

---

#### b. Upload Berkas Shapefile (`.zip`) — Exclusive Feature
* **Endpoint:** `POST /api/v1/rapid-fs/upload-shapefile`
* **Content-Type:** `multipart/form-data`
* **Headers (Opsional tapi disarankan jika user login):**
  * `Authorization: Bearer <access_token>`
* **Form Parameters:**
  * `file`: Berkas `.zip` (berisi `.shp`, `.shx`, `.dbf`, `.prj`)
  * `location_name`: Nama Lokasi (string)
  * `ecosystem_type`: Tipe Ekosistem (string)
  * `project_duration_years`: Durasi proyek (int, default: 30)
  * `carbon_price_usd`: Harga karbon (float, default: 10.0)
* **Response (`200 OK`):**
  Mengembalikan respon kalkulasi Rapid-FS beserta field **`is_unlocked: boolean`**.
  
  > 💡 **Ketentuan Tampilan Frontend (Blur):**
  > - **Jika `is_unlocked === false`:**
  >   - Tampilkan dengan jelas: **`feasibility_score`**, **`feasibility_category`**, dan **`component_scores`** (Carbon, Legality, Biodiversity, Social, Economy).
  >   - **BLUR** bagian detail lainnya (AGB ton, Carbon Stock, CO2e, Annual ER, Gross/Net Revenue, Cost Breakdown, Recommendations).
  >   - Berikan badge: 🔒 **"Fitur Eksklusif"** dan tombol CTA: *"Hubungi Satu Bumi untuk membuka analisis lengkap & unduh laporan resmi"*.
  >   - User tetap bisa klik tombol **"Simpan ke My Assessment"**!
  > - **Jika `is_unlocked === true`:**
  >   - Tampilkan seluruh data secara lengkap tanpa efek blur.

---

### 2. Autentikasi Pengguna (JWT Auth)

* **Register:** `POST /api/v1/auth/register` (Body: `email`, `password`, `full_name`, `phone_number`)
* **Login:** `POST /api/v1/auth/login` (Body: `email`, `password`)
  * *Mengembalikan `{ "access_token": "eyJhbG..." }`*
* **Get Profile:** `GET /api/v1/auth/me`
  * *Header:* `Authorization: Bearer <access_token>`
  * *Response mencakup field:* `"has_rapidfs_access": true | false`

---

### 3. Histori & Manajemen Assessment Project ("My Assessment")

* **Simpan Hasil Assessment:** `POST /api/v1/assessments`
  * Request Body: `AssessmentSubmitRequest` (berisi data kontak + payload `rapid_fs_result`).
  * Backend akan menyimpan seluruh data kalkulasi secara lengkap ke database.
* **Lihat Daftar Proyek Tersimpan:** `GET /api/v1/assessments` (Memerlukan Token Auth)
* **Lihat Detail Proyek:** `GET /api/v1/assessments/{id}` (Memerlukan Token Auth)
  
  > 🔒 **Keamanan & Perilaku My Assessment:**
  > - Response dari `GET /assessments` dan `GET /assessments/{id}` menyertakan field **`is_unlocked: boolean`**.
  > - Jika user **belum di-unlock** oleh Admin (`is_unlocked === false`):
  >   - Field sensitif (`agb_ton`, `carbon_stock_tc`, `co2e_ton`, `acc_total_credits`, `gross_revenue_usd`, `total_cost_usd`, `net_revenue_usd`, `cost_breakdown_json`, `recommendations_json`) **otomatis bernilai `null`** dari backend.
  >   - Frontend menampilkan badge 🔒 **"Preview / Locked"** dan banner hubungi tim Satu Bumi.
  > - Setelah user **di-unlock** oleh Admin:
  >   - User tinggal me-refresh halaman, field `is_unlocked` otomatis menjadi `true`, dan seluruh angka langsung muncul tanpa perlu upload ulang file!
* **Hapus Proyek:** `DELETE /api/v1/assessments/{id}`

---

### 4. Generator PDF Report & Contact Form

* **Download Report PDF:** `GET /api/v1/reports/{id}/pdf`
  * *Header:* `Authorization: Bearer <access_token>`
  * **Aturan Akses:**
    - Jika user memiliki akses (`has_rapidfs_access === true` atau Admin) $\rightarrow$ Mengembalikan *stream binary* berkas PDF laporan resmi Satubumi (`200 OK`).
    - Jika user belum di-unlock $\rightarrow$ Mengembalikan `403 Forbidden` (*"Akses ditolak. Fitur unduh laporan resmi (PDF) hanya tersedia untuk akun yang telah diverifikasi Satu Bumi"*).
    - Tombol "Download PDF" di Frontend sebaiknya di-disable / diberi ikon gembok jika `is_unlocked === false`.
* **Form Inquiry Kontak:** `POST /api/v1/contact`
  * Body: `name`, `email`, `company`, `message`

---

### 5. Khusus Admin: Membuka Kunci Akses Pengguna (Unlock Flow)

Ketika calon klien menghubungi tim Satu Bumi dan disetujui, Admin dapat membuka akses akun klien melalui:

* **Endpoint:** `PATCH /api/v1/users/{user_id}/rapidfs-access?has_access=true`
* **Header:** `Authorization: Bearer <token_admin>`
* **Response (`200 OK`):** Data user ter-update dengan `has_rapidfs_access: true`.
* Seketika user tersebut login atau me-refresh halaman, semua proyeknya di My Assessment dan fitur Download PDF langsung terbuka penuh.

---

## 💻 Contoh Kode Integrasi di Next.js (React)

### Contoh 1: Memanggil Engine Rapid-FS (`fetch`)
```javascript
export async function calculateRapidFS(data) {
  const response = await fetch('http://localhost:8000/api/v1/rapid-fs/calculate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      location_name: data.locationName,
      area_ha: parseFloat(data.areaHa),
      ecosystem_type: data.ecosystemType,
      project_duration_years: 30,
      carbon_price_usd: 10.0
    }),
  });

  if (!response.ok) {
    throw new Error('Gagal melakukan komputasi Rapid-FS');
  }

  return await response.json();
}
```

### Contoh 2: Upload File Shapefile `.zip` di Next.js
```javascript
export async function uploadShapefile(file, locationName, ecosystemType) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('location_name', locationName);
  formData.append('ecosystem_type', ecosystemType);

  const response = await fetch('http://localhost:8000/api/v1/rapid-fs/upload-shapefile', {
    method: 'POST',
    body: formData,
  });

  return await response.json();
}
```
