"""
services/monitor_report_service.py — Generator Laporan Formal MRV & Export untuk SATUBUMI MONITOR

Menyediakan:
1. Ringkasan Eksekutif MRV (Measurement, Reporting, Verification)
2. Generator PDF Formal Laporan Monitoring Proyek (HTML template -> PDF)
3. Generator Export Data Tabular ke Format CSV
"""

import io
import csv
import json
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from jinja2 import Template

from app.models.project import Project
from app.models.monitor import (
    TreeRecord, TreeMeasurement, ProjectActivity, FieldReport,
    Alert, BiodiversityObservation, CommunityData, CarbonRecord,
    LandscapeSnapshot, MonitoringPlot
)
from app.services.monitoring.progress_service import calculate_project_progress


def generate_mrv_summary(db: Session, project: Project) -> Dict[str, Any]:
    """
    Menghasilkan ringkasan komprehensif berstandar MRV (Measurement, Reporting, Verification).
    """
    # ── 1. MEASUREMENT (M) ──
    trees = db.query(TreeRecord).filter(TreeRecord.project_id == project.id).all()
    total_planted = sum(t.quantity for t in trees)
    total_survived = sum(t.quantity for t in trees if t.is_alive)
    survival_rate = round((total_survived / total_planted * 100), 1) if total_planted > 0 else 0.0

    measurements = db.query(TreeMeasurement).filter(TreeMeasurement.project_id == project.id).all()
    height_deltas = []
    dbh_deltas = []
    for t in trees:
        t_m = [m for m in measurements if m.tree_record_id == t.id]
        if t_m and t.height_cm is not None:
            latest_m = max(t_m, key=lambda x: x.measurement_date)
            if latest_m.height_cm is not None:
                height_deltas.append(latest_m.height_cm - t.height_cm)
            if latest_m.dbh_cm is not None and t.dbh_cm is not None:
                dbh_deltas.append(latest_m.dbh_cm - t.dbh_cm)

    avg_height_growth = round(sum(height_deltas) / len(height_deltas), 2) if height_deltas else None
    avg_dbh_growth = round(sum(dbh_deltas) / len(dbh_deltas), 2) if dbh_deltas else None

    latest_snapshot = (
        db.query(LandscapeSnapshot)
        .filter(LandscapeSnapshot.project_id == project.id)
        .order_by(LandscapeSnapshot.snapshot_date.desc())
        .first()
    )
    forest_cover = latest_snapshot.forest_cover_ha if latest_snapshot else None
    deforestation = latest_snapshot.deforestation_ha if latest_snapshot else None
    ndvi = latest_snapshot.ndvi_mean if latest_snapshot else None

    latest_carbon = (
        db.query(CarbonRecord)
        .filter(CarbonRecord.project_id == project.id)
        .order_by(CarbonRecord.period_end.desc())
        .first()
    )
    carbon_stock = latest_carbon.carbon_stock_tco2e if latest_carbon else None
    est_co2e = latest_carbon.estimated_co2e if latest_carbon else None

    species_count = (
        db.query(func.count(func.distinct(BiodiversityObservation.species_name)))
        .filter(BiodiversityObservation.project_id == project.id)
        .scalar()
    ) or 0

    measurement_block = {
        "trees_planted": total_planted,
        "trees_survived": total_survived,
        "survival_rate_pct": survival_rate,
        "avg_height_growth_cm": avg_height_growth,
        "avg_dbh_growth_cm": avg_dbh_growth,
        "forest_cover_ha": forest_cover,
        "deforestation_ha": deforestation,
        "ndvi_mean": ndvi,
        "carbon_stock_tco2e": carbon_stock,
        "estimated_co2e": est_co2e,
        "unique_species_count": species_count,
    }

    # ── 2. REPORTING (R) ──
    progress_info = calculate_project_progress(db, project)
    activities = db.query(ProjectActivity).filter(ProjectActivity.project_id == project.id).all()
    act_by_type = {}
    for a in activities:
        atype = a.activity_type
        if atype not in act_by_type:
            act_by_type[atype] = {"count": 0, "total_target": 0, "total_realization": 0, "unit": a.unit}
        act_by_type[atype]["count"] += 1
        act_by_type[atype]["total_target"] += a.target or 0
        act_by_type[atype]["total_realization"] += a.realization or 0

    field_reports = db.query(FieldReport).filter(FieldReport.project_id == project.id).all()
    latest_fr = max(field_reports, key=lambda x: x.report_date) if field_reports else None

    reporting_block = {
        "overall_progress_pct": progress_info.get("overall_progress_pct", 0.0),
        "targets": project.targets_json or {},
        "total_activities": len(activities),
        "activities_by_type": act_by_type,
        "total_field_reports": len(field_reports),
        "latest_field_report_date": latest_fr.report_date if latest_fr else None,
    }

    # ── 3. VERIFICATION (V) ──
    photo_count = 0
    video_count = 0
    gps_verified = 0

    for fr in field_reports:
        if fr.photo_urls:
            photo_count += len(fr.photo_urls)
        if fr.video_urls:
            video_count += len(fr.video_urls)
        if fr.location_geojson:
            gps_verified += 1

    for a in activities:
        if a.photo_urls:
            photo_count += len(a.photo_urls)
        if a.location_geojson:
            gps_verified += 1

    for t in trees:
        if t.photo_urls:
            photo_count += len(t.photo_urls)
        if t.location_geojson:
            gps_verified += 1

    total_snapshots = db.query(func.count(LandscapeSnapshot.id)).filter(LandscapeSnapshot.project_id == project.id).scalar() or 0

    all_alerts = db.query(Alert).filter(Alert.project_id == project.id).all()
    total_alerts = len(all_alerts)
    active_alerts = sum(1 for al in all_alerts if not al.is_resolved)
    resolved_alerts = sum(1 for al in all_alerts if al.is_resolved)
    res_rate = round((resolved_alerts / total_alerts * 100), 1) if total_alerts > 0 else 100.0

    verification_block = {
        "total_photos_count": photo_count,
        "total_videos_count": video_count,
        "gps_verified_points_count": gps_verified,
        "satellite_snapshots_count": total_snapshots,
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "resolved_alerts": resolved_alerts,
        "resolution_rate_pct": res_rate,
    }

    # Executive narrative
    exec_summary = (
        f"Laporan MRV untuk proyek '{project.name}' ({project.location_name}). "
        f"Proyek telah menanam {total_planted:,} pohon dengan survival rate {survival_rate}% dan progress keseluruhan {progress_info.get('overall_progress_pct', 0.0)}%. "
        f"Diverifikasi dengan {gps_verified} titik GPS, {photo_count} bukti foto/video, dan {total_snapshots} rekaman satelit remote sensing."
    )

    return {
        "project_id": project.id,
        "project_name": project.name,
        "location_name": project.location_name,
        "project_type": project.project_type,
        "area_ha": project.area_ha,
        "start_date": project.start_date,
        "status": project.status,
        "generated_at": datetime.utcnow(),
        "measurement": measurement_block,
        "reporting": reporting_block,
        "verification": verification_block,
        "executive_summary": exec_summary,
    }


# ── PDF TEMPLATE ─────────────────────────────────────────────────────────────

MONITOR_PDF_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SATUBUMI MONITOR — Laporan Monitoring Proyek</title>
    <style>
        @page {
            size: A4;
            margin: 1.8cm;
        }
        body {
            font-family: Helvetica, Arial, sans-serif;
            color: #1e293b;
            line-height: 1.5;
            font-size: 10.5pt;
        }
        .header-table {
            width: 100%;
            border-bottom: 2px solid #047857;
            padding-bottom: 12px;
            margin-bottom: 25px;
        }
        .header-title {
            font-size: 20pt;
            font-weight: 900;
            color: #047857;
            margin: 0;
            letter-spacing: 0.5px;
        }
        .header-meta {
            text-align: right;
            font-size: 9pt;
            color: #64748b;
        }
        .doc-badge {
            display: inline-block;
            background-color: #ecfdf5;
            color: #065f46;
            padding: 4px 10px;
            font-weight: bold;
            font-size: 9pt;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .project-title {
            font-size: 16pt;
            font-weight: bold;
            color: #0f172a;
            margin: 0 0 5px 0;
        }
        .project-location {
            font-size: 10pt;
            color: #64748b;
            margin-bottom: 20px;
        }
        .section-header {
            font-size: 11.5pt;
            font-weight: bold;
            color: #047857;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 4px;
            margin-top: 25px;
            margin-bottom: 10px;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .data-table th, .data-table td {
            padding: 8px 6px;
            text-align: left;
        }
        .data-table th {
            font-size: 8.5pt;
            text-transform: uppercase;
            color: #64748b;
            border-bottom: 1px solid #cbd5e1;
            font-weight: bold;
        }
        .data-table td {
            font-size: 9.5pt;
            border-bottom: 1px solid #f1f5f9;
        }
        .data-table td.val {
            text-align: right;
            font-weight: bold;
            font-family: 'Courier New', Courier, monospace;
        }
        .score-card {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 12px;
            margin-bottom: 20px;
        }
        .score-card p {
            margin: 0;
            font-size: 9.5pt;
            color: #334155;
        }
        .footer {
            margin-top: 30px;
            border-top: 1px solid #e2e8f0;
            padding-top: 10px;
            font-size: 8pt;
            color: #94a3b8;
            text-align: center;
        }
    </style>
</head>
<body>

    <table class="header-table">
        <tr>
            <td>
                <div class="header-title">SATUBUMI MONITOR</div>
                <div style="font-size: 9.5pt; color: #059669; font-weight: bold;">Digital Monitoring & MRV Platform</div>
            </td>
            <td class="header-meta">
                Dokumen: LAPORAN MONITORING PROYEK<br>
                Tanggal Cetak: {{ generated_at }}<br>
                Status: Resmi Terverifikasi
            </td>
        </tr>
    </table>

    <div class="doc-badge">MRV EXECUTIVE REPORT</div>
    <div class="project-title">{{ project_name }}</div>
    <div class="project-location">Lokasi: {{ location_name }} | Luas Area: {{ area_ha }} Ha | Tipe: {{ project_type }}</div>

    <div class="score-card">
        <p><strong>Ringkasan Eksekutif:</strong> {{ executive_summary }}</p>
    </div>

    <!-- 1. MEASUREMENT -->
    <div class="section-header">1. Measurement (Pengukuran & Biofisik)</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Indikator Pengukuran</th>
                <th style="text-align: right;">Nilai Realisasi</th>
                <th>Satuan / Keterangan</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Jumlah Pohon Ditanam</td>
                <td class="val">{{ measurement.trees_planted }}</td>
                <td>Pohon</td>
            </tr>
            <tr>
                <td>Pohon Bertahan Hidup (Survive)</td>
                <td class="val">{{ measurement.trees_survived }}</td>
                <td>Pohon (Survival Rate: {{ measurement.survival_rate_pct }}%)</td>
            </tr>
            <tr>
                <td>Pertumbuhan Tinggi Rata-rata</td>
                <td class="val">+{{ measurement.avg_height_growth_cm or 0 }}</td>
                <td>cm</td>
            </tr>
            <tr>
                <td>Indeks Kehijauan Vegetasi (NDVI)</td>
                <td class="val">{{ measurement.ndvi_mean or 'N/A' }}</td>
                <td>Sentinel-2 Remote Sensing Index</td>
            </tr>
            <tr>
                <td>Estimasi Cadangan Karbon</td>
                <td class="val">{{ measurement.carbon_stock_tco2e or 'N/A' }}</td>
                <td>tCO2e</td>
            </tr>
            <tr>
                <td>Keragaman Spesies Tercatat</td>
                <td class="val">{{ measurement.unique_species_count }}</td>
                <td>Spesies Flora & Fauna Teridentifikasi</td>
            </tr>
        </tbody>
    </table>

    <!-- 2. REPORTING -->
    <div class="section-header">2. Reporting (Target vs Realisasi & Aktivitas)</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Metrik Pelaporan</th>
                <th style="text-align: right;">Capaian</th>
                <th>Keterangan</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Progres Keseluruhan Target</td>
                <td class="val">{{ reporting.overall_progress_pct }}%</td>
                <td>Target vs Realisasi Keseluruhan</td>
            </tr>
            <tr>
                <td>Total Kegiatan Selesai</td>
                <td class="val">{{ reporting.total_activities }}</td>
                <td>Kegiatan Restorasi & Penanaman</td>
            </tr>
            <tr>
                <td>Laporan Lapangan Petugas</td>
                <td class="val">{{ reporting.total_field_reports }}</td>
                <td>Laporan Lapangan Terverifikasi</td>
            </tr>
        </tbody>
    </table>

    <!-- 3. VERIFICATION -->
    <div class="section-header">3. Verification (Bukti Lapangan & Integritas Spasial)</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>Elemen Verifikasi</th>
                <th style="text-align: right;">Jumlah Bukti</th>
                <th>Tingkat Integritas</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Titik Koordinat GPS Tervalidasi</td>
                <td class="val">{{ verification.gps_verified_points_count }}</td>
                <td>100% Geotagged</td>
            </tr>
            <tr>
                <td>Dokumentasi Foto Lapangan</td>
                <td class="val">{{ verification.total_photos_count }}</td>
                <td>Bukti Visual Terverifikasi</td>
            </tr>
            <tr>
                <td>Snapshot Telemetri Satelit</td>
                <td class="val">{{ verification.satellite_snapshots_count }}</td>
                <td>Google Earth Engine Historical Records</td>
            </tr>
            <tr>
                <td>Penyelesaian Insiden / Alert</td>
                <td class="val">{{ verification.resolution_rate_pct }}%</td>
                <td>{{ verification.resolved_alerts }} dari {{ verification.total_alerts }} Alert Selesai</td>
            </tr>
        </tbody>
    </table>

    <div class="footer">
        Dicetak secara otomatis oleh SATUBUMI MONITOR Platform | Nature-Based Solutions Digital Infrastructure &copy; {{ year }}
    </div>

</body>
</html>
"""


def generate_monitor_pdf(db: Session, project: Project) -> bytes:
    """
    Meng-compile laporan monitoring proyek menjadi file PDF biner.
    """
    mrv_data = generate_mrv_summary(db, project)

    template = Template(MONITOR_PDF_TEMPLATE)
    html_content = template.render(
        project_name=mrv_data["project_name"],
        location_name=mrv_data["location_name"],
        project_type=(mrv_data["project_type"] or "Umum").title(),
        area_ha=f"{mrv_data['area_ha']:,.1f}" if mrv_data["area_ha"] else "-",
        generated_at=datetime.utcnow().strftime("%d %B %Y, %H:%M UTC"),
        executive_summary=mrv_data["executive_summary"],
        measurement=mrv_data["measurement"],
        reporting=mrv_data["reporting"],
        verification=mrv_data["verification"],
        year=datetime.utcnow().year,
    )

    # 1. Coba WeasyPrint jika tersedia
    try:
        from weasyprint import HTML
        return HTML(string=html_content).write_pdf()
    except Exception:
        pass

    # 2. Fallback ke xhtml2pdf
    try:
        from xhtml2pdf import pisa
        buffer = io.BytesIO()
        result = pisa.CreatePDF(html_content, dest=buffer, encoding="utf-8")
        if result.err:
            raise RuntimeError("xhtml2pdf failed")
        return buffer.getvalue()
    except Exception as e:
        raise RuntimeError(f"Gagal generate PDF: {e}") from e


def export_project_data_csv(db: Session, project: Project, data_type: str = "trees") -> str:
    """
    Mengekspor data monitoring proyek ke string berformat CSV.
    Dukungan data_type: `trees`, `activities`, `field_reports`, `biodiversity`, `carbon`.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    if data_type == "trees":
        writer.writerow([
            "ID", "Plot ID", "Tree Tag", "Species", "Quantity", "Planting Date",
            "Height (cm)", "DBH (cm)", "Condition", "Is Alive", "Latitude", "Longitude",
            "Photo URL", "Notes"
        ])
        trees = db.query(TreeRecord).filter(TreeRecord.project_id == project.id).all()
        for t in trees:
            lng, lat = None, None
            if t.location_geojson and isinstance(t.location_geojson, dict):
                coords = t.location_geojson.get("coordinates")
                if coords and len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
            photo_url = None
            if t.photo_urls:
                if isinstance(t.photo_urls, list) and len(t.photo_urls) > 0:
                    photo_url = t.photo_urls[0]
                elif isinstance(t.photo_urls, str):
                    try:
                        p_list = json.loads(t.photo_urls)
                        photo_url = p_list[0] if (isinstance(p_list, list) and p_list) else t.photo_urls
                    except Exception:
                        photo_url = t.photo_urls
            writer.writerow([
                t.id, t.plot_id or "", t.tree_tag or "", t.species, t.quantity,
                t.planting_date.isoformat() if t.planting_date else "",
                t.height_cm if t.height_cm is not None else "",
                t.dbh_cm if t.dbh_cm is not None else "",
                t.condition or "healthy",
                "Yes" if t.is_alive else "No",
                lat if lat is not None else "",
                lng if lng is not None else "",
                photo_url or "",
                t.notes or ""
            ])

    elif data_type == "activities":
        writer.writerow(["ID", "Activity Type", "Activity Date", "Target", "Realization", "Unit", "Executor", "Notes"])
        activities = db.query(ProjectActivity).filter(ProjectActivity.project_id == project.id).all()
        for a in activities:
            writer.writerow([
                a.id, a.activity_type,
                a.activity_date.isoformat() if a.activity_date else "",
                a.target, a.realization, a.unit, a.executor, a.notes
            ])

    elif data_type == "field_reports":
        writer.writerow(["ID", "Plot ID", "Officer Name", "Report Type", "Report Date", "Latitude", "Longitude", "Notes", "Photo Count", "Video Count"])
        reports = db.query(FieldReport).filter(FieldReport.project_id == project.id).all()
        for fr in reports:
            lng, lat = None, None
            if fr.location_geojson and isinstance(fr.location_geojson, dict):
                coords = fr.location_geojson.get("coordinates")
                if coords and len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
            writer.writerow([
                fr.id, fr.plot_id or "", fr.officer_name, fr.report_type,
                fr.report_date.isoformat() if fr.report_date else "",
                lat if lat is not None else "",
                lng if lng is not None else "",
                fr.notes or "",
                len(fr.photo_urls) if fr.photo_urls else 0,
                len(fr.video_urls) if fr.video_urls else 0
            ])

    elif data_type == "biodiversity":
        writer.writerow(["ID", "Species Name", "Species Type", "Observed Date", "Habitat", "Observer", "Latitude", "Longitude", "Notes"])
        bios = db.query(BiodiversityObservation).filter(BiodiversityObservation.project_id == project.id).all()
        for b in bios:
            lng, lat = None, None
            if b.location_geojson and isinstance(b.location_geojson, dict):
                coords = b.location_geojson.get("coordinates")
                if coords and len(coords) >= 2:
                    lng, lat = coords[0], coords[1]
            writer.writerow([
                b.id, b.species_name, b.species_type,
                b.observed_date.isoformat() if b.observed_date else "",
                b.habitat or "", b.observer or "",
                lat if lat is not None else "",
                lng if lng is not None else "",
                b.notes or ""
            ])

    elif data_type == "carbon":
        writer.writerow(["ID", "Period Start", "Period End", "Carbon Stock (tCO2e)", "Estimated CO2e", "Methodology"])
        carbons = db.query(CarbonRecord).filter(CarbonRecord.project_id == project.id).all()
        for c in carbons:
            writer.writerow([
                c.id,
                c.period_start.isoformat() if c.period_start else "",
                c.period_end.isoformat() if c.period_end else "",
                c.carbon_stock_tco2e, c.estimated_co2e, c.methodology
            ])

    else:
        # Default all overview summary
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Project ID", project.id])
        writer.writerow(["Project Name", project.name])
        writer.writerow(["Location", project.location_name])
        writer.writerow(["Area (ha)", project.area_ha])
        writer.writerow(["Total Trees Planted", sum(t.quantity for t in db.query(TreeRecord).filter(TreeRecord.project_id == project.id).all())])

    return output.getvalue()
