from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.core.activity import create_activity_log
from app.models.user import User
from app.schemas.rapid_fs import RapidFSInput, RapidFSResult
from app.schemas.user import RapidFsAccessRequestBody, UserResponse
from app.services.monitoring.gee_service import gee_service
from app.services.compro.rapid_fs_engine import calculate_rapid_fs
from app.services.compro.spatial_parser import parse_shapefile_zip

router = APIRouter(prefix="/rapid-fs", tags=["Rapid-FS Engine"])


@router.post("/calculate", response_model=RapidFSResult)
def calculate(input_data: RapidFSInput):
    """
    Menghitung Indicative Carbon Project Feasibility Score (ICPFS) 7-Stage
    berdasarkan luas area (ha), koordinat/poligon, tipe ekosistem, durasi, dan harga karbon.
    """
    spatial_data = None
    if input_data.polygon_geojson or (input_data.latitude and input_data.longitude):
        spatial_data = gee_service.extract_spatial_metrics(
            input_data.polygon_geojson, input_data.area_ha
        )

    result = calculate_rapid_fs(input_data, spatial_override=spatial_data)
    return result


@router.post("/upload-shapefile", response_model=RapidFSResult)
async def upload_shapefile(
    file: UploadFile = File(
        ...,
        description="File .zip berisi berkas ESRI Shapefile (.shp, .shx, .dbf, .prj)",
    ),
    location_name: str | None = Form("Lokasi Proyek Shapefile"),
    ecosystem_type: str = Form("hutan_tropis"),
    project_duration_years: int = Form(30),
    carbon_price_usd: float = Form(10.0),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Ekstraksi poligon dari berkas ESRI Shapefile (.zip),
    lalu secara otomatis menghitung skor ICPFS dan metrik ekosistem.
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Berkas harus dalam format .zip yang berisi komponen Shapefile (.shp, .shx, .dbf, .prj)",
        )

    content = await file.read()

    try:
        geojson_polygon, area_ha = parse_shapefile_zip(content)

        input_data = RapidFSInput(
            location_name=location_name,
            area_ha=area_ha,
            ecosystem_type=ecosystem_type,
            project_duration_years=project_duration_years,
            carbon_price_usd=carbon_price_usd,
            polygon_geojson=geojson_polygon,
        )

        spatial_metrics = gee_service.extract_spatial_metrics(geojson_polygon, area_ha)
        result = calculate_rapid_fs(input_data, spatial_override=spatial_metrics)

        is_unlocked = False
        if current_user:
            is_unlocked = current_user.role in ["admin", "super_admin"] or getattr(
                current_user, "has_rapidfs_access", False
            )
        result.is_unlocked = is_unlocked

        return result
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Gagal memproses file Shapefile: {e!s}"
        )


@router.post("/request-access", response_model=UserResponse)
def request_rapidfs_access_alias(
    body: Optional[RapidFsAccessRequestBody] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Alias endpoint bagi user untuk mengajukan permohonan akses Rapid-FS.
    """
    current_user.rapidfs_request_status = "pending"
    current_user.rapidfs_requested_at = datetime.utcnow()
    if body and body.project_name:
        current_user.rapidfs_request_project = body.project_name

    create_activity_log(
        db=db,
        user=current_user,
        action="REQUEST",
        module="RAPID_FS",
        target_id=current_user.id,
        target_name=current_user.full_name or current_user.email,
        description=f"Mengajukan permohonan akses Rapid-FS penuh{' untuk ' + body.project_name if body and body.project_name else ''}",
    )

    db.commit()
    db.refresh(current_user)
    return current_user
