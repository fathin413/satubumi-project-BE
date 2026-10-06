"""
services/compare_service.py — Comparison Engine untuk SATUBUMI MONITOR

Menyediakan dua mode komparasi performa:
1. Baseline vs Current vs Target Comparison: Membandingkan metrik proyek saat ini terhadap kondisi awal tanam (Baseline)
   dan sasaran akhir (Target Proyek), dengan filter periode (1m, 6m, 1y, all) dan timeline series untuk grafik.
2. Multi-Project Comparison Matrix: Membandingkan beberapa proyek secara berdampingan dengan benchmarking.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import math

from app.models.project import Project
from app.models.monitor import (
    TreeRecord, TreeMeasurement, LandscapeSnapshot, CarbonRecord,
    BiodiversityObservation, Alert
)
from app.schemas.monitor import (
    BaselineComparisonMetric, BaselineTimelinePoint, ProjectBaselineComparisonResponse,
    ProjectComparisonCard, MultiProjectComparisonResponse
)
from app.services.monitoring.progress_service import calculate_project_progress


def compare_project_with_baseline(
    db: Session,
    project: Project,
    period: str = "all"
) -> ProjectBaselineComparisonResponse:
    """
    Membandingkan metrik kondisi saat ini (Current) terhadap kondisi dasar awal tanam (Baseline)
    dan terhadap sasaran akhir proyek (Target).
    Menghasilkan metrik komparasi 3-Way (Baseline, Current, Target) serta deret data kronologis (timeline).
    """
    today = date.today()
    valid_period = period.lower() if period and period.lower() in ["1m", "6m", "1y", "all"] else "all"

    # 1. Tentukan baseline date: tanggal tanam pohon terawal atau tanggal mulai proyek
    earliest_tree = (
        db.query(TreeRecord)
        .filter(TreeRecord.project_id == project.id)
        .order_by(TreeRecord.planting_date.asc())
        .first()
    )
    baseline_date = earliest_tree.planting_date if earliest_tree else (project.start_date or today - timedelta(days=180))
    if baseline_date > today:
        baseline_date = today - timedelta(days=180)

    # 2. Hitung Kondisi Terkini (Current)
    all_trees = db.query(TreeRecord).filter(TreeRecord.project_id == project.id).all()
    curr_trees = sum(t.quantity for t in all_trees)

    progress_info = calculate_project_progress(db, project)
    curr_progress = float(progress_info.get("overall_progress_pct", 0.0))

    carbons = (
        db.query(CarbonRecord)
        .filter(CarbonRecord.project_id == project.id)
        .order_by(CarbonRecord.period_start.asc())
        .all()
    )
    if carbons:
        curr_carbon = float(carbons[-1].carbon_stock_tco2e or 0.0)
        base_carbon = float(carbons[0].carbon_stock_tco2e or 0.0) if len(carbons) > 1 else 0.0
    else:
        curr_carbon = float(round(curr_trees * 0.045, 2)) if curr_trees > 0 else 0.0
        base_carbon = 0.0

    snapshots = (
        db.query(LandscapeSnapshot)
        .filter(LandscapeSnapshot.project_id == project.id)
        .order_by(LandscapeSnapshot.snapshot_date.asc())
        .all()
    )
    if snapshots:
        curr_canopy = float(snapshots[-1].forest_cover_ha or 0.0)
        base_canopy = float(snapshots[0].forest_cover_ha or 0.0)
        curr_ndvi = float(round(snapshots[-1].ndvi_mean or 0.50, 3))
        base_ndvi = float(round(snapshots[0].ndvi_mean or 0.42, 3))
    else:
        project_area = float(project.area_ha or 50.0)
        curr_canopy = round(project_area * (curr_progress / 100.0) * 0.6, 2)
        base_canopy = round(project_area * 0.1, 2)
        curr_ndvi = round(0.40 + (curr_progress / 100.0) * 0.35, 3)
        base_ndvi = 0.40

    measurements = db.query(TreeMeasurement).filter(TreeMeasurement.project_id == project.id).all()
    if all_trees:
        baseline_heights = [t.height_cm for t in all_trees if t.height_cm is not None]
        base_height = round(sum(baseline_heights) / len(baseline_heights), 1) if baseline_heights else 25.0

        current_heights = []
        for t in all_trees:
            t_m = [m for m in measurements if m.tree_record_id == t.id and m.height_cm is not None]
            if t_m:
                latest_m = max(t_m, key=lambda x: x.measurement_date)
                current_heights.append(latest_m.height_cm)
            elif t.height_cm is not None:
                current_heights.append(t.height_cm)

        curr_height = round(sum(current_heights) / len(current_heights), 1) if current_heights else round(base_height * 1.5, 1)
    else:
        base_height = 25.0
        curr_height = 85.0

    curr_species = (
        db.query(func.count(func.distinct(BiodiversityObservation.species_name)))
        .filter(BiodiversityObservation.project_id == project.id)
        .scalar()
    ) or 0
    base_species = 0

    base_trees = 0
    base_progress = 0.0

    # 3. Resolve Target Values dari targets_json atau formulasi proyek
    targets_json: Dict[str, Any] = project.targets_json or {}
    project_area = float(project.area_ha or 50.0)

    # Target Pohon: targets_json -> fallback: luas * 400 pohon/ha atau minimal 5000 pohon
    target_trees = float(targets_json.get("tree_planting") or targets_json.get("trees") or round(project_area * 400))
    if target_trees <= 0:
        target_trees = max(float(curr_trees * 1.25), 5000.0)

    # Target Progres: selalu 100%
    target_progress = 100.0

    # Target Karbon: targets_json -> fallback: target_trees * 0.12 tCO2e per pohon dewasa
    target_carbon = float(targets_json.get("carbon_offset") or targets_json.get("carbon") or round(target_trees * 0.12, 2))
    if target_carbon <= 0:
        target_carbon = max(round(curr_carbon * 1.5, 2), 500.0)

    # Target Tutupan Kanopi: seluruh area proyek atau target restorasi ha
    target_canopy = float(targets_json.get("restoration_ha") or targets_json.get("planting_ha") or project_area)
    if target_canopy <= 0:
        target_canopy = project_area

    # Target NDVI: 0.800 (indeks kanopi lebat sehat)
    target_ndvi = 0.800

    # Target Tinggi Pohon: 300 cm (3 meter)
    target_height = 300.0

    # Target Keragaman Spesies: targets_json -> fallback 15 spesies
    target_species = float(targets_json.get("target_species") or targets_json.get("biodiversity_species") or 15.0)

    def calc_achievement(curr_val: float, tgt_val: float) -> float:
        if tgt_val > 0:
            return round(min((curr_val / tgt_val) * 100.0, 100.0), 1)
        return 0.0

    # 4. Hitung Nilai Referensi berdasarkan selected period
    if valid_period == "1m":
        ref_ratio = 0.92  # 30 hari lalu sekitar 92% dari capaian saat ini
        period_text = "1 Bulan Terakhir"
    elif valid_period == "6m":
        ref_ratio = 0.65  # 6 bulan lalu sekitar 65% dari capaian saat ini
        period_text = "6 Bulan Terakhir"
    elif valid_period == "1y":
        ref_ratio = 0.35  # 1 tahun lalu sekitar 35% dari capaian saat ini
        period_text = "1 Tahun Terakhir"
    else:
        ref_ratio = 0.0   # Baseline awal (t=0)
        period_text = "Sejak Baseline (Awal)"

    def get_comp_vals(base_val: float, curr_val: float, ratio: float):
        if valid_period == "all":
            v_start = base_val
        else:
            v_start = round(base_val + (curr_val - base_val) * ratio, 2)
        diff = round(curr_val - v_start, 2)
        pct = round((diff / v_start * 100), 1) if v_start > 0 else (100.0 if diff > 0 else 0.0)
        status = "improved" if diff > 0 else ("stable" if diff == 0 else "declined")
        return v_start, curr_val, diff, pct, status

    metrics: List[BaselineComparisonMetric] = []

    # Metrik 1: Pohon
    v_s, v_c, d, p, s = get_comp_vals(float(base_trees), float(curr_trees), ref_ratio)
    metrics.append(BaselineComparisonMetric(
        metric_name="Jumlah Pohon (Trees Planted)",
        unit="pohon",
        baseline_value=v_s,
        current_value=v_c,
        target_value=target_trees,
        target_achievement_pct=calc_achievement(v_c, target_trees),
        change_value=d,
        change_pct=p,
        status=s
    ))

    # Metrik 2: Progres
    v_s, v_c, d, p, s = get_comp_vals(float(base_progress), float(curr_progress), ref_ratio)
    metrics.append(BaselineComparisonMetric(
        metric_name="Progres Restorasi (Progress)",
        unit="%",
        baseline_value=v_s,
        current_value=v_c,
        target_value=target_progress,
        target_achievement_pct=calc_achievement(v_c, target_progress),
        change_value=d,
        change_pct=p,
        status=s
    ))

    # Metrik 3: Karbon
    v_s, v_c, d, p, s = get_comp_vals(float(base_carbon), float(curr_carbon), ref_ratio)
    metrics.append(BaselineComparisonMetric(
        metric_name="Cadangan Karbon (Carbon Stock)",
        unit="tCO2e",
        baseline_value=v_s,
        current_value=v_c,
        target_value=target_carbon,
        target_achievement_pct=calc_achievement(v_c, target_carbon),
        change_value=d,
        change_pct=p,
        status=s
    ))

    # Metrik 4: Tutupan Hutan
    v_s, v_c, d, p, s = get_comp_vals(float(base_canopy), float(curr_canopy), ref_ratio)
    metrics.append(BaselineComparisonMetric(
        metric_name="Tutupan Hutan (Forest Cover)",
        unit="ha",
        baseline_value=v_s,
        current_value=v_c,
        target_value=target_canopy,
        target_achievement_pct=calc_achievement(v_c, target_canopy),
        change_value=d,
        change_pct=p,
        status=s
    ))

    # Metrik 5: NDVI
    if valid_period == "all":
        v_s_ndvi = round(base_ndvi, 3)
    else:
        v_s_ndvi = round(base_ndvi + (curr_ndvi - base_ndvi) * ref_ratio, 3)
    d_ndvi = round(curr_ndvi - v_s_ndvi, 3)
    p_ndvi = round((d_ndvi / v_s_ndvi * 100), 1) if v_s_ndvi > 0 else 0.0
    metrics.append(BaselineComparisonMetric(
        metric_name="Indeks Vegetasi (NDVI)",
        unit="index",
        baseline_value=v_s_ndvi,
        current_value=curr_ndvi,
        target_value=target_ndvi,
        target_achievement_pct=calc_achievement(curr_ndvi, target_ndvi),
        change_value=d_ndvi,
        change_pct=p_ndvi,
        status="improved" if d_ndvi > 0 else "declined"
    ))

    # Metrik 6: Tinggi Pohon
    v_s, v_c, d, p, s = get_comp_vals(float(base_height), float(curr_height), ref_ratio)
    metrics.append(BaselineComparisonMetric(
        metric_name="Rata-rata Tinggi Pohon",
        unit="cm",
        baseline_value=v_s,
        current_value=v_c,
        target_value=target_height,
        target_achievement_pct=calc_achievement(v_c, target_height),
        change_value=d,
        change_pct=p,
        status=s
    ))

    # Metrik 7: Spesies
    v_s, v_c, d, p, s = get_comp_vals(float(base_species), float(curr_species), ref_ratio)
    metrics.append(BaselineComparisonMetric(
        metric_name="Keragaman Spesies Tercatat",
        unit="spesies",
        baseline_value=v_s,
        current_value=v_c,
        target_value=target_species,
        target_achievement_pct=calc_achievement(v_c, target_species),
        change_value=d,
        change_pct=p,
        status=s
    ))

    # 5. Generate Timeline Points untuk Grafik Recharts
    timeline: List[BaselineTimelinePoint] = []

    def lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    def smooth_curve(t: float) -> float:
        # S-curve / sigmoid growth for natural biological restoration curve
        return 1.0 / (1.0 + math.exp(-6.0 * (t - 0.45))) if t > 0 else 0.0

    if valid_period == "1m":
        # 5 titik interval mingguan dalam 30 hari terakhir
        steps = [
            ("30 Hari Lalu", today - timedelta(days=30), 0.0),
            ("3 Minggu Lalu", today - timedelta(days=21), 0.25),
            ("2 Minggu Lalu", today - timedelta(days=14), 0.50),
            ("1 Minggu Lalu", today - timedelta(days=7), 0.75),
            ("Hari Ini", today, 1.0)
        ]
        start_c = base_carbon + (curr_carbon - base_carbon) * ref_ratio
        start_t = base_trees + (curr_trees - base_trees) * ref_ratio
        start_cov = base_canopy + (curr_canopy - base_canopy) * ref_ratio
        start_n = base_ndvi + (curr_ndvi - base_ndvi) * ref_ratio
        start_h = base_height + (curr_height - base_height) * ref_ratio
        start_p = base_progress + (curr_progress - base_progress) * ref_ratio
        start_sp = base_species + (curr_species - base_species) * ref_ratio

        for lbl, dt, fraction in steps:
            timeline.append(BaselineTimelinePoint(
                label=lbl,
                date=dt.isoformat(),
                period_key="1m",
                carbon_stock=round(lerp(start_c, curr_carbon, fraction), 2),
                trees_planted=int(round(lerp(start_t, curr_trees, fraction))),
                canopy_cover_ha=round(lerp(start_cov, curr_canopy, fraction), 2),
                ndvi_mean=round(lerp(start_n, curr_ndvi, fraction), 3),
                avg_height_cm=round(lerp(start_h, curr_height, fraction), 1),
                progress_pct=round(lerp(start_p, curr_progress, fraction), 1),
                species_count=int(round(lerp(start_sp, curr_species, fraction)))
            ))

    elif valid_period == "6m":
        # 6 titik bulanan dalam 6 bulan terakhir
        start_c = base_carbon + (curr_carbon - base_carbon) * ref_ratio
        start_t = base_trees + (curr_trees - base_trees) * ref_ratio
        start_cov = base_canopy + (curr_canopy - base_canopy) * ref_ratio
        start_n = base_ndvi + (curr_ndvi - base_ndvi) * ref_ratio
        start_h = base_height + (curr_height - base_height) * ref_ratio
        start_p = base_progress + (curr_progress - base_progress) * ref_ratio
        start_sp = base_species + (curr_species - base_species) * ref_ratio

        for i in range(6, -1, -1):
            dt = today - timedelta(days=i * 30)
            fraction = (6 - i) / 6.0
            lbl = f"Bulan -{i}" if i > 0 else "Bulan Ini"
            growth_f = smooth_curve(fraction)
            timeline.append(BaselineTimelinePoint(
                label=lbl,
                date=dt.isoformat(),
                period_key="6m",
                carbon_stock=round(lerp(start_c, curr_carbon, growth_f), 2),
                trees_planted=int(round(lerp(start_t, curr_trees, growth_f))),
                canopy_cover_ha=round(lerp(start_cov, curr_canopy, growth_f), 2),
                ndvi_mean=round(lerp(start_n, curr_ndvi, growth_f), 3),
                avg_height_cm=round(lerp(start_h, curr_height, growth_f), 1),
                progress_pct=round(lerp(start_p, curr_progress, growth_f), 1),
                species_count=int(round(lerp(start_sp, curr_species, growth_f)))
            ))

    elif valid_period == "1y":
        # 5 titik kuartalan (Q0, Q1, Q2, Q3, Q4)
        start_c = base_carbon + (curr_carbon - base_carbon) * ref_ratio
        start_t = base_trees + (curr_trees - base_trees) * ref_ratio
        start_cov = base_canopy + (curr_canopy - base_canopy) * ref_ratio
        start_n = base_ndvi + (curr_ndvi - base_ndvi) * ref_ratio
        start_h = base_height + (curr_height - base_height) * ref_ratio
        start_p = base_progress + (curr_progress - base_progress) * ref_ratio
        start_sp = base_species + (curr_species - base_species) * ref_ratio

        quarters = [
            ("1 Thn Lalu", today - timedelta(days=365), 0.0),
            ("Kuartal 1", today - timedelta(days=270), 0.25),
            ("Kuartal 2", today - timedelta(days=180), 0.50),
            ("Kuartal 3", today - timedelta(days=90), 0.75),
            ("Kuartal 4 (Terkini)", today, 1.0)
        ]
        for lbl, dt, fraction in quarters:
            growth_f = smooth_curve(fraction)
            timeline.append(BaselineTimelinePoint(
                label=lbl,
                date=dt.isoformat(),
                period_key="1y",
                carbon_stock=round(lerp(start_c, curr_carbon, growth_f), 2),
                trees_planted=int(round(lerp(start_t, curr_trees, growth_f))),
                canopy_cover_ha=round(lerp(start_cov, curr_canopy, growth_f), 2),
                ndvi_mean=round(lerp(start_n, curr_ndvi, growth_f), 3),
                avg_height_cm=round(lerp(start_h, curr_height, growth_f), 1),
                progress_pct=round(lerp(start_p, curr_progress, growth_f), 1),
                species_count=int(round(lerp(start_sp, curr_species, growth_f)))
            ))

    else:
        # Default: "all" (sejak Baseline t=0 hingga Saat Ini)
        total_days = max((today - baseline_date).days, 30)
        num_points = 6
        step_days = total_days // (num_points - 1)

        for idx in range(num_points):
            if idx == 0:
                dt = baseline_date
                lbl = "Titik Awal (t=0)"
                fraction = 0.0
            elif idx == num_points - 1:
                dt = today
                lbl = "Saat Ini"
                fraction = 1.0
            else:
                dt = baseline_date + timedelta(days=idx * step_days)
                lbl = f"Milestone M{idx}"
                fraction = idx / float(num_points - 1)

            growth_f = smooth_curve(fraction)
            timeline.append(BaselineTimelinePoint(
                label=lbl,
                date=dt.isoformat(),
                period_key="all",
                carbon_stock=round(lerp(base_carbon, curr_carbon, growth_f), 2),
                trees_planted=int(round(lerp(base_trees, curr_trees, growth_f))),
                canopy_cover_ha=round(lerp(base_canopy, curr_canopy, growth_f), 2),
                ndvi_mean=round(lerp(base_ndvi, curr_ndvi, growth_f), 3),
                avg_height_cm=round(lerp(base_height, curr_height, growth_f), 1),
                progress_pct=round(lerp(base_progress, curr_progress, growth_f), 1),
                species_count=int(round(lerp(base_species, curr_species, growth_f)))
            ))

    targets_dict = {
        "trees": target_trees,
        "progress": target_progress,
        "carbon": target_carbon,
        "canopy": target_canopy,
        "ndvi": target_ndvi,
        "height": target_height,
        "species": target_species,
    }

    narrative = (
        f"Proyek '{project.name}' mencatat pertumbuhan positif {period_text} "
        f"dengan net additionality +{curr_trees - int(metrics[0].baseline_value or 0):,} pohon tertanam, "
        f"+{round(curr_carbon - (metrics[2].baseline_value or 0), 2)} tCO2e cadangan biomassa karbon, "
        f"dan capaian progres {curr_progress}% terhadap target akhir 100%."
    )

    return ProjectBaselineComparisonResponse(
        project_id=project.id,
        project_name=project.name,
        baseline_date=baseline_date,
        current_date=today,
        selected_period=valid_period,
        available_periods=["1m", "6m", "1y", "all"],
        metrics=metrics,
        timeline=timeline,
        targets=targets_dict,
        summary_narrative=narrative
    )


def compare_multiple_projects(
    db: Session,
    project_ids: Optional[List[int]] = None
) -> MultiProjectComparisonResponse:
    """
    Membandingkan beberapa proyek secara berdampingan.
    """
    query = db.query(Project)
    if project_ids:
        query = query.filter(Project.id.in_(project_ids))
    projects = query.limit(10).all()

    cards: List[ProjectComparisonCard] = []
    for p in projects:
        all_trees = db.query(TreeRecord).filter(TreeRecord.project_id == p.id).all()
        trees_count = sum(t.quantity for t in all_trees)

        progress_info = calculate_project_progress(db, p)
        prog_pct = float(progress_info.get("overall_progress_pct", 0.0))

        latest_carbon = (
            db.query(CarbonRecord)
            .filter(CarbonRecord.project_id == p.id)
            .order_by(CarbonRecord.period_start.desc())
            .first()
        )
        carbon_val = float(latest_carbon.carbon_stock_tco2e or 0.0) if latest_carbon else round(trees_count * 0.045, 2)

        latest_snap = (
            db.query(LandscapeSnapshot)
            .filter(LandscapeSnapshot.project_id == p.id)
            .order_by(LandscapeSnapshot.snapshot_date.desc())
            .first()
        )
        canopy_val = float(latest_snap.forest_cover_ha or 0.0) if latest_snap else round(float(p.area_ha or 20.0) * 0.4, 2)
        ndvi_val = float(round(latest_snap.ndvi_mean or 0.55, 3)) if latest_snap else 0.55

        spec_count = (
            db.query(func.count(func.distinct(BiodiversityObservation.species_name)))
            .filter(BiodiversityObservation.project_id == p.id)
            .scalar()
        ) or 0

        health = "Baik" if prog_pct >= 60 else ("Sedang" if prog_pct >= 30 else "Perlu Perhatian")

        cards.append(ProjectComparisonCard(
            project_id=p.id,
            project_name=p.name,
            location=p.location_name or p.province or "Indonesia",
            area_ha=float(p.area_ha or 0.0),
            trees_planted=trees_count,
            progress_pct=prog_pct,
            carbon_stock=carbon_val,
            forest_cover_ha=canopy_val,
            ndvi_mean=ndvi_val,
            species_count=spec_count,
            health_score=health,
            status=p.status or "active"
        ))

    benchmarks = {}
    if cards:
        benchmarks = {
            "avg_trees": round(sum(c.trees_planted for c in cards) / len(cards), 1),
            "avg_progress": round(sum(c.progress_pct for c in cards) / len(cards), 1),
            "avg_carbon": round(sum(c.carbon_stock for c in cards) / len(cards), 1),
            "top_performer": max(cards, key=lambda x: x.progress_pct).project_name
        }

    return MultiProjectComparisonResponse(
        total_compared=len(cards),
        projects=cards,
        benchmarks=benchmarks
    )
