from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, date


# ─────────────────────────────────────────────
# PROJECT ACTIVITY
# ─────────────────────────────────────────────

class ActivityCreate(BaseModel):
    """Request body untuk mencatat kegiatan proyek baru."""
    activity_type: str = Field(
        ...,
        description="Jenis kegiatan: planting, restoration, biodiversity_survey, community_development, fire_prevention, forest_protection"
    )
    activity_date: date = Field(..., description="Tanggal kegiatan")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Lokasi kegiatan (GeoJSON Point/Polygon)")
    target: Optional[float] = Field(None, description="Target kegiatan")
    realization: Optional[float] = Field(None, description="Realisasi kegiatan")
    unit: Optional[str] = Field(None, max_length=50, description="Satuan: ha, trees, person, dll")
    executor: Optional[str] = Field(None, max_length=255, description="Nama pelaksana/tim")
    photo_urls: Optional[List[str]] = Field(None, description="List URL foto dokumentasi")
    notes: Optional[str] = Field(None, description="Catatan tambahan")


class ActivityResponse(BaseModel):
    id: int
    project_id: int
    activity_type: str
    activity_date: date
    location_geojson: Optional[Dict[str, Any]] = None
    target: Optional[float] = None
    realization: Optional[float] = None
    unit: Optional[str] = None
    executor: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# MONITORING PLOT
# ─────────────────────────────────────────────

class MonitoringPlotCreate(BaseModel):
    """Request body untuk membuat plot monitoring baru."""
    plot_code: str = Field(..., max_length=100, description="Kode unik plot, misal WK-023")
    plot_name: Optional[str] = Field(None, max_length=255, description="Nama deskriptif plot")
    plot_type: Optional[str] = Field(None, max_length=50, description="Tipe plot: permanent_plot, transect, point")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="GeoJSON Point atau Polygon lokasi plot")
    area_ha: Optional[float] = Field(None, gt=0, description="Luas plot dalam ha")
    
    # Standar MRV Karbon
    stratum: Optional[str] = Field(None, max_length=100, description="Kelas tutupan lahan / strata karbon")
    elevation_mdpl: Optional[float] = Field(None, description="Ketinggian mdpl")
    slope_pct: Optional[float] = Field(None, description="Kelerengan lahan (%)")
    shape_type: Optional[str] = Field("rectangle", max_length=50, description="Bentuk plot: rectangle, circle, polygon, point")
    dimension_length_m: Optional[float] = Field(None, description="Panjang plot (m)")
    dimension_width_m: Optional[float] = Field(None, description="Lebar plot (m)")
    azimuth_deg: Optional[float] = Field(None, description="Orientasi kompas plot (0 - 360)")
    established_date: Optional[date] = Field(None, description="Tanggal penetapan plot")
    last_survey_date: Optional[date] = Field(None, description="Tanggal pengukuran terakhir")

    status: Optional[str] = Field("active", max_length=50, description="Status: active, inactive")
    notes: Optional[str] = Field(None, description="Catatan tambahan")


class MonitoringPlotUpdate(BaseModel):
    """Request body untuk mengupdate plot monitoring."""
    plot_code: Optional[str] = Field(None, max_length=100)
    plot_name: Optional[str] = Field(None, max_length=255)
    plot_type: Optional[str] = Field(None, max_length=50)
    location_geojson: Optional[Dict[str, Any]] = None
    area_ha: Optional[float] = Field(None, gt=0)
    
    stratum: Optional[str] = Field(None, max_length=100)
    elevation_mdpl: Optional[float] = None
    slope_pct: Optional[float] = None
    shape_type: Optional[str] = Field(None, max_length=50)
    dimension_length_m: Optional[float] = None
    dimension_width_m: Optional[float] = None
    azimuth_deg: Optional[float] = None
    established_date: Optional[date] = None
    last_survey_date: Optional[date] = None

    status: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class MonitoringPlotResponse(BaseModel):
    """Response data plot monitoring."""
    id: int
    project_id: int
    plot_code: str
    plot_name: Optional[str] = None
    plot_type: Optional[str] = None
    location_geojson: Optional[Dict[str, Any]] = None
    area_ha: Optional[float] = None
    
    stratum: Optional[str] = None
    elevation_mdpl: Optional[float] = None
    slope_pct: Optional[float] = None
    shape_type: Optional[str] = "rectangle"
    dimension_length_m: Optional[float] = None
    dimension_width_m: Optional[float] = None
    azimuth_deg: Optional[float] = None
    established_date: Optional[date] = None
    last_survey_date: Optional[date] = None

    status: str
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# TREE RECORD
# ─────────────────────────────────────────────

class TreeRecordCreate(BaseModel):
    """Request body untuk menambah data tanam pohon."""
    plot_id: Optional[str] = Field(None, max_length=100, description="Kode plot, misal WK-023")
    tree_tag: Optional[str] = Field(None, max_length=100, description="Nomor Tag / ID fisik pohon (misal TR-001)")
    species: str = Field(..., max_length=255, description="Jenis/spesies pohon")
    quantity: Optional[int] = Field(1, ge=1, description="Jumlah pohon (1 untuk sensus individual)")
    planting_date: date = Field(..., description="Tanggal penanaman")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Lokasi plot (GeoJSON Point)")
    condition: Optional[str] = Field("healthy", description="Kondisi: healthy, stressed, dead")
    height_cm: Optional[float] = Field(None, description="Tinggi pohon (cm)")
    dbh_cm: Optional[float] = Field(None, description="Diameter Breast Height (cm)")
    is_alive: Optional[bool] = Field(True, description="Status hidup pohon")
    photo_urls: Optional[List[str]] = Field(None, description="List URL foto")
    notes: Optional[str] = None


class TreeRecordUpdate(BaseModel):
    """Request body untuk update kondisi dan data tanam pohon."""
    plot_id: Optional[str] = Field(None, max_length=100, description="Kode plot, misal WK-023")
    tree_tag: Optional[str] = Field(None, max_length=100, description="Nomor Tag / ID fisik pohon")
    species: Optional[str] = Field(None, max_length=255, description="Jenis/spesies pohon")
    quantity: Optional[int] = Field(None, ge=1, description="Jumlah pohon")
    planting_date: Optional[date] = Field(None, description="Tanggal penanaman")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Lokasi plot (GeoJSON Point)")
    condition: Optional[str] = Field(None, description="Kondisi: healthy, stressed, dead")
    height_cm: Optional[float] = Field(None, description="Tinggi pohon (cm)")
    dbh_cm: Optional[float] = Field(None, description="Diameter Breast Height (cm)")
    is_alive: Optional[bool] = Field(None, description="Status hidup pohon")
    photo_urls: Optional[List[str]] = Field(None, description="List URL foto")
    notes: Optional[str] = Field(None, description="Catatan tambahan / koreksi")



class TreeRecordResponse(BaseModel):
    id: int
    project_id: int
    plot_id: Optional[str] = None
    tree_tag: Optional[str] = None
    species: str
    quantity: int
    planting_date: date
    location_geojson: Optional[Dict[str, Any]] = None
    condition: str
    height_cm: Optional[float] = None
    dbh_cm: Optional[float] = None
    is_alive: bool
    photo_urls: Optional[List[str]] = None
    notes: Optional[str] = None
    last_monitored: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TreeSummary(BaseModel):
    """Agregat statistik pohon untuk dashboard."""
    trees_planted: int
    trees_survived: int
    trees_dead: int
    survival_rate: float  # Persentase (%)
    alert_triggered: bool = False  # True jika survival rate < threshold


# ─────────────────────────────────────────────
# TREE MEASUREMENT (Growth Tracking)
# ─────────────────────────────────────────────

class TreeMeasurementCreate(BaseModel):
    """Request body untuk mencatat pengukuran berkala pohon (growth tracking)."""
    measurement_date: date = Field(..., description="Tanggal pengukuran")
    height_cm: Optional[float] = Field(None, description="Tinggi pohon saat diukur (cm)")
    dbh_cm: Optional[float] = Field(None, description="Diameter Breast Height saat diukur (cm)")
    condition: Optional[str] = Field(None, max_length=50, description="Kondisi: healthy, stressed, dead")
    is_alive: Optional[bool] = Field(True, description="Status hidup pohon")
    measured_by: Optional[str] = Field(None, max_length=255, description="Nama pengukur/petugas")
    photo_urls: Optional[List[str]] = Field(None, description="List URL foto dokumentasi")
    notes: Optional[str] = None


class TreeMeasurementResponse(BaseModel):
    """Response data pengukuran pohon."""
    id: int
    tree_record_id: int
    project_id: int
    measurement_date: date
    height_cm: Optional[float] = None
    dbh_cm: Optional[float] = None
    condition: Optional[str] = None
    is_alive: bool
    measured_by: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TreeGrowthPoint(BaseModel):
    """Satu titik data pada garis waktu pertumbuhan pohon."""
    date: date
    height_cm: Optional[float] = None
    dbh_cm: Optional[float] = None
    condition: Optional[str] = None
    is_alive: bool
    measured_by: Optional[str] = None
    source: str  # "initial_planting" atau "periodic_measurement"


class TreeGrowthResponse(BaseModel):
    """Response endpoint timeline pertumbuhan pohon."""
    tree_record_id: int
    project_id: int
    species: str
    quantity: int
    planting_date: date
    initial_height_cm: Optional[float] = None
    initial_dbh_cm: Optional[float] = None
    current_height_cm: Optional[float] = None
    current_dbh_cm: Optional[float] = None
    height_growth_cm: Optional[float] = None
    dbh_growth_cm: Optional[float] = None
    total_measurements: int = 0
    timeline: List[TreeGrowthPoint] = []


# ─────────────────────────────────────────────
# FIELD REPORT
# ─────────────────────────────────────────────

class FieldReportCreate(BaseModel):
    """Request body untuk submit laporan lapangan."""
    officer_name: str = Field(..., max_length=255, description="Nama petugas lapangan")
    plot_id: Optional[str] = Field(None, max_length=100, description="Kode plot yang dimonitor")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Koordinat GPS petugas (GeoJSON Point)")
    report_date: datetime = Field(..., description="Tanggal & waktu laporan")
    report_type: str = Field(
        ...,
        description="Jenis laporan: tree_monitoring, biodiversity, incident, general, community"
    )
    activity_description: Optional[str] = Field(None, description="Deskripsi kegiatan yang dilakukan")
    result_description: Optional[str] = Field(None, description="Hasil/temuan di lapangan")
    photo_urls: Optional[List[str]] = Field(None, description="List URL foto bukti lapangan")
    video_urls: Optional[List[str]] = Field(None, description="List URL video bukti lapangan")
    tree_record_id: Optional[int] = Field(None, description="ID tree record terkait")
    biodiversity_id: Optional[int] = Field(None, description="ID observasi biodiversitas terkait")


class FieldReportResponse(BaseModel):
    id: int
    project_id: int
    officer_name: str
    plot_id: Optional[str] = None
    location_geojson: Optional[Dict[str, Any]] = None
    report_date: datetime
    report_type: str
    activity_description: Optional[str] = None
    result_description: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None
    tree_record_id: Optional[int] = None
    biodiversity_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
class MediaUploadResponse(BaseModel):
    url: str
    filename: str
    media_type: str  # "photo" | "video"
    size: int


# ALERT
# ─────────────────────────────────────────────

class AlertCreate(BaseModel):
    """Request body untuk membuat alert secara manual."""
    alert_type: str = Field(
        ...,
        description="Tipe alert: deforestation, fire, land_cover_change, monitoring_overdue, low_tree_survival"
    )
    severity: Optional[str] = Field("medium", description="Severity: low, medium, high, critical")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Lokasi kejadian (GeoJSON)")
    description: str = Field(..., description="Deskripsi detail alert")
    source_url: Optional[str] = Field(None, max_length=500, description="URL sumber/bukti remote sensing")


class AlertUpdate(BaseModel):
    """Request body untuk update status alert."""
    is_read: Optional[bool] = None
    is_resolved: Optional[bool] = None


class AlertResponse(BaseModel):
    id: int
    project_id: int
    alert_type: str
    severity: str
    location_geojson: Optional[Dict[str, Any]] = None
    description: str
    is_read: bool
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    auto_generated: bool
    created_by: Optional[int] = None
    source_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# BIODIVERSITY OBSERVATION
# ─────────────────────────────────────────────

class BiodiversityCreate(BaseModel):
    """Request body untuk mencatat observasi biodiversitas."""
    species_name: str = Field(..., max_length=255, description="Nama spesies")
    species_type: str = Field(..., description="Tipe: fauna, flora")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Lokasi observasi (GeoJSON Point)")
    observed_date: date = Field(..., description="Tanggal observasi")
    habitat: Optional[str] = Field(None, max_length=255, description="Jenis habitat")
    observer: Optional[str] = Field(None, max_length=255, description="Nama observer")
    photo_url: Optional[str] = Field(None, max_length=500, description="URL foto spesies (legacy)")
    photo_urls: Optional[List[str]] = Field(None, description="URLs foto spesies")
    video_urls: Optional[List[str]] = Field(None, description="URLs video spesies")
    notes: Optional[str] = None


class BiodiversityUpdate(BaseModel):
    species_name: Optional[str] = Field(None, max_length=255, description="Nama spesies")
    species_type: Optional[str] = Field(None, description="Tipe: fauna, flora")
    location_geojson: Optional[Dict[str, Any]] = Field(None, description="Lokasi observasi (GeoJSON Point)")
    observed_date: Optional[date] = Field(None, description="Tanggal observasi")
    habitat: Optional[str] = Field(None, max_length=255, description="Jenis habitat")
    observer: Optional[str] = Field(None, max_length=255, description="Nama observer")
    photo_url: Optional[str] = Field(None, max_length=500, description="URL foto spesies (legacy)")
    photo_urls: Optional[List[str]] = Field(None, description="URLs foto spesies")
    video_urls: Optional[List[str]] = Field(None, description="URLs video spesies")
    notes: Optional[str] = None


class BiodiversityResponse(BaseModel):
    id: int
    project_id: int
    species_name: str
    species_type: str
    location_geojson: Optional[Dict[str, Any]] = None
    observed_date: date
    habitat: Optional[str] = None
    observer: Optional[str] = None
    photo_url: Optional[str] = None
    photo_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BiodiversitySummary(BaseModel):
    """Ringkasan biodiversitas proyek."""
    total_observations: int
    unique_species: int
    fauna_count: int
    flora_count: int


# ─────────────────────────────────────────────
# COMMUNITY DATA
# ─────────────────────────────────────────────

class CommunityCreate(BaseModel):
    """Request body untuk mencatat data dampak komunitas."""
    village_name: str = Field(..., max_length=255, description="Nama desa")
    beneficiary_count: Optional[int] = Field(0, ge=0, description="Jumlah penerima manfaat")
    livelihood_groups: Optional[int] = Field(0, ge=0, description="Jumlah kelompok usaha/tani")
    employment_count: Optional[int] = Field(0, ge=0, description="Jumlah tenaga kerja terserap")
    community_investment: Optional[float] = Field(0.0, ge=0, description="Nilai investasi komunitas (USD)")
    activity_type: Optional[str] = Field(None, max_length=100, description="Jenis kegiatan komunitas")
    description: Optional[str] = None
    date: Optional[date] = None


class CommunityResponse(BaseModel):
    id: int
    project_id: int
    village_name: str
    beneficiary_count: int
    livelihood_groups: int
    employment_count: int
    community_investment: float
    activity_type: Optional[str] = None
    description: Optional[str] = None
    date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommunitySummary(BaseModel):
    """Ringkasan dampak komunitas proyek."""
    total_beneficiaries: int
    total_villages: int
    total_livelihood_groups: int
    total_employment: int
    total_investment_usd: float


# ─────────────────────────────────────────────
# CARBON RECORD (Monitoring / Estimasi)
# ─────────────────────────────────────────────

class CarbonCreate(BaseModel):
    """Request body untuk mencatat estimasi karbon per periode."""
    period_start: date = Field(..., description="Awal periode monitoring")
    period_end: date = Field(..., description="Akhir periode monitoring")
    carbon_stock_tco2e: Optional[float] = Field(None, description="Total cadangan karbon (tCO2e)")
    biomass_ton: Optional[float] = Field(None, description="Total biomassa (ton)")
    estimated_co2e: Optional[float] = Field(None, description="Estimasi CO2 equivalent")
    carbon_change: Optional[float] = Field(None, description="Perubahan karbon vs periode sebelumnya")
    methodology: Optional[str] = Field(None, max_length=255, description="Metodologi estimasi")
    notes: Optional[str] = None


class CarbonResponse(BaseModel):
    id: int
    project_id: int
    period_start: date
    period_end: date
    carbon_stock_tco2e: Optional[float] = None
    biomass_ton: Optional[float] = None
    estimated_co2e: Optional[float] = None
    carbon_change: Optional[float] = None
    methodology: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# LANDSCAPE SNAPSHOT (Remote Sensing / Time Series)
# ─────────────────────────────────────────────

class LandscapeSnapshotCreate(BaseModel):
    """Request body untuk mencatat snapshot lanskap / tutupan lahan."""
    snapshot_date: date = Field(..., description="Tanggal snapshot kondisi lanskap")
    data_source: Optional[str] = Field("manual", max_length=100, description="Sumber: manual, GEE, satellite, report")
    forest_cover_ha: Optional[float] = Field(None, description="Tutupan hutan (ha)")
    deforestation_ha: Optional[float] = Field(None, description="Deforestasi (ha)")
    restoration_ha: Optional[float] = Field(None, description="Restorasi (ha)")
    land_cleared_ha: Optional[float] = Field(None, description="Lahan terbuka / cleared (ha)")
    fire_ha: Optional[float] = Field(None, description="Area terbakar (ha)")
    ndvi_mean: Optional[float] = Field(None, description="Rata-rata indeks NDVI")
    ndvi_min: Optional[float] = Field(None, description="NDVI minimum")
    ndvi_max: Optional[float] = Field(None, description="NDVI maksimum")
    geojson_data: Optional[Dict[str, Any]] = Field(None, description="Layer GeoJSON spasial")
    notes: Optional[str] = None


class LandscapeSnapshotResponse(BaseModel):
    id: int
    project_id: int
    snapshot_date: date
    data_source: Optional[str] = None
    forest_cover_ha: Optional[float] = None
    deforestation_ha: Optional[float] = None
    restoration_ha: Optional[float] = None
    land_cleared_ha: Optional[float] = None
    fire_ha: Optional[float] = None
    ndvi_mean: Optional[float] = None
    ndvi_min: Optional[float] = None
    ndvi_max: Optional[float] = None
    geojson_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

class DashboardResponse(BaseModel):
    """Response agregat dashboard proyek."""
    project_id: int
    project_name: str
    project_status: str

    # Statistik area
    area_ha: Optional[float] = None

    # Statistik pohon
    trees_planted: int = 0
    trees_survived: int = 0
    trees_dead: int = 0
    survival_rate: Optional[float] = None

    # Karbon (data terbaru)
    carbon_stock_tco2e: Optional[float] = None
    estimated_co2e: Optional[float] = None

    # Biodiversitas
    species_recorded: int = 0

    # Komunitas
    total_beneficiaries: int = 0
    total_villages: int = 0
    total_livelihood_groups: int = 0

    # Progress kegiatan
    total_activities: int = 0
    recent_activities: List[Dict[str, Any]] = []

    # Alert aktif
    active_alerts: int = 0
    recent_alerts: List[Dict[str, Any]] = []

    # Field reports
    total_field_reports: int = 0
    last_field_report: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT MEMBER
# ─────────────────────────────────────────────────────────────────────────────

class ProjectMemberCreate(BaseModel):
    """Request body untuk assign user ke proyek."""
    user_id: int = Field(..., description="ID user yang akan di-assign")
    role: str = Field(
        "viewer",
        description="Role dalam proyek: project_manager, field_officer, viewer"
    )


class ProjectMemberResponse(BaseModel):
    """Response data anggota proyek."""
    id: int
    project_id: int
    user_id: int
    role: str
    assigned_at: Optional[datetime] = None
    assigned_by: Optional[int] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# PROJECT PROGRESS (Target vs Actual)
# ─────────────────────────────────────────────────────────────────────────────

class TargetProgress(BaseModel):
    """Progress untuk satu target key."""
    target: float
    actual: float
    progress_pct: float
    unit: str


class TreeSummaryProgress(BaseModel):
    """Ringkasan statistik pohon."""
    planted: int = 0
    survived: int = 0
    dead: int = 0
    survival_rate: float = 0.0
    total_batches: int = 0


class ActivityTypeSummary(BaseModel):
    """Ringkasan kegiatan per tipe."""
    count: int = 0
    total_realization: float = 0.0
    unit: Optional[str] = None


class ProgressResponse(BaseModel):
    """Response endpoint GET /projects/{id}/progress."""
    project_id: int
    project_name: str
    targets: Dict[str, TargetProgress] = {}
    tree_summary: TreeSummaryProgress
    activities_by_type: Dict[str, ActivityTypeSummary] = {}
    overall_progress_pct: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# EVIDENCE SYSTEM (Multimedia Timeline & Map)
# ─────────────────────────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """Satu item bukti / evidence pada timeline multimedia."""
    id: str
    source_type: str  # "field_report", "activity", "tree_record", "tree_measurement", "biodiversity"
    source_id: int
    timestamp: datetime
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    plot_id: Optional[str] = None
    photos: List[str] = []
    videos: List[str] = []
    location_geojson: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class EvidenceTimelineResponse(BaseModel):
    """Response feed timeline multimedia evidence."""
    project_id: int
    total_items: int
    page: int
    limit: int
    items: List[EvidenceItem]


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature standar untuk visualisasi spasial."""
    type: str = "Feature"
    geometry: Optional[Dict[str, Any]] = None
    properties: Dict[str, Any]


class EvidenceMapResponse(BaseModel):
    """GeoJSON FeatureCollection untuk visualisasi evidence di peta."""
    type: str = "FeatureCollection"
    project_id: int
    total_features: int
    features: List[GeoJSONFeature]


# ─────────────────────────────────────────────────────────────────────────────
# SPATIAL GIS MULTI-LAYER & SATELLITE MAP
# ─────────────────────────────────────────────────────────────────────────────

class GeoJSONFeatureCollection(BaseModel):
    """Standar FeatureCollection GeoJSON."""
    type: str = "FeatureCollection"
    total_features: int = 0
    features: List[GeoJSONFeature] = []


class MapLayerSummary(BaseModel):
    """Ringkasan layer spasial proyek."""
    total_plots: int = 0
    total_activities: int = 0
    total_tree_batches: int = 0
    total_alerts: int = 0
    total_field_reports: int = 0
    total_biodiversity: int = 0
    has_boundary: bool = False
    center_coordinates: Optional[List[float]] = None  # [lng, lat]


class ProjectMapLayersResponse(BaseModel):
    """Response multi-layer spasial lengkap untuk peta GIS interaktif."""
    project_id: int
    project_name: str
    boundary: Optional[GeoJSONFeature] = None
    plots: GeoJSONFeatureCollection
    activities: GeoJSONFeatureCollection
    tree_locations: GeoJSONFeatureCollection
    alerts: GeoJSONFeatureCollection
    field_reports: GeoJSONFeatureCollection
    biodiversity: GeoJSONFeatureCollection
    summary: MapLayerSummary


class SatelliteTileResponse(BaseModel):
    """Response metadata tile satelit / remote sensing."""
    project_id: int
    tile_url_template: str
    attribution: str
    layer_type: str  # "true_color", "ndvi", "swir"
    acquisition_date: Optional[str] = None
    cloud_coverage_pct: Optional[float] = None
    available_layers: List[str] = []
    latest_ndvi_metrics: Optional[Dict[str, Any]] = None


class GEESyncResponse(BaseModel):
    """Response sinkronisasi data remote sensing GEE ke LandscapeSnapshot."""
    status: str
    message: str
    snapshot_id: int
    snapshot_date: date
    data_source: str
    metrics: Dict[str, Any]
    alerts_generated: List[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# INDICATORS & COMPARISON ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class VegetationHealthIndicator(BaseModel):
    ndvi_mean: Optional[float] = None
    status: str  # "Sangat Baik", "Baik", "Sedang", "Kritis"
    description: str


class TreePerformanceIndicator(BaseModel):
    trees_planted: int = 0
    trees_survived: int = 0
    survival_rate_pct: float = 0.0
    status: str  # "Optimal", "Waspada", "Kritis"
    avg_height_growth_cm: Optional[float] = None
    avg_dbh_growth_cm: Optional[float] = None


class CarbonIndicator(BaseModel):
    carbon_stock_tco2e: Optional[float] = None
    estimated_co2e: Optional[float] = None
    carbon_density_tco2e_per_ha: Optional[float] = None
    methodology: Optional[str] = None


class BiodiversityIndicator(BaseModel):
    unique_species_count: int = 0
    fauna_count: int = 0
    flora_count: int = 0
    richness_index: str  # "Tinggi", "Sedang", "Rendah"


class CommunityIndicator(BaseModel):
    total_beneficiaries: int = 0
    total_villages: int = 0
    total_investment_usd: float = 0.0


class ProjectIndicatorsResponse(BaseModel):
    """Response komprehensif metrik indikator ekologis & sosial proyek."""
    project_id: int
    project_name: str
    project_type: Optional[str] = None
    evaluated_at: datetime
    overall_health_score: float  # Skala 0.0 - 100.0
    health_category: str  # "Sangat Sehat", "Sehat", "Perlu Perhatian", "Kritis"
    vegetation_health: VegetationHealthIndicator
    tree_performance: TreePerformanceIndicator
    carbon: CarbonIndicator
    biodiversity: BiodiversityIndicator
    community: CommunityIndicator


class BaselineComparisonMetric(BaseModel):
    """Satu metrik perbandingan antara baseline awal vs kondisi terkini dan target proyek."""
    metric_name: str
    unit: str
    baseline_value: Optional[float] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    target_achievement_pct: Optional[float] = None
    change_value: Optional[float] = None
    change_pct: Optional[float] = None
    status: str  # "improved", "stable", "declined"


class BaselineTimelinePoint(BaseModel):
    """Satu titik data pada garis waktu perbandingan baseline proyek."""
    label: str
    date: Optional[str] = None
    period_key: str = ""
    carbon_stock: float = 0.0
    trees_planted: int = 0
    canopy_cover_ha: float = 0.0
    ndvi_mean: float = 0.0
    avg_height_cm: float = 0.0
    progress_pct: float = 0.0
    species_count: int = 0


class ProjectBaselineComparisonResponse(BaseModel):
    """Response perbandingan kondisi proyek: Baseline vs Kondisi Terkini."""
    project_id: int
    project_name: str
    baseline_date: Optional[date] = None
    current_date: date
    selected_period: str = "all"
    available_periods: List[str] = ["1m", "6m", "1y", "all"]
    metrics: List[BaselineComparisonMetric]
    timeline: List[BaselineTimelinePoint] = []
    targets: Dict[str, float] = {}
    summary_narrative: str


class ProjectComparisonCard(BaseModel):
    """Kartu data ringkas satu proyek untuk komparasi multi-project."""
    project_id: int
    name: str
    location_name: str
    project_type: Optional[str] = None
    area_ha: Optional[float] = None
    status: str
    overall_progress_pct: float
    trees_planted: int
    survival_rate_pct: float
    carbon_stock_tco2e: Optional[float] = None
    species_recorded: int
    active_alerts_count: int


class MultiProjectComparisonResponse(BaseModel):
    """Response komparasi performa lintas banyak proyek."""
    total_projects: int
    projects: List[ProjectComparisonCard]
    benchmarks: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# ALERT SYSTEM EXPANSION (Phase 7)
# ─────────────────────────────────────────────────────────────────────────────

class AlertCheckResponse(BaseModel):
    """Response evaluasi aturan alert otomatis."""
    project_id: int
    evaluated_rules: int
    new_alerts_created: List[str] = []
    total_active_alerts: int
    message: str


class AlertSummaryResponse(BaseModel):
    """Ringkasan statistik alert proyek."""
    project_id: int
    total_alerts: int
    active_alerts: int
    resolved_alerts: int
    resolution_rate_pct: float
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    latest_alerts: List[AlertResponse] = []


# ─────────────────────────────────────────────────────────────────────────────
# MRV SUMMARY & REPORTING (Phase 8)
# ─────────────────────────────────────────────────────────────────────────────

class MRVMeasurementBlock(BaseModel):
    trees_planted: int = 0
    trees_survived: int = 0
    survival_rate_pct: float = 0.0
    avg_height_growth_cm: Optional[float] = None
    avg_dbh_growth_cm: Optional[float] = None
    forest_cover_ha: Optional[float] = None
    deforestation_ha: Optional[float] = None
    ndvi_mean: Optional[float] = None
    carbon_stock_tco2e: Optional[float] = None
    estimated_co2e: Optional[float] = None
    unique_species_count: int = 0


class MRVReportingBlock(BaseModel):
    overall_progress_pct: float = 0.0
    targets: Dict[str, Any] = {}
    total_activities: int = 0
    activities_by_type: Dict[str, Any] = {}
    total_field_reports: int = 0
    latest_field_report_date: Optional[datetime] = None


class MRVVerificationBlock(BaseModel):
    total_photos_count: int = 0
    total_videos_count: int = 0
    gps_verified_points_count: int = 0
    satellite_snapshots_count: int = 0
    total_alerts: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    resolution_rate_pct: float = 0.0


class MRVSummaryResponse(BaseModel):
    """Ringkasan eksekutif MRV (Measurement, Reporting, Verification) formal proyek."""
    project_id: int
    project_name: str
    location_name: str
    project_type: Optional[str] = None
    area_ha: Optional[float] = None
    start_date: Optional[date] = None
    status: str
    generated_at: datetime
    measurement: MRVMeasurementBlock
    reporting: MRVReportingBlock
    verification: MRVVerificationBlock
    executive_summary: str





