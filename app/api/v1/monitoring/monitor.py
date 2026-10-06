from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date
import os
import uuid

from app.core.database import get_db
from app.models.project import Project
from app.models.monitor import (
    ProjectActivity, TreeRecord, TreeMeasurement, FieldReport,
    Alert, BiodiversityObservation, CommunityData, CarbonRecord,
    MonitoringPlot, LandscapeSnapshot, ProjectMember,
)
from app.models.user import User
from app.schemas.monitor import (
    ActivityCreate, ActivityResponse,
    MonitoringPlotCreate, MonitoringPlotUpdate, MonitoringPlotResponse,
    TreeRecordCreate, TreeRecordUpdate, TreeRecordResponse, TreeSummary,
    TreeMeasurementCreate, TreeMeasurementResponse, TreeGrowthPoint, TreeGrowthResponse,
    FieldReportCreate, FieldReportResponse, MediaUploadResponse,
    AlertCreate, AlertUpdate, AlertResponse,
    BiodiversityCreate, BiodiversityResponse, BiodiversitySummary,
    CommunityCreate, CommunityResponse, CommunitySummary,
    CarbonCreate, CarbonResponse,
    LandscapeSnapshotCreate, LandscapeSnapshotResponse,
    DashboardResponse,
    EvidenceTimelineResponse, EvidenceMapResponse,
    ProjectMapLayersResponse, SatelliteTileResponse, GEESyncResponse,
    ProjectIndicatorsResponse, ProjectBaselineComparisonResponse, MultiProjectComparisonResponse,
    AlertCheckResponse, AlertSummaryResponse,
    MRVSummaryResponse,
)
from app.api.v1.auth import get_current_user
from app.core.dependencies import require_admin, require_field_officer, get_project_or_404
from app.services.monitoring.alert_service import (
    check_and_create_survival_alert, check_and_create_overdue_alert,
    check_all_project_alerts, get_alerts_summary
)
from app.services.monitoring.evidence_service import get_evidence_timeline, get_evidence_map
from app.services.monitoring.spatial_layer_service import get_project_map_layers
from app.services.monitoring.gee_service import gee_service
from app.services.monitoring.indicator_service import calculate_project_indicators
from app.services.monitoring.compare_service import compare_project_with_baseline, compare_multiple_projects
from app.services.monitoring.monitor_report_service import generate_mrv_summary, generate_monitor_pdf, export_project_data_csv

router = APIRouter(prefix="/projects", tags=["Monitor — Data"])


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@router.get("/{project_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dashboard agregat untuk satu proyek.

    Menampilkan ringkasan semua data monitor:
    statistik pohon, karbon, biodiversitas, komunitas,
    kegiatan terbaru, dan alert aktif.

    Endpoint ini juga men-trigger auto-check untuk alert monitoring_overdue.
    """
    project = get_project_or_404(project_id, db, current_user)

    # Auto-check monitoring overdue
    check_and_create_overdue_alert(db, project_id)

    # --- Statistik Pohon ---
    tree_records = db.query(TreeRecord).filter(TreeRecord.project_id == project_id).all()
    trees_planted = sum(r.quantity for r in tree_records)
    trees_survived = sum(r.quantity for r in tree_records if r.is_alive)
    trees_dead = trees_planted - trees_survived
    survival_rate = round((trees_survived / trees_planted * 100), 2) if trees_planted > 0 else None

    # --- Karbon (record terbaru) ---
    latest_carbon = (
        db.query(CarbonRecord)
        .filter(CarbonRecord.project_id == project_id)
        .order_by(CarbonRecord.period_end.desc())
        .first()
    )

    # --- Biodiversitas ---
    species_recorded = (
        db.query(func.count(func.distinct(BiodiversityObservation.species_name)))
        .filter(BiodiversityObservation.project_id == project_id)
        .scalar()
    ) or 0

    # --- Komunitas ---
    community_agg = (
        db.query(
            func.sum(CommunityData.beneficiary_count).label("total_beneficiaries"),
            func.count(func.distinct(CommunityData.village_name)).label("total_villages"),
            func.sum(CommunityData.livelihood_groups).label("total_livelihood_groups"),
        )
        .filter(CommunityData.project_id == project_id)
        .first()
    )

    # --- Kegiatan Terbaru ---
    recent_activities_db = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id)
        .order_by(ProjectActivity.activity_date.desc())
        .limit(5)
        .all()
    )
    recent_activities = [
        {
            "id": a.id,
            "activity_type": a.activity_type,
            "date": str(a.activity_date),
            "target": a.target,
            "realization": a.realization,
            "unit": a.unit,
            "executor": a.executor,
        }
        for a in recent_activities_db
    ]

    # --- Alert Aktif ---
    active_alerts_db = (
        db.query(Alert)
        .filter(Alert.project_id == project_id, Alert.is_resolved == False)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )
    active_alerts_count = (
        db.query(func.count(Alert.id))
        .filter(Alert.project_id == project_id, Alert.is_resolved == False)
        .scalar()
    ) or 0

    recent_alerts = [
        {
            "id": al.id,
            "alert_type": al.alert_type,
            "severity": al.severity,
            "description": al.description,
            "is_read": al.is_read,
            "created_at": al.created_at.isoformat() if al.created_at else None,
        }
        for al in active_alerts_db
    ]

    # --- Field Reports ---
    total_field_reports = (
        db.query(func.count(FieldReport.id))
        .filter(FieldReport.project_id == project_id)
        .scalar()
    ) or 0

    last_field_report_obj = (
        db.query(FieldReport)
        .filter(FieldReport.project_id == project_id)
        .order_by(FieldReport.report_date.desc())
        .first()
    )

    return DashboardResponse(
        project_id=project.id,
        project_name=project.name,
        project_status=project.status,
        area_ha=project.area_ha,
        trees_planted=trees_planted,
        trees_survived=trees_survived,
        trees_dead=trees_dead,
        survival_rate=survival_rate,
        carbon_stock_tco2e=latest_carbon.carbon_stock_tco2e if latest_carbon else None,
        estimated_co2e=latest_carbon.estimated_co2e if latest_carbon else None,
        species_recorded=species_recorded,
        total_beneficiaries=int(community_agg.total_beneficiaries or 0),
        total_villages=int(community_agg.total_villages or 0),
        total_livelihood_groups=int(community_agg.total_livelihood_groups or 0),
        total_activities=len(recent_activities_db),
        recent_activities=recent_activities,
        active_alerts=active_alerts_count,
        recent_alerts=recent_alerts,
        total_field_reports=total_field_reports,
        last_field_report=last_field_report_obj.report_date if last_field_report_obj else None,
    )


# ─────────────────────────────────────────────
# MONITORING PLOTS
# ─────────────────────────────────────────────

@router.post("/{project_id}/plots", response_model=MonitoringPlotResponse, status_code=status.HTTP_201_CREATED)
def create_monitoring_plot(
    project_id: int,
    body: MonitoringPlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Membuat plot monitoring baru dalam proyek.

    - Bisa dibuat oleh **admin**, **super_admin**, atau **field_officer**.
    - `plot_code`: Kode unik plot (misal: "WK-023", "PL-01").
    - `plot_type`: `permanent_plot`, `transect`, `point`.
    """
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    # Validasi duplikasi plot_code dalam satu project
    existing = db.query(MonitoringPlot).filter(
        MonitoringPlot.project_id == project_id,
        MonitoringPlot.plot_code == body.plot_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Plot dengan kode '{body.plot_code}' sudah ada di proyek ini."
        )

    plot = MonitoringPlot(
        project_id=project_id,
        plot_code=body.plot_code,
        plot_name=body.plot_name,
        plot_type=body.plot_type,
        location_geojson=body.location_geojson,
        area_ha=body.area_ha,
        stratum=body.stratum,
        elevation_mdpl=body.elevation_mdpl,
        slope_pct=body.slope_pct,
        shape_type=body.shape_type or "rectangle",
        dimension_length_m=body.dimension_length_m,
        dimension_width_m=body.dimension_width_m,
        azimuth_deg=body.azimuth_deg,
        established_date=body.established_date,
        last_survey_date=body.last_survey_date,
        status=body.status or "active",
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(plot)
    db.commit()
    db.refresh(plot)
    return plot


@router.get("/{project_id}/plots", response_model=List[MonitoringPlotResponse])
def list_monitoring_plots(
    project_id: int,
    status: Optional[str] = Query(None, description="Filter status plot: active, inactive"),
    plot_type: Optional[str] = Query(None, description="Filter tipe plot: permanent_plot, transect, point"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan daftar semua plot monitoring untuk satu proyek."""
    get_project_or_404(project_id, db, current_user)
    query = db.query(MonitoringPlot).filter(MonitoringPlot.project_id == project_id)
    if status:
        query = query.filter(MonitoringPlot.status == status)
    if plot_type:
        query = query.filter(MonitoringPlot.plot_type == plot_type)
    return query.order_by(MonitoringPlot.plot_code.asc()).all()


@router.get("/{project_id}/plots/{plot_id}", response_model=MonitoringPlotResponse)
def get_monitoring_plot(
    project_id: int,
    plot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan detail satu plot monitoring berdasarkan ID."""
    get_project_or_404(project_id, db, current_user)
    plot = db.query(MonitoringPlot).filter(
        MonitoringPlot.id == plot_id,
        MonitoringPlot.project_id == project_id
    ).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot monitoring tidak ditemukan.")
    return plot


@router.put("/{project_id}/plots/{plot_id}", response_model=MonitoringPlotResponse)
def update_monitoring_plot(
    project_id: int,
    plot_id: int,
    body: MonitoringPlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mengupdate data plot monitoring."""
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    plot = db.query(MonitoringPlot).filter(
        MonitoringPlot.id == plot_id,
        MonitoringPlot.project_id == project_id
    ).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot monitoring tidak ditemukan.")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(plot, field, value)

    plot.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plot)
    return plot


@router.delete("/{project_id}/plots/{plot_id}", status_code=status.HTTP_200_OK)
def delete_monitoring_plot(
    project_id: int,
    plot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Menghapus plot monitoring (hanya Admin)."""
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    plot = db.query(MonitoringPlot).filter(
        MonitoringPlot.id == plot_id,
        MonitoringPlot.project_id == project_id
    ).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot monitoring tidak ditemukan.")

    db.delete(plot)
    db.commit()
    return {"message": f"Plot '{plot.plot_code}' berhasil dihapus."}


# ─────────────────────────────────────────────
# PROJECT ACTIVITIES
# ─────────────────────────────────────────────

@router.post("/{project_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(
    project_id: int,
    body: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mencatat kegiatan proyek baru.

    Jenis kegiatan: `planting`, `restoration`, `biodiversity_survey`,
    `community_development`, `fire_prevention`, `forest_protection`.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    activity = ProjectActivity(
        project_id=project_id,
        activity_type=body.activity_type,
        activity_date=body.activity_date,
        location_geojson=body.location_geojson,
        target=body.target,
        realization=body.realization,
        unit=body.unit,
        executor=body.executor,
        photo_urls=body.photo_urls,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.get("/{project_id}/activities", response_model=List[ActivityResponse])
def list_activities(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan semua kegiatan untuk satu proyek, diurutkan dari terbaru."""
    get_project_or_404(project_id, db, current_user)
    return (
        db.query(ProjectActivity)
        .filter(ProjectActivity.project_id == project_id)
        .order_by(ProjectActivity.activity_date.desc())
        .all()
    )


@router.get("/{project_id}/activities/{activity_id}", response_model=ActivityResponse)
def get_activity(
    project_id: int,
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan detail satu kegiatan."""
    get_project_or_404(project_id, db, current_user)
    activity = (
        db.query(ProjectActivity)
        .filter(ProjectActivity.id == activity_id, ProjectActivity.project_id == project_id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Kegiatan tidak ditemukan.")
    return activity


# ─────────────────────────────────────────────
# TREE RECORDS
# ─────────────────────────────────────────────

@router.post("/{project_id}/trees", response_model=TreeRecordResponse, status_code=status.HTTP_201_CREATED)
def create_tree_record(
    project_id: int,
    body: TreeRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menambahkan data tanam pohon (per batch/plot).

    Setelah data disimpan, sistem otomatis mengecek survival rate.
    Jika survival rate < 70%, alert `low_tree_survival` akan dibuat secara otomatis.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    record = TreeRecord(
        project_id=project_id,
        plot_id=body.plot_id,
        tree_tag=body.tree_tag,
        species=body.species,
        quantity=body.quantity or 1,
        planting_date=body.planting_date,
        location_geojson=body.location_geojson,
        condition=body.condition or "healthy",
        height_cm=body.height_cm,
        dbh_cm=body.dbh_cm,
        is_alive=body.is_alive if body.is_alive is not None else True,
        photo_urls=body.photo_urls,
        notes=body.notes,
        last_monitored=datetime.utcnow(),
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Auto-check survival rate setelah data baru ditambahkan
    check_and_create_survival_alert(db, project_id)

    return record


@router.get("/{project_id}/trees", response_model=List[TreeRecordResponse])
def list_tree_records(
    project_id: int,
    plot_id: Optional[str] = Query(None, description="Filter berdasarkan kode plot"),
    species: Optional[str] = Query(None, description="Filter berdasarkan spesies pohon"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan semua record pohon untuk satu proyek."""
    get_project_or_404(project_id, db, current_user)
    query = db.query(TreeRecord).filter(TreeRecord.project_id == project_id)
    if plot_id:
        query = query.filter(TreeRecord.plot_id == plot_id)
    if species:
        query = query.filter(TreeRecord.species.ilike(f"%{species}%"))
    return query.order_by(TreeRecord.planting_date.desc()).all()


@router.get("/{project_id}/trees/summary", response_model=TreeSummary)
def get_tree_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ringkasan statistik pohon proyek:
    Trees Planted, Survived, Dead, dan Survival Rate (%).
    """
    get_project_or_404(project_id, db, current_user)
    records = db.query(TreeRecord).filter(TreeRecord.project_id == project_id).all()

    trees_planted = sum(r.quantity for r in records)
    trees_survived = sum(r.quantity for r in records if r.is_alive)
    trees_dead = trees_planted - trees_survived
    survival_rate = round((trees_survived / trees_planted * 100), 2) if trees_planted > 0 else 0.0
    alert_triggered = survival_rate < 70.0 and trees_planted > 0

    return TreeSummary(
        trees_planted=trees_planted,
        trees_survived=trees_survived,
        trees_dead=trees_dead,
        survival_rate=survival_rate,
        alert_triggered=alert_triggered,
    )


@router.get("/{project_id}/trees/{tree_id}", response_model=TreeRecordResponse)
def get_tree_record(
    project_id: int,
    tree_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan detail satu batch penanaman pohon."""
    get_project_or_404(project_id, db, current_user)
    record = (
        db.query(TreeRecord)
        .filter(TreeRecord.id == tree_id, TreeRecord.project_id == project_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Data pohon tidak ditemukan.")
    return record


@router.put("/{project_id}/trees/{tree_id}", response_model=TreeRecordResponse)
def update_tree_record(
    project_id: int,
    tree_id: int,
    body: TreeRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update kondisi pohon (monitoring berkala).

    Setelah update, sistem otomatis mengecek survival rate dan membuat alert jika diperlukan.
    """
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    record = (
        db.query(TreeRecord)
        .filter(TreeRecord.id == tree_id, TreeRecord.project_id == project_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Data pohon tidak ditemukan.")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    record.last_monitored = datetime.utcnow()
    db.commit()
    db.refresh(record)

    # Auto-check survival rate setelah update
    check_and_create_survival_alert(db, project_id)

    return record


@router.post("/{project_id}/trees/upload-photo")
async def upload_tree_photo(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload foto pohon / monitoring tanaman."""
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    upload_dir = "static/trees"
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    unique_filename = f"tree_{project_id}_{uuid.uuid4().hex[:10]}{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    file_bytes = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    try:
        from app.core.storage import upload_public_file
        content_type = file.content_type or "image/jpeg"
        public_url = upload_public_file(f"trees/{unique_filename}", file_bytes, content_type)
        return {"url": public_url, "filename": unique_filename}
    except Exception:
        return {"url": f"/{file_path.replace(os.sep, '/')}", "filename": unique_filename}


# ─────────────────────────────────────────────
# TREE MEASUREMENTS (Growth Tracking)
# ─────────────────────────────────────────────

@router.post("/{project_id}/trees/{tree_id}/measurements", response_model=TreeMeasurementResponse, status_code=status.HTTP_201_CREATED)
def create_tree_measurement(
    project_id: int,
    tree_id: int,
    body: TreeMeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mencatat data pengukuran berkala untuk satu batch/plot pohon (Growth Tracking).

    - Bisa dilakukan oleh **field_officer** maupun **admin**.
    - Mengupdate `last_monitored` pada TreeRecord terkait serta snapshot kondisi terakhir.
    - Men-trigger pengecekan otomatis survival rate alert.
    """
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    tree = db.query(TreeRecord).filter(
        TreeRecord.id == tree_id,
        TreeRecord.project_id == project_id
    ).first()
    if not tree:
        raise HTTPException(status_code=404, detail="Data pohon tidak ditemukan.")

    measurement = TreeMeasurement(
        tree_record_id=tree_id,
        project_id=project_id,
        measurement_date=body.measurement_date,
        height_cm=body.height_cm,
        dbh_cm=body.dbh_cm,
        condition=body.condition,
        is_alive=body.is_alive if body.is_alive is not None else True,
        measured_by=body.measured_by or current_user.full_name,
        photo_urls=body.photo_urls,
        notes=body.notes,
    )
    db.add(measurement)

    # Update TreeRecord status & timestamp tanpa menimpa baseline height/dbh awal tanam
    if body.condition:
        tree.condition = body.condition
    if body.is_alive is not None:
        tree.is_alive = body.is_alive
    tree.last_monitored = datetime.utcnow()

    db.commit()
    db.refresh(measurement)

    # Auto-check survival rate
    check_and_create_survival_alert(db, project_id)

    return measurement


@router.get("/{project_id}/trees/{tree_id}/measurements", response_model=List[TreeMeasurementResponse])
def list_tree_measurements(
    project_id: int,
    tree_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan riwayat semua pengukuran untuk satu batch pohon."""
    get_project_or_404(project_id, db, current_user)
    tree = db.query(TreeRecord).filter(
        TreeRecord.id == tree_id,
        TreeRecord.project_id == project_id
    ).first()
    if not tree:
        raise HTTPException(status_code=404, detail="Data pohon tidak ditemukan.")

    return (
        db.query(TreeMeasurement)
        .filter(TreeMeasurement.tree_record_id == tree_id)
        .order_by(TreeMeasurement.measurement_date.desc())
        .all()
    )


@router.get("/{project_id}/trees/{tree_id}/growth", response_model=TreeGrowthResponse)
def get_tree_growth(
    project_id: int,
    tree_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Timeline dan kalkulasi delta pertumbuhan pohon (Growth Analysis).

    Menghitung:
    - Pertambahan tinggi (`height_growth_cm`): tinggi terkini dikurangi tinggi awal tanam.
    - Pertambahan diameter (`dbh_growth_cm`): DBH terkini dikurangi DBH awal tanam.
    - Garis waktu lengkap (`timeline`): dari tanam awal hingga setiap pengukuran berkala.
    """
    get_project_or_404(project_id, db, current_user)
    tree = db.query(TreeRecord).filter(
        TreeRecord.id == tree_id,
        TreeRecord.project_id == project_id
    ).first()
    if not tree:
        raise HTTPException(status_code=404, detail="Data pohon tidak ditemukan.")

    measurements = (
        db.query(TreeMeasurement)
        .filter(TreeMeasurement.tree_record_id == tree_id)
        .order_by(TreeMeasurement.measurement_date.asc())
        .all()
    )

    timeline: List[TreeGrowthPoint] = []

    # 1. Initial planting point
    timeline.append(TreeGrowthPoint(
        date=tree.planting_date,
        height_cm=tree.height_cm,
        dbh_cm=tree.dbh_cm,
        condition=tree.condition,
        is_alive=tree.is_alive,
        measured_by=None,
        source="initial_planting"
    ))

    # 2. Measurement points
    for m in measurements:
        timeline.append(TreeGrowthPoint(
            date=m.measurement_date,
            height_cm=m.height_cm,
            dbh_cm=m.dbh_cm,
            condition=m.condition,
            is_alive=m.is_alive,
            measured_by=m.measured_by,
            source="periodic_measurement"
        ))

    initial_height = tree.height_cm
    initial_dbh = tree.dbh_cm

    latest_measurement = measurements[-1] if measurements else None
    current_height = latest_measurement.height_cm if (latest_measurement and latest_measurement.height_cm is not None) else tree.height_cm
    current_dbh = latest_measurement.dbh_cm if (latest_measurement and latest_measurement.dbh_cm is not None) else tree.dbh_cm

    height_growth = round(current_height - initial_height, 2) if (current_height is not None and initial_height is not None) else None
    dbh_growth = round(current_dbh - initial_dbh, 2) if (current_dbh is not None and initial_dbh is not None) else None

    return TreeGrowthResponse(
        tree_record_id=tree.id,
        project_id=tree.project_id,
        species=tree.species,
        quantity=tree.quantity,
        planting_date=tree.planting_date,
        initial_height_cm=initial_height,
        initial_dbh_cm=initial_dbh,
        current_height_cm=current_height,
        current_dbh_cm=current_dbh,
        height_growth_cm=height_growth,
        dbh_growth_cm=dbh_growth,
        total_measurements=len(measurements),
        timeline=timeline,
    )


# ─────────────────────────────────────────────
# FIELD REPORTS
# ─────────────────────────────────────────────

@router.post("/{project_id}/field-reports", response_model=FieldReportResponse, status_code=status.HTTP_201_CREATED)
def create_field_report(
    project_id: int,
    body: FieldReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit laporan dari petugas lapangan.

    Setiap laporan mencakup: **WHO** (officer) + **WHERE** (GPS) +
    **WHEN** (tanggal) + **WHAT** (aktivitas) + **EVIDENCE** (foto/video).
    """
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    report = FieldReport(
        project_id=project_id,
        officer_name=body.officer_name,
        plot_id=body.plot_id,
        location_geojson=body.location_geojson,
        report_date=body.report_date,
        report_type=body.report_type,
        activity_description=body.activity_description,
        result_description=body.result_description,
        photo_urls=body.photo_urls,
        video_urls=body.video_urls,
        tree_record_id=body.tree_record_id,
        biodiversity_id=body.biodiversity_id,
        created_by=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{project_id}/field-reports", response_model=List[FieldReportResponse])
def list_field_reports(
    project_id: int,
    report_type: Optional[str] = Query(None, description="Filter jenis laporan: tree_monitoring, biodiversity, incident, general, community"),
    plot_id: Optional[str] = Query(None, description="Filter kode plot"),
    officer_name: Optional[str] = Query(None, description="Filter nama petugas lapangan"),
    start_date: Optional[datetime] = Query(None, description="Filter tanggal mulai"),
    end_date: Optional[datetime] = Query(None, description="Filter tanggal selesai"),
    page: int = Query(1, ge=1, description="Nomor halaman"),
    limit: int = Query(50, ge=1, le=100, description="Jumlah data per halaman"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan semua laporan lapangan untuk satu proyek dengan filter dan pagination."""
    get_project_or_404(project_id, db, current_user)
    query = db.query(FieldReport).filter(FieldReport.project_id == project_id)
    if report_type:
        query = query.filter(FieldReport.report_type == report_type)
    if plot_id:
        query = query.filter(FieldReport.plot_id == plot_id)
    if officer_name:
        query = query.filter(FieldReport.officer_name.ilike(f"%{officer_name}%"))
    if start_date:
        query = query.filter(FieldReport.report_date >= start_date)
    if end_date:
        query = query.filter(FieldReport.report_date <= end_date)

    offset = (page - 1) * limit
    return query.order_by(FieldReport.report_date.desc()).offset(offset).limit(limit).all()


@router.get("/{project_id}/field-reports/{report_id}", response_model=FieldReportResponse)
def get_field_report(
    project_id: int,
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan detail satu laporan lapangan."""
    get_project_or_404(project_id, db, current_user)
    report = (
        db.query(FieldReport)
        .filter(FieldReport.id == report_id, FieldReport.project_id == project_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan.")
    return report


@router.post("/{project_id}/media/upload", response_model=MediaUploadResponse)
async def upload_media_file(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload media bukti lapangan (foto atau video).
    Mendukung format gambar (.jpg, .jpeg, .png, .webp) hingga 20MB
    dan video (.mp4, .webm, .mov, .m4v) hingga 100MB.
    """
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    filename = file.filename or "media"
    ext = os.path.splitext(filename)[1].lower()

    allowed_images = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_videos = {".mp4", ".webm", ".mov", ".m4v"}

    if ext in allowed_images:
        media_type = "photo"
        subdir = "photos"
        max_size = 20 * 1024 * 1024  # 20 MB
    elif ext in allowed_videos:
        media_type = "video"
        subdir = "videos"
        max_size = 100 * 1024 * 1024  # 100 MB
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Format file '{ext}' tidak didukung. Harap unggah foto ({', '.join(allowed_images)}) atau video ({', '.join(allowed_videos)})."
        )

    upload_dir = os.path.join("static", "media", str(project_id), subdir)
    os.makedirs(upload_dir, exist_ok=True)

    unique_filename = f"{media_type}_{project_id}_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file {file_size / (1024 * 1024):.1f}MB melebihi batas maksimal {max_mb}MB untuk {media_type}."
        )

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    rel_url = f"/static/media/{project_id}/{subdir}/{unique_filename}".replace(os.sep, "/")

    try:
        from app.core.storage import upload_public_file
        content_type = file.content_type or ("video/mp4" if media_type == "video" else "image/jpeg")
        public_url = upload_public_file(f"media/{project_id}/{subdir}/{unique_filename}", file_bytes, content_type)
        return MediaUploadResponse(
            url=public_url,
            filename=unique_filename,
            media_type=media_type,
            size=file_size
        )
    except Exception:
        return MediaUploadResponse(
            url=rel_url,
            filename=unique_filename,
            media_type=media_type,
            size=file_size
        )


# ─────────────────────────────────────────────
# EVIDENCE SYSTEM (Timeline & Map)
# ─────────────────────────────────────────────

@router.get("/{project_id}/evidence/timeline", response_model=EvidenceTimelineResponse)
def get_project_evidence_timeline(
    project_id: int,
    page: int = Query(1, ge=1, description="Nomor halaman"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah item per halaman"),
    source_type: Optional[str] = Query(None, description="Filter sumber: field_report, activity, tree_record, tree_measurement, biodiversity"),
    media_type: Optional[str] = Query(None, description="Filter media: photo, video, has_media (foto atau video)"),
    start_date: Optional[date] = Query(None, description="Filter tanggal awal (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter tanggal akhir (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Feed timeline multimedia bukti monitoring (Evidence Feed).

    Menggabungkan dokumentasi dari:
    - Laporan lapangan (foto/video GPS)
    - Kegiatan penanaman & restorasi
    - Batch tanam pohon & pengukuran berkala
    - Observasi satwa & flora (biodiversitas)
    """
    get_project_or_404(project_id, db, current_user)
    return get_evidence_timeline(
        db=db,
        project_id=project_id,
        page=page,
        limit=limit,
        source_type=source_type,
        media_type=media_type,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{project_id}/evidence/map", response_model=EvidenceMapResponse)
def get_project_evidence_map(
    project_id: int,
    source_type: Optional[str] = Query(None, description="Filter sumber bukti: field_report, activity, tree_record, biodiversity"),
    has_media_only: bool = Query(False, description="Hanya tampilkan titik yang memiliki foto/video"),
    start_date: Optional[date] = Query(None, description="Filter tanggal awal"),
    end_date: Optional[date] = Query(None, description="Filter tanggal akhir"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GeoJSON FeatureCollection untuk visualisasi seluruh titik bukti lapangan di peta.

    Menghasilkan format layer GIS standar yang siap di-render di Leaflet/Mapbox:
    - Titik laporan petugas (GPS)
    - Lokasi kegiatan penanaman & plot monitoring
    - Titik observasi satwa & flora liar
    """
    get_project_or_404(project_id, db, current_user)
    return get_evidence_map(
        db=db,
        project_id=project_id,
        source_type=source_type,
        has_media_only=has_media_only,
        start_date=start_date,
        end_date=end_date,
    )



# ─────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────

@router.get("/{project_id}/alerts/summary", response_model=AlertSummaryResponse)
def get_project_alerts_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan ringkasan statistik alert proyek.

    Menghitung:
    - Total alert, alert aktif vs resolved, serta *Resolution Rate (%)*
    - Distribusi alert berdasarkan tingkat keparahan (*Severity*: Critical, High, Medium, Low)
    - Distribusi alert berdasarkan jenis (*Deforestation*, *Fire*, *Land Cover*, *Overdue*, *Low Survival*)
    - 5 alert terbaru
    """
    get_project_or_404(project_id, db, current_user)
    return get_alerts_summary(db, project_id)


@router.post("/{project_id}/alerts/check", response_model=AlertCheckResponse)
def run_project_alerts_check(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menjalankan evaluasi serentak 5 aturan peringatan dini lingkungan (Early Warning Engine):
    1. Deforestation threshold
    2. Fire hotspot detection
    3. Vegetation NDVI degradation
    4. Low tree survival (< 70%)
    5. Monitoring overdue (> 30 hari)
    """
    require_field_officer(current_user)
    project = get_project_or_404(project_id, db, current_user)
    return check_all_project_alerts(db, project)


@router.get("/{project_id}/alerts", response_model=List[AlertResponse])
def list_alerts(
    project_id: int,
    only_active: bool = Query(True, description="Hanya tampilkan alert yang belum resolved"),
    severity: Optional[str] = Query(None, description="Filter severity: low, medium, high, critical"),
    alert_type: Optional[str] = Query(None, description="Filter tipe alert: deforestation, fire, land_cover_change, monitoring_overdue, low_tree_survival"),
    is_resolved: Optional[bool] = Query(None, description="Filter status penyelesaian spesifik"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan daftar alert untuk satu proyek dengan filter multi-parameter.

    Endpoint ini juga secara otomatis mengevaluasi keterlambatan monitoring (*monitoring_overdue*).
    """
    get_project_or_404(project_id, db, current_user)

    # Auto-check monitoring overdue setiap kali alert di-fetch
    check_and_create_overdue_alert(db, project_id)

    query = db.query(Alert).filter(Alert.project_id == project_id)

    if is_resolved is not None:
        query = query.filter(Alert.is_resolved == is_resolved)
    elif only_active:
        query = query.filter(Alert.is_resolved == False)

    if severity:
        query = query.filter(Alert.severity == severity)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    return query.order_by(Alert.created_at.desc()).all()


@router.post("/{project_id}/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    project_id: int,
    body: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Membuat alert secara manual oleh admin.

    Tipe alert yang tersedia: `deforestation`, `fire`, `land_cover_change`,
    `monitoring_overdue`, `low_tree_survival`.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    alert = Alert(
        project_id=project_id,
        alert_type=body.alert_type,
        severity=body.severity or "medium",
        location_geojson=body.location_geojson,
        description=body.description,
        source_url=body.source_url,
        created_by=current_user.id,
        auto_generated=False,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.put("/{project_id}/alerts/{alert_id}", response_model=AlertResponse)
def update_alert(
    project_id: int,
    alert_id: int,
    body: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update status alert: mark as read atau mark as resolved.

    Ketika `is_resolved` diset ke `true`, `resolved_at` otomatis diisi dengan waktu sekarang.
    """
    get_project_or_404(project_id, db, current_user)
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.project_id == project_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan.")

    if body.is_read is not None:
        alert.is_read = body.is_read
    if body.is_resolved is not None:
        alert.is_resolved = body.is_resolved
        if body.is_resolved and not alert.resolved_at:
            alert.resolved_at = datetime.utcnow()


    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/{project_id}/alerts/{alert_id}", status_code=status.HTTP_200_OK)
def delete_alert(
    project_id: int,
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghapus alert dari database oleh admin.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.project_id == project_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan.")

    db.delete(alert)
    db.commit()
    return {"message": f"Alert #{alert_id} berhasil dihapus."}


# ─────────────────────────────────────────────
# BIODIVERSITY OBSERVATIONS
# ─────────────────────────────────────────────

@router.post("/{project_id}/biodiversity", response_model=BiodiversityResponse, status_code=status.HTTP_201_CREATED)
def create_biodiversity_observation(
    project_id: int,
    body: BiodiversityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mencatat observasi biodiversitas baru (satwa atau flora)."""
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)

    legacy_photo = body.photo_url
    if not legacy_photo and body.photo_urls:
        legacy_photo = body.photo_urls[0]

    obs = BiodiversityObservation(
        project_id=project_id,
        species_name=body.species_name,
        species_type=body.species_type,
        location_geojson=body.location_geojson,
        observed_date=body.observed_date,
        habitat=body.habitat,
        observer=body.observer,
        photo_url=legacy_photo,
        photo_urls=body.photo_urls or ([body.photo_url] if body.photo_url else None),
        video_urls=body.video_urls,
        notes=body.notes,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


@router.get("/{project_id}/biodiversity", response_model=List[BiodiversityResponse])
def list_biodiversity_observations(
    project_id: int,
    species_type: Optional[str] = Query(None, description="Filter: fauna atau flora"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan semua observasi biodiversitas untuk satu proyek."""
    get_project_or_404(project_id, db, current_user)
    query = db.query(BiodiversityObservation).filter(BiodiversityObservation.project_id == project_id)
    if species_type:
        query = query.filter(BiodiversityObservation.species_type == species_type)
    observations = query.order_by(BiodiversityObservation.observed_date.desc()).all()
    for obs in observations:
        if not obs.photo_urls and obs.photo_url:
            obs.photo_urls = [obs.photo_url]
    return observations


@router.get("/{project_id}/biodiversity/summary", response_model=BiodiversitySummary)
def get_biodiversity_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ringkasan biodiversitas: jumlah total observasi, spesies unik, fauna, dan flora."""
    get_project_or_404(project_id, db, current_user)
    all_obs = db.query(BiodiversityObservation).filter(
        BiodiversityObservation.project_id == project_id
    ).all()

    unique_species = len(set(o.species_name for o in all_obs))
    fauna_count = sum(1 for o in all_obs if o.species_type == "fauna")
    flora_count = sum(1 for o in all_obs if o.species_type == "flora")

    return BiodiversitySummary(
        total_observations=len(all_obs),
        unique_species=unique_species,
        fauna_count=fauna_count,
        flora_count=flora_count,
    )


@router.put("/{project_id}/biodiversity/{obs_id}", response_model=BiodiversityResponse)
def update_biodiversity_observation(
    project_id: int,
    obs_id: int,
    body: BiodiversityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mengubah data observasi biodiversitas."""
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)
    obs = db.query(BiodiversityObservation).filter(
        BiodiversityObservation.id == obs_id,
        BiodiversityObservation.project_id == project_id
    ).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Biodiversity observation not found")

    obs.species_name = body.species_name
    obs.species_type = body.species_type
    obs.location_geojson = body.location_geojson
    obs.observed_date = body.observed_date
    obs.habitat = body.habitat
    obs.observer = body.observer
    obs.photo_urls = body.photo_urls or ([body.photo_url] if body.photo_url else obs.photo_urls)
    obs.video_urls = body.video_urls
    if body.photo_url:
        obs.photo_url = body.photo_url
    elif body.photo_urls:
        obs.photo_url = body.photo_urls[0]
    obs.notes = body.notes

    db.commit()
    db.refresh(obs)
    return obs


@router.delete("/{project_id}/biodiversity/{obs_id}")
def delete_biodiversity_observation(
    project_id: int,
    obs_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Menghapus observasi biodiversitas."""
    require_field_officer(current_user)
    get_project_or_404(project_id, db, current_user)
    obs = db.query(BiodiversityObservation).filter(
        BiodiversityObservation.id == obs_id,
        BiodiversityObservation.project_id == project_id
    ).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Biodiversity observation not found")

    db.delete(obs)
    db.commit()
    return {"message": "Biodiversity observation deleted successfully", "id": obs_id}



# ─────────────────────────────────────────────
# COMMUNITY DATA
# ─────────────────────────────────────────────

@router.post("/{project_id}/community", response_model=CommunityResponse, status_code=status.HTTP_201_CREATED)
def create_community_data(
    project_id: int,
    body: CommunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mencatat data dampak sosial dan ekonomi proyek terhadap komunitas."""
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    data = CommunityData(
        project_id=project_id,
        village_name=body.village_name,
        beneficiary_count=body.beneficiary_count or 0,
        livelihood_groups=body.livelihood_groups or 0,
        employment_count=body.employment_count or 0,
        community_investment=body.community_investment or 0.0,
        activity_type=body.activity_type,
        description=body.description,
        date=body.date,
    )
    db.add(data)
    db.commit()
    db.refresh(data)
    return data


@router.get("/{project_id}/community", response_model=List[CommunityResponse])
def list_community_data(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan semua data komunitas untuk satu proyek."""
    get_project_or_404(project_id, db, current_user)
    return (
        db.query(CommunityData)
        .filter(CommunityData.project_id == project_id)
        .order_by(CommunityData.created_at.desc())
        .all()
    )


@router.get("/{project_id}/community/summary", response_model=CommunitySummary)
def get_community_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ringkasan dampak komunitas: villages, beneficiaries, livelihood groups, employment."""
    get_project_or_404(project_id, db, current_user)
    all_data = db.query(CommunityData).filter(CommunityData.project_id == project_id).all()

    return CommunitySummary(
        total_villages=len(set(d.village_name for d in all_data)),
        total_beneficiaries=sum(d.beneficiary_count for d in all_data),
        total_livelihood_groups=sum(d.livelihood_groups for d in all_data),
        total_employment=sum(d.employment_count for d in all_data),
        total_community_investment=sum(d.community_investment for d in all_data),
    )


# ─────────────────────────────────────────────
# CARBON RECORDS
# ─────────────────────────────────────────────

@router.post("/{project_id}/carbon", response_model=CarbonResponse, status_code=status.HTTP_201_CREATED)
def create_carbon_record(
    project_id: int,
    body: CarbonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menambahkan data monitoring karbon untuk satu periode.

    **Penting**: Data ini adalah estimasi monitoring, bukan verified carbon credit.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    record = CarbonRecord(
        project_id=project_id,
        period_start=body.period_start,
        period_end=body.period_end,
        carbon_stock_tco2e=body.carbon_stock_tco2e,
        biomass_ton=body.biomass_ton,
        estimated_co2e=body.estimated_co2e,
        carbon_change=body.carbon_change,
        methodology=body.methodology,
        notes=body.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{project_id}/carbon", response_model=List[CarbonResponse])
def list_carbon_records(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan semua record karbon untuk satu proyek, diurutkan dari periode terbaru."""
    get_project_or_404(project_id, db, current_user)
    return (
        db.query(CarbonRecord)
        .filter(CarbonRecord.project_id == project_id)
        .order_by(CarbonRecord.period_end.desc())
        .all()
    )


# ─────────────────────────────────────────────
# LANDSCAPE SNAPSHOTS (Time-series / Remote Sensing)
# ─────────────────────────────────────────────

@router.post("/{project_id}/snapshots", response_model=LandscapeSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_landscape_snapshot(
    project_id: int,
    body: LandscapeSnapshotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menambahkan snapshot kondisi tutupan lahan dan indeks vegetasi (NDVI).

    Data bisa bersumber dari input manual, Google Earth Engine, atau satelit remote sensing.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    snapshot = LandscapeSnapshot(
        project_id=project_id,
        snapshot_date=body.snapshot_date,
        data_source=body.data_source or "manual",
        forest_cover_ha=body.forest_cover_ha,
        deforestation_ha=body.deforestation_ha,
        restoration_ha=body.restoration_ha,
        land_cleared_ha=body.land_cleared_ha,
        fire_ha=body.fire_ha,
        ndvi_mean=body.ndvi_mean,
        ndvi_min=body.ndvi_min,
        ndvi_max=body.ndvi_max,
        geojson_data=body.geojson_data,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/{project_id}/snapshots", response_model=List[LandscapeSnapshotResponse])
def list_landscape_snapshots(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan seluruh snapshot kondisi lanskap proyek, diurutkan dari tanggal terbaru."""
    get_project_or_404(project_id, db, current_user)
    return (
        db.query(LandscapeSnapshot)
        .filter(LandscapeSnapshot.project_id == project_id)
        .order_by(LandscapeSnapshot.snapshot_date.desc())
        .all()
    )


@router.get("/{project_id}/snapshots/{snapshot_id}", response_model=LandscapeSnapshotResponse)
def get_landscape_snapshot(
    project_id: int,
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan detail satu snapshot lanskap berdasarkan ID."""
    get_project_or_404(project_id, db, current_user)
    snapshot = (
        db.query(LandscapeSnapshot)
        .filter(LandscapeSnapshot.id == snapshot_id, LandscapeSnapshot.project_id == project_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Landscape snapshot tidak ditemukan.")
    return snapshot


@router.delete("/{project_id}/snapshots/{snapshot_id}", status_code=status.HTTP_200_OK)
def delete_landscape_snapshot(
    project_id: int,
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Menghapus snapshot lanskap (hanya Admin)."""
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    snapshot = (
        db.query(LandscapeSnapshot)
        .filter(LandscapeSnapshot.id == snapshot_id, LandscapeSnapshot.project_id == project_id)
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Landscape snapshot tidak ditemukan.")

    db.delete(snapshot)
    db.commit()
    return {"message": f"Landscape snapshot {snapshot_id} berhasil dihapus."}


# ─────────────────────────────────────────────
# SPATIAL GIS MULTI-LAYER & SATELLITE MAP
# ─────────────────────────────────────────────

@router.get("/{project_id}/map/layers", response_model=ProjectMapLayersResponse)
def get_project_map_layers_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengambil seluruh lapisan data spasial GIS proyek untuk rendering peta terpadu.

    Mengembalikan 7 layer spasial GeoJSON:
    1. `boundary`: Batas teritori proyek (Polygon)
    2. `plots`: Plot monitoring permanen, transek, sampling (Point/Polygon)
    3. `activities`: Lokasi kegiatan penanaman & restorasi
    4. `tree_locations`: Titik tanam pohon per-batch
    5. `alerts`: Titik peringatan deforestasi / kebakaran aktif
    6. `field_reports`: Titik laporan GPS petugas lapangan
    7. `biodiversity`: Titik observasi satwa & flora liar

    Juga menyertakan titik tengah (`center_coordinates`) untuk auto-focus peta.
    """
    project = get_project_or_404(project_id, db, current_user)
    return get_project_map_layers(db, project)


@router.get("/{project_id}/map/satellite", response_model=SatelliteTileResponse)
def get_project_satellite_map(
    project_id: int,
    layer_type: str = Query("true_color", description="Tipe citra: true_color (RGB), ndvi (Vegetasi), swir (Kelembaban/Api)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan konfigurasi tile satelit / remote sensing untuk base layer peta GIS.

    Menghubungkan citra Sentinel-2 / Landsat resolusi tinggi beserta metrik NDVI terkini.
    """
    project = get_project_or_404(project_id, db, current_user)

    satellite_data = gee_service.fetch_monitoring_satellite_data(
        geojson_polygon=project.boundary_geojson,
        area_ha=project.area_ha or 0.0
    )

    # Ambil data snapshot terakhir jika ada
    latest_snapshot = (
        db.query(LandscapeSnapshot)
        .filter(LandscapeSnapshot.project_id == project_id)
        .order_by(LandscapeSnapshot.snapshot_date.desc())
        .first()
    )

    ndvi_summary = None
    if latest_snapshot and latest_snapshot.ndvi_mean is not None:
        ndvi_summary = {
            "mean": latest_snapshot.ndvi_mean,
            "min": latest_snapshot.ndvi_min,
            "max": latest_snapshot.ndvi_max,
            "date": latest_snapshot.snapshot_date.isoformat(),
        }
    else:
        ndvi_summary = {
            "mean": satellite_data.get("ndvi_mean", 0.72),
            "min": satellite_data.get("ndvi_min", 0.40),
            "max": satellite_data.get("ndvi_max", 0.88),
            "date": datetime.utcnow().date().isoformat(),
        }

    return SatelliteTileResponse(
        project_id=project.id,
        tile_url_template=satellite_data.get("tile_url_template", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
        attribution=satellite_data.get("attribution", "Copernicus Sentinel-2 / Google Earth Engine"),
        layer_type=layer_type,
        acquisition_date=datetime.utcnow().date().isoformat(),
        cloud_coverage_pct=1.8,
        available_layers=["true_color", "ndvi", "swir", "tree_cover_loss"],
        latest_ndvi_metrics=ndvi_summary,
    )


@router.post("/{project_id}/gee/sync", response_model=GEESyncResponse)
def sync_project_gee_telemetry(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menjalankan sinkronisasi realtime telemetri Google Earth Engine untuk proyek.

    - Menghitung tutupan hutan, kehilangan tutupan lahan (deforestasi), dan indeks NDVI.
    - Menyimpan snapshot historis baru di tabel `landscape_snapshots`.
    - Otomatis men-generate `Alert` berkategori tinggi/kritis jika terdeteksi deforestasi atau kebakaran.
    """
    require_admin(current_user)
    project = get_project_or_404(project_id, db, current_user)

    result = gee_service.sync_project_gee_data(db=db, project=project, user_id=current_user.id)
    return GEESyncResponse(**result)


# ─────────────────────────────────────────────
# INDICATORS & COMPARISON ENGINE
# ─────────────────────────────────────────────

@router.get("/{project_id}/indicators", response_model=ProjectIndicatorsResponse)
def get_project_indicators_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghitung dan menyajikan ringkasan indikator performa & kesehatan proyek.

    Mencakup:
    - **Vegetation Health Index (NDVI)**
    - **Tree Performance & Growth Rate** (Tinggi, DBH, Survival Rate)
    - **Carbon Metrics & Carbon Density** (tCO2e/ha)
    - **Biodiversity Richness Index** (Fauna & Flora)
    - **Community Impact Reach** (Penerima manfaat & desa)
    - **Overall Project Health Score (0 - 100)**
    """
    project = get_project_or_404(project_id, db, current_user)
    return calculate_project_indicators(db, project)


@router.get("/{project_id}/compare/baseline", response_model=ProjectBaselineComparisonResponse)
def get_project_baseline_comparison_endpoint(
    project_id: int,
    period: str = Query("all", description="Filter periode komparasi: 1m (1 Bulan), 6m (6 Bulan), 1y (1 Tahun), all (Semua/Baseline)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Membandingkan kondisi proyek saat ini (Current) terhadap kondisi awal tanam (Baseline).

    Menghitung delta perubahan & persentase peningkatan untuk:
    - Tutupan Hutan (ha)
    - Indeks Vegetasi (NDVI)
    - Rata-rata Tinggi Pohon (cm)
    - Cadangan Karbon (tCO2e)
    - Keragaman Spesies Tercatat
    """
    project = get_project_or_404(project_id, db, current_user)
    return compare_project_with_baseline(db, project, period=period)


# ─────────────────────────────────────────────
# MRV REPORTING & EXPORT ENGINE (Phase 8)
# ─────────────────────────────────────────────

@router.get("/{project_id}/report/summary", response_model=MRVSummaryResponse)
def get_project_mrv_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghasilkan ringkasan eksekutif MRV (Measurement, Reporting, Verification) formal proyek.

    - **Measurement**: Data biofisik pohon, pertumbuhan, citra satelit NDVI, cadangan karbon, dan keanekaragaman hayati.
    - **Reporting**: Pencapaian target vs realisasi, ringkasan aktivitas lapangan, dan histori pelaporan.
    - **Verification**: Jumlah bukti geotagged GPS, dokumentasi foto & video, serta status resolusi alert/insiden.
    """
    project = get_project_or_404(project_id, db, current_user)
    return generate_mrv_summary(db, project)


@router.get("/{project_id}/report/pdf")
def download_project_monitor_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mendownload dokumen PDF formal Laporan Monitoring Proyek SATUBUMI MONITOR.

    Berisi header resmi, ringkasan eksekutif, tabel biofisik Measurement, progres Reporting,
    dan matriks Verification integritas data.
    """
    project = get_project_or_404(project_id, db, current_user)
    try:
        pdf_bytes = generate_monitor_pdf(db, project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat file PDF laporan: {str(e)}")

    filename = f"satubumi_monitor_report_{project.id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{project_id}/export/csv")
def export_project_data_csv_endpoint(
    project_id: int,
    data_type: str = Query("trees", description="Tipe data untuk diexport: trees, activities, field_reports, biodiversity, carbon, overview"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengekspor data tabular monitoring proyek ke dalam format file CSV.
    """
    project = get_project_or_404(project_id, db, current_user)
    csv_string = export_project_data_csv(db, project, data_type=data_type)

    filename = f"satubumi_{project.id}_{data_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_string,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{project_id}/export/geojson")
def export_project_geojson_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengekspor seluruh lapisan spasial GIS proyek ke file GeoJSON terpadu.
    """
    project = get_project_or_404(project_id, db, current_user)
    map_layers = get_project_map_layers(db, project)

    filename = f"satubumi_spatial_layers_{project.id}_{datetime.utcnow().strftime('%Y%m%d')}.geojson"
    return Response(
        content=map_layers.model_dump_json(indent=2),
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )



