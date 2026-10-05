# Panduan Integrasi API Backend Satubumi (Frontend Handoff Guide)

**Base API URL (Development):** `http://localhost:8000/api/v1`
**Interactive Swagger Docs:** `http://localhost:8000/docs`
**GitHub Repository:** [https://github.com/fru33er/satubumi-project-BE.git](https://github.com/fru33er/satubumi-project-BE.git)
**Branch Aktif:** `temp-be-testing`

---

## Cara Menjalankan Backend

```bash
git clone https://github.com/fru33er/satubumi-project-BE.git
cd satubumi-project-BE
git checkout temp-be-testing
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Server aktif di `http://localhost:8000`. Swagger UI: `http://localhost:8000/docs`.

---

## Autentikasi (JWT)

Sertakan token di header untuk endpoint yang memerlukan auth:

```
Authorization: Bearer <access_token>
```

| Method | Endpoint | Deskripsi | Auth |
|--------|----------|-----------|------|
| `POST` | `/api/v1/auth/register` | Daftar akun baru | Tidak perlu |
| `POST` | `/api/v1/auth/login` | Login, mendapatkan token | Tidak perlu |
| `GET`  | `/api/v1/auth/me` | Lihat profil user saat ini | Bearer Token |

**Register — `POST /api/v1/auth/register`**
```json
{
  "full_name": "Budi Santoso",
  "email": "budi@example.com",
  "password": "rahasia123",
  "phone_number": "08123456789"
}
```

**Login — `POST /api/v1/auth/login`**
```json
// Request
{ "email": "budi@example.com", "password": "rahasia123" }

// Response 200 OK
{ "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer" }
```

---

## Daftar Endpoint API

### 1. Engine Rapid-FS (Carbon Feasibility Calculator)

> **PERUBAHAN TERBARU** — Rapid-FS kini menjadi **fitur eksklusif** dengan dua tingkat akses:
> - **Upload Shapefile** — Wajib login. Response **terbatas**: Indicative Score + Score Components saja.
> - **Calculate (JSON)** — Khusus **Admin / Super Admin**. Response **penuh** termasuk data finansial & karbon.

---

#### a. Upload Berkas Shapefile — *Exclusive, Login Required*

- **Endpoint:** `POST /api/v1/rapid-fs/upload-shapefile`
- **Auth:** Bearer Token (semua user yang sudah login)
- **Content-Type:** `multipart/form-data`

**Form Parameters:**

| Field | Tipe | Wajib | Default | Keterangan |
|-------|------|-------|---------|-----------|
| `file` | file `.zip` | Ya | — | Berisi `.shp`, `.shx`, `.dbf`, `.prj` |
| `location_name` | string | Tidak | `"Lokasi Proyek Shapefile"` | Nama lokasi proyek |
| `ecosystem_type` | string | Tidak | `"hutan_tropis"` | Lihat opsi di bawah |
| `project_duration_years` | integer | Tidak | `30` | Durasi proyek (1-100 tahun) |
| `carbon_price_usd` | float | Tidak | `10.0` | Harga karbon per tCO2e (USD) |

**Opsi `ecosystem_type`:** `hutan_tropis` · `mangrove` · `agroforestri` · `gambut` · `lahan_terdegradasi`

**Response `200 OK` — RapidFSPreviewResult:**
```json
{
  "location_name": "Proyek Hutan Kalimantan",
  "area_ha": 50000.0,
  "ecosystem_type": "hutan_tropis",
  "project_duration_years": 30,
  "feasibility_score": 73.65,
  "feasibility_category": "Potensi Sedang",
  "component_scores": {
    "carbon_score": 50.0,
    "legality_score": 90.0,
    "biodiversity_score": 85.0,
    "social_score": 75.0,
    "economy_score": 89.5
  },
  "contact_cta": "Ingin melihat proyeksi karbon lengkap, analisis finansial, dan rekomendasi detail? Hubungi tim Satu Bumi di https://satubumi.org/contact"
}
```

**Catatan untuk Frontend:**
- Field `contact_cta` **wajib ditampilkan** ke user sebagai CTA untuk menghubungi tim Satu Bumi.
- Data seperti `carbon_stock`, `gross_revenue`, `cost_breakdown`, `recommendations` tidak tersedia di response ini (by design).

**Error Responses:**

| Status | Keterangan |
|--------|-----------|
| `401 Unauthorized` | Token tidak valid atau tidak dikirim |
| `400 Bad Request` | File bukan `.zip` atau shapefile tidak valid |

---

#### b. Hitung Skor Rapid-FS (JSON Input) — *Internal, Admin Only*

- **Endpoint:** `POST /api/v1/rapid-fs/calculate`
- **Auth:** Bearer Token — Admin / Super Admin only
- **Content-Type:** `application/json`

> Endpoint ini hanya untuk penggunaan internal (dashboard admin Satu Bumi). Frontend publik tidak perlu mengintegrasikan endpoint ini.

**Request Body:**
```json
{
  "location_name": "Proyek Hutan Kalimantan",
  "area_ha": 50000.0,
  "ecosystem_type": "hutan_tropis",
  "project_duration_years": 30,
  "carbon_price_usd": 10.0,
  "polygon_geojson": null,
  "latitude": null,
  "longitude": null
}
```

**Response `200 OK` — RapidFSResult (Penuh):**
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
    "Proyek potensial namun memerlukan optimalisasi luas area.",
    "Lakukan negosiasi harga kredit karbon minimal USD 12-15/tCO2e."
  ],
  "spatial_overlay_layers": null,
  "geometry": null
}
```

**Error Responses:**

| Status | Keterangan |
|--------|-----------|
| `401 Unauthorized` | Token tidak valid atau tidak dikirim |
| `403 Forbidden` | User bukan admin / super_admin |

---

### 2. Histori & Manajemen Assessment Project

Auth: Bearer Token diperlukan untuk semua endpoint di bawah ini.

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/api/v1/assessments` | Simpan hasil assessment ke histori |
| `GET`  | `/api/v1/assessments` | Lihat semua assessment milik user |
| `GET`  | `/api/v1/assessments/{id}` | Lihat detail satu assessment |
| `DELETE` | `/api/v1/assessments/{id}` | Hapus assessment |

**Simpan Assessment — `POST /api/v1/assessments`**

Menerima data kontak + hasil `RapidFSResult` penuh (khusus admin):
```json
{
  "name": "Budi Santoso",
  "email": "budi@example.com",
  "company": "PT Hijau Lestari",
  "phone": "08123456789",
  "rapid_fs_result": { }
}
```

---

### 3. Generator PDF Report & Contact Form

| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| `GET` | `/api/v1/reports/{id}/pdf` | Token | Download laporan PDF assessment |
| `POST` | `/api/v1/contact` | Tidak perlu | Kirim form inquiry kontak |

**Contact Form — `POST /api/v1/contact`:**
```json
{
  "name": "Budi Santoso",
  "email": "budi@example.com",
  "company": "PT Hijau Lestari",
  "message": "Saya tertarik dengan hasil analisis RapidFS dan ingin berdiskusi lebih lanjut."
}
```

---

## Contoh Kode Integrasi (Next.js / React)

### Contoh 1: Login dan Simpan Token
```javascript
export async function login(email, password) {
  const response = await fetch('http://localhost:8000/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) throw new Error('Login gagal');

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  return data;
}
```

### Contoh 2: Upload Shapefile (Exclusive Feature)
```javascript
export async function uploadShapefile(file, locationName, ecosystemType) {
  const token = localStorage.getItem('access_token');
  if (!token) throw new Error('Anda harus login terlebih dahulu');

  const formData = new FormData();
  formData.append('file', file);
  formData.append('location_name', locationName);
  formData.append('ecosystem_type', ecosystemType);
  formData.append('project_duration_years', '30');
  formData.append('carbon_price_usd', '10.0');

  const response = await fetch('http://localhost:8000/api/v1/rapid-fs/upload-shapefile', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      // Jangan set Content-Type manual — browser auto-set multipart boundary
    },
    body: formData,
  });

  if (response.status === 401) throw new Error('Sesi habis, silakan login ulang');
  if (!response.ok) throw new Error('Gagal memproses shapefile');

  // Response preview: indicative score + component scores + contact_cta
  return await response.json();
}
```

### Contoh 3: Menampilkan Result Preview + CTA
```jsx
function RapidFSPreview({ result }) {
  return (
    <div>
      <h2>Indicative Feasibility Score</h2>
      <p>{result.feasibility_score} / 100</p>
      <p>{result.feasibility_category}</p>

      <h3>Score Components</h3>
      <ul>
        <li>Carbon (C): {result.component_scores.carbon_score}</li>
        <li>Legality (L): {result.component_scores.legality_score}</li>
        <li>Biodiversity (B): {result.component_scores.biodiversity_score}</li>
        <li>Social (S): {result.component_scores.social_score}</li>
        <li>Economy (E): {result.component_scores.economy_score}</li>
      </ul>

      {/* Wajib tampilkan CTA — teks dari backend */}
      <div className="cta-banner">
        <p>{result.contact_cta}</p>
        <a href="https://satubumi.org/contact" target="_blank" rel="noreferrer">
          Hubungi Tim Satu Bumi
        </a>
      </div>
    </div>
  );
}
```

### Contoh 4: Handle Error Auth (401 / 403)
```javascript
async function apiCall(url, options = {}) {
  const token = localStorage.getItem('access_token');
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
    return;
  }

  if (response.status === 403) {
    throw new Error('Akses ditolak. Fitur ini memerlukan hak akses lebih tinggi.');
  }

  return response.json();
}
```

---

## Ringkasan Akses per Role

| Endpoint | Public | User (Login) | Admin / Super Admin |
|----------|:------:|:------------:|:-------------------:|
| `POST /auth/register` | Ya | Ya | Ya |
| `POST /auth/login` | Ya | Ya | Ya |
| `GET /auth/me` | Tidak | Ya | Ya |
| `POST /rapid-fs/upload-shapefile` | Tidak | Ya (preview) | Ya (preview) |
| `POST /rapid-fs/calculate` | Tidak | Tidak | Ya (full result) |
| `POST /assessments` | Tidak | Ya | Ya |
| `GET /assessments` | Tidak | Ya | Ya |
| `GET /reports/{id}/pdf` | Tidak | Ya | Ya |
| `POST /contact` | Ya | Ya | Ya |
