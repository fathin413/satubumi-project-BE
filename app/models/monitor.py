from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, JSON, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProjectActivity(Base):
    """
    Mencatat kegiatan yang dilakukan dalam proyek.
    Contoh: penanaman, restorasi, biodiversity survey, community development.
    """

    __tablename__ = "project_activities"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Jenis kegiatan: planting, restoration, biodiversity_survey,
    # community_development, fire_prevention, forest_protection
    activity_type = Column(String(100), nullable=False)

    activity_date = Column(Date, nullable=False)
    location_geojson = Column(
        JSON, nullable=True
    )  # GeoJSON Point atau Polygon lokasi kegiatan

    # Target & realisasi (misalnya target 1000 ha, realisasi 650 ha)
    target = Column(Float, nullable=True)
    realization = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)  # "ha", "trees", "person", dll

    executor = Column(String(255), nullable=True)  # Nama pelaksana/tim
    photo_urls = Column(JSON, nullable=True)  # List URL foto dokumentasi
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MonitoringPlot(Base):
    """
    Plot monitoring yang digunakan untuk pengambilan data di lapangan.
    Bisa berupa permanent plot, transect, atau point sampling.
    Plot ini menjadi referensi untuk tree_records dan field_reports.
    """
    __tablename__ = "monitoring_plots"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    plot_code = Column(String(100), nullable=False)   # Kode unik plot, misal "WK-023"
    plot_name = Column(String(255), nullable=True)    # Nama deskriptif plot
    plot_type = Column(String(50), nullable=True)     # permanent_plot, transect, point

    location_geojson = Column(JSON, nullable=True)    # GeoJSON Point atau Polygon
    area_ha = Column(Float, nullable=True)            # Luas plot dalam ha

    # Standar MRV Karbon & Sensus Ekologis
    stratum = Column(String(100), nullable=True)          # Kelas stratifikasi tutupan lahan (misal: "Hutan Sekunder Kerapatan Tinggi")
    elevation_mdpl = Column(Float, nullable=True)         # Ketinggian dari permukaan laut (meter)
    slope_pct = Column(Float, nullable=True)              # Kemiringan / kelerengan lahan (%)
    shape_type = Column(String(50), default="rectangle", nullable=True) # rectangle, circle, polygon, point
    dimension_length_m = Column(Float, nullable=True)    # Panjang plot (meter)
    dimension_width_m = Column(Float, nullable=True)     # Lebar plot (meter)
    azimuth_deg = Column(Float, nullable=True)           # Orientasi kompas arah plot (0 - 360)
    established_date = Column(Date, nullable=True)        # Tanggal penetapan plot pertama kali
    last_survey_date = Column(Date, nullable=True)        # Tanggal sensus/pengukuran lapangan terakhir

    # Status: active, inactive
    status = Column(String(50), default="active", nullable=False)
    notes = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TreeRecord(Base):
    """
    Data tanam per-batch atau per-plot untuk monitoring pohon/restorasi.
    Satu record mewakili satu batch penanaman (misal: 500 pohon Shorea di plot WK-023).
    Dashboard menghitung Trees Planted, Survived, Dead, Survival Rate dari tabel ini.

    Untuk tracking growth history per-batch, gunakan tabel tree_measurements.
    """

    __tablename__ = "tree_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    plot_id = Column(String(100), nullable=True)    # Kode plot, misal "WK-023" (referensi ke monitoring_plots.plot_code)
    tree_tag = Column(String(100), nullable=True, index=True) # Nomor Tag / ID unik pohon individual, misal "TR-001"

    species = Column(String(255), nullable=False)       # Nama Latin / Ilmiah (misal: "Coffea canephora")
    local_name = Column(String(255), nullable=True)       # Nama Lokal / Nama Umum (misal: "Kopi Robusta", "Alpukat")
    quantity = Column(Integer, nullable=False, default=1)  # Jumlah pohon (default 1 untuk individual)
    planting_date = Column(Date, nullable=False)
    location_geojson = Column(JSON, nullable=True)  # GeoJSON Point lokasi plot

    # Data monitoring kondisi pohon (nilai snapshot terakhir)
    condition = Column(String(50), default="healthy")  # healthy, stressed, dead
    height_cm = Column(Float, nullable=True)
    dbh_cm = Column(Float, nullable=True)  # Diameter Breast Height
    circumference_cm = Column(Float, nullable=True, default=0.0)  # Keliling Batang (cm)
    is_tag_lost = Column(Boolean, default=False, nullable=False)  # Flag apakah QR tag fisik hilang/rusak di lapangan
    is_alive = Column(Boolean, default=True)

    photo_urls = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    last_monitored = Column(DateTime, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # [NEW] siapa yang input data
    created_by_name = Column(String(255), nullable=True)  # Nama lengkap pengguna saat data diinput
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TreeMeasurement(Base):
    """
    History pengukuran pohon per-batch (growth tracking).
    Setiap kali ada monitoring berkala, tambah record baru di tabel ini
    tanpa menimpa data di tree_records — sehingga growth history terjaga.

    Contoh timeline:
      - 2024-01-01: height=45cm, dbh=3.2cm (penanaman awal)
      - 2024-07-01: height=78cm, dbh=5.1cm (monitoring 6 bulan)
      - 2025-01-01: height=120cm, dbh=8.4cm (monitoring 1 tahun)
    """
    __tablename__ = "tree_measurements"

    id = Column(Integer, primary_key=True, index=True)
    tree_record_id = Column(Integer, ForeignKey("tree_records.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    measurement_date = Column(Date, nullable=False)
    height_cm = Column(Float, nullable=True)
    dbh_cm = Column(Float, nullable=True)              # Diameter Breast Height (cm)
    circumference_cm = Column(Float, nullable=True)    # Keliling Batang (cm)
    condition = Column(String(50), nullable=True)      # healthy, stressed, dead
    is_alive = Column(Boolean, default=True)

    measured_by = Column(String(255), nullable=True)   # Nama petugas yang mengukur
    photo_urls = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class FieldReport(Base):
    """
    Laporan yang dikirim petugas lapangan secara langsung.
    Setiap laporan memiliki: WHO + WHERE + WHEN + WHAT + EVIDENCE.
    """

    __tablename__ = "field_reports"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    officer_name = Column(String(255), nullable=False)
    plot_id = Column(String(100), nullable=True)
    location_geojson = Column(JSON, nullable=True)  # GPS Point dari petugas lapangan

    report_date = Column(DateTime, nullable=False)

    # Jenis laporan: tree_monitoring, biodiversity, incident, general, community
    report_type = Column(String(100), nullable=False)

    activity_description = Column(Text, nullable=True)
    result_description = Column(Text, nullable=True)
    photo_urls = Column(JSON, nullable=True)
    video_urls = Column(JSON, nullable=True)             # [NEW] URL video lapangan

    # [NEW] Link opsional ke data monitoring terkait
    tree_record_id = Column(Integer, ForeignKey("tree_records.id"), nullable=True)
    biodiversity_id = Column(Integer, ForeignKey("biodiversity_observations.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """
    Peringatan terkait kondisi atau perubahan di wilayah proyek.
    Bisa dibuat manual (admin) atau auto-generated oleh sistem.
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tipe alert: deforestation, fire, land_cover_change, monitoring_overdue, low_tree_survival
    alert_type = Column(String(100), nullable=False)

    # Severity: low, medium, high, critical
    severity = Column(String(50), default="medium", nullable=False)

    location_geojson = Column(JSON, nullable=True)
    description = Column(Text, nullable=False)

    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

    # True jika alert dibuat otomatis oleh sistem (bukan manual dari admin)
    auto_generated = Column(Boolean, default=False)

    # [NEW] Siapa yang membuat alert (untuk alert manual)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # [NEW] URL sumber data yang memicu alert (GEE, satellite data, dll)
    source_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class BiodiversityObservation(Base):
    """
    Hasil pengamatan biodiversitas (satwa/flora) di lokasi proyek.
    """

    __tablename__ = "biodiversity_observations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    species_name = Column(String(255), nullable=False)
    species_type = Column(String(50), nullable=False)  # fauna, flora
    location_geojson = Column(JSON, nullable=True)

    observed_date = Column(Date, nullable=False)
    habitat = Column(String(255), nullable=True)
    observer = Column(String(255), nullable=True)
    photo_url = Column(String(500), nullable=True)
    photo_urls = Column(JSON, nullable=True)
    video_urls = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class CommunityData(Base):
    """
    Data dampak sosial & ekonomi proyek terhadap masyarakat sekitar.
    """

    __tablename__ = "community_data"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    village_name = Column(String(255), nullable=False)
    beneficiary_count = Column(Integer, default=0)
    livelihood_groups = Column(Integer, default=0)
    employment_count = Column(Integer, default=0)
    community_investment = Column(Float, default=0.0)  # Nilai investasi (USD)

    # Jenis kegiatan: pelatihan, agroforestry, livelihood, community_enterprise, dll
    activity_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class CarbonRecord(Base):
    """
    Estimasi dan monitoring data karbon per periode.
    CATATAN: Data ini adalah monitoring/estimation, bukan verified carbon credit.
    """

    __tablename__ = "carbon_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    carbon_stock_tco2e = Column(Float, nullable=True)  # Total carbon stock (tCO2e)
    biomass_ton = Column(Float, nullable=True)
    estimated_co2e = Column(Float, nullable=True)  # Estimasi CO2 equivalent
    carbon_change = Column(
        Float, nullable=True
    )  # Perubahan karbon vs periode sebelumnya

    methodology = Column(
        String(255), nullable=True
    )  # Metode perhitungan yang digunakan
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class LandscapeSnapshot(Base):
    """
    Snapshot kondisi tutupan lahan/hutan pada suatu waktu tertentu.
    Digunakan untuk time-series monitoring perubahan lanskap:
    deforestasi, restorasi, perubahan tutupan lahan, NDVI.

    Data bisa diinput manual atau di-fetch dari Google Earth Engine.
    Bandingkan dua snapshot untuk melihat perubahan antar periode.
    """
    __tablename__ = "landscape_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    snapshot_date = Column(Date, nullable=False)

    # Sumber data: GEE (Google Earth Engine), manual, satellite, report
    data_source = Column(String(100), nullable=True, default="manual")

    # Data tutupan lahan (dalam hektare)
    forest_cover_ha = Column(Float, nullable=True)
    deforestation_ha = Column(Float, nullable=True)
    restoration_ha = Column(Float, nullable=True)
    land_cleared_ha = Column(Float, nullable=True)
    fire_ha = Column(Float, nullable=True)

    # Indeks vegetasi NDVI (0.0 - 1.0)
    ndvi_mean = Column(Float, nullable=True)
    ndvi_min = Column(Float, nullable=True)
    ndvi_max = Column(Float, nullable=True)

    # Data spasial raw (GeoJSON layer atau metadata dari GEE)
    geojson_data = Column(JSON, nullable=True)

    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProjectMember(Base):
    """
    Relasi user ke proyek dengan role spesifik.
    Memungkinkan assignment petugas lapangan, project manager, atau viewer
    ke proyek tertentu tanpa mengubah role global mereka di sistem.
    """
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role dalam proyek: project_manager, field_officer, viewer
    role = Column(String(50), nullable=False, default="viewer")

    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

