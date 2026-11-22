from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.project import Project
from app.models.monitor import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.monitor import (
    ProjectMemberCreate, ProjectMemberResponse,
    ProgressResponse, TreeSummaryProgress, ActivityTypeSummary, TargetProgress,
    MultiProjectComparisonResponse,
)
from app.api.v1.auth import get_current_user
from app.core.dependencies import require_admin, get_project_or_404
from app.core.security import create_access_token
from app.services.monitoring.progress_service import calculate_project_progress
from app.services.monitoring.compare_service import compare_multiple_projects

router = APIRouter(prefix="/projects", tags=["Monitor — Projects"])


# ── CRUD Proyek ───────────────────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Membuat proyek monitoring baru.

    - Hanya **admin** dan **super_admin** yang dapat membuat proyek.
    - `boundary_geojson`: Batas wilayah proyek dalam format GeoJSON (opsional).
    - `targets_json`: Target proyek, contoh `{"restoration_ha": 1000, "tree_planting": 100000}`.
    - `project_type`: Tipe ekosistem: `reforestation`, `mangrove`, `agroforestry`, `peatland`, `blue_carbon`.
    """
    require_admin(current_user)

    project = Project(
        name=body.name,
        description=body.description,
        location_name=body.location_name,
        area_ha=body.area_ha,
        status=body.status or "active",
        project_type=body.project_type,
        start_date=body.start_date,
        end_date=body.end_date,
        country=body.country or "Indonesia",
        province=body.province,
        district=body.district,
        boundary_geojson=body.boundary_geojson,
        targets_json=body.targets_json,
        created_by=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Nomor halaman (mulai dari 1)"),
    limit: int = Query(20, ge=1, le=100, description="Jumlah data per halaman (max 100)"),
    status: Optional[str] = Query(None, description="Filter by status: active, completed, suspended"),
    project_type: Optional[str] = Query(None, description="Filter by type: reforestation, mangrove, dll"),
    search: Optional[str] = Query(None, description="Cari berdasarkan nama atau lokasi"),
):
    """
    Mendapatkan daftar proyek monitoring dengan pagination dan filter.

    - **admin** & **super_admin**: Melihat semua proyek.
    - **client** & **field_officer**: HANYA melihat proyek yang di-assign ke akunnya (ada di project_members).
    - Mendukung filter by `status`, `project_type`, dan pencarian nama/lokasi.
    - Default: 20 proyek per halaman, urut dari terbaru.
    """
    query = db.query(Project)

    # Filter akses: role non-admin hanya melihat proyek yang di-assign
    if current_user.role not in {"admin", "super_admin"}:
        query = query.join(ProjectMember, Project.id == ProjectMember.project_id).filter(
            ProjectMember.user_id == current_user.id
        )

    if status:
        query = query.filter(Project.status == status)
    if project_type:
        query = query.filter(Project.project_type == project_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Project.name.ilike(search_term) | Project.location_name.ilike(search_term)
        )

    offset = (page - 1) * limit
    return query.order_by(Project.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/compare", response_model=MultiProjectComparisonResponse)
def compare_projects(
    project_ids: str = Query(..., description="Daftar ID proyek dipisahkan koma, contoh: '1,2,3'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Komparasi performa lintas banyak proyek (Multi-Project Comparison Matrix).

    Menganalisis dan membandingkan secara berdampingan:
    - Luas area & target vs realisasi (%)
    - Jumlah pohon ditanam & survival rate (%)
    - Estimasi cadangan karbon & keragaman biodiversitas
    - Jumlah alert aktif serta benchmark performa tertinggi

    User non-admin hanya dapat mengomparasi proyek yang menjadi hak aksesnya.
    """
    try:
        parsed_ids = [int(x.strip()) for x in project_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Format project_ids tidak valid. Gunakan format angka dipisah koma (contoh: '1,2,3').")

    if not parsed_ids:
        raise HTTPException(status_code=400, detail="Minimal sertakan satu ID proyek untuk dikomparasi.")

    # Filter hak akses: non-admin hanya boleh compare project yang di-assign ke dirinya
    if current_user.role not in {"admin", "super_admin"}:
        member_project_ids = {
            row[0]
            for row in db.query(ProjectMember.project_id)
            .filter(
                ProjectMember.user_id == current_user.id,
                ProjectMember.project_id.in_(parsed_ids)
            )
            .all()
        }
        if not member_project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak. Anda tidak memiliki akses ke proyek yang dipilih."
            )
        parsed_ids = [pid for pid in parsed_ids if pid in member_project_ids]

    return compare_multiple_projects(db, parsed_ids)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan detail satu proyek berdasarkan ID (hanya anggota proyek / admin)."""
    return get_project_or_404(project_id, db, current_user)



@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mengupdate data proyek.

    - Hanya **admin** dan **super_admin** yang dapat mengupdate proyek.
    - Semua field bersifat opsional — hanya field yang dikirim yang diupdate.
    - Field baru: `project_type`, `start_date`, `end_date`, `country`, `province`, `district`.
    """
    require_admin(current_user)
    project = get_project_or_404(project_id, db, current_user)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghapus proyek beserta seluruh data monitornya (cascade).

    - Hanya **admin** dan **super_admin** yang dapat menghapus proyek.
    """
    require_admin(current_user)
    project = get_project_or_404(project_id, db, current_user)

    db.delete(project)
    db.commit()
    return {"message": f"Proyek '{project.name}' berhasil dihapus."}


# ── Progress & Target vs Actual ───────────────────────────────────────────────

@router.get("/{project_id}/progress", response_model=ProgressResponse)
def get_project_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Menghitung progress Target vs Actual untuk sebuah proyek.

    Membaca `targets_json` proyek dan membandingkan dengan data aktual:
    - `tree_records` → untuk target `tree_planting`
    - `project_activities` → untuk target `restoration_ha`, `planting_ha`, dll.

    **Contoh targets_json**:
    ```json
    {
      "tree_planting": 100000,
      "restoration_ha": 1000,
      "planting_ha": 500
    }
    ```
    """
    project = get_project_or_404(project_id, db, current_user)
    raw = calculate_project_progress(db, project)

    return ProgressResponse(
        project_id=raw["project_id"],
        project_name=raw["project_name"],
        targets={k: TargetProgress(**v) for k, v in raw["targets"].items()},
        tree_summary=TreeSummaryProgress(**raw["tree_summary"]),
        activities_by_type={k: ActivityTypeSummary(**v) for k, v in raw["activities_by_type"].items()},
        overall_progress_pct=raw["overall_progress_pct"],
    )


# ── Project Members ───────────────────────────────────────────────────────────

@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    body: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign user ke proyek dengan role tertentu.

    - Hanya **admin** dan **super_admin** yang dapat assign member.
    - Role tersedia: `project_manager`, `field_officer`, `viewer`.
    - Satu user hanya bisa punya satu role per proyek (unique constraint).
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    target_user = db.query(User).filter(User.id == body.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User dengan ID {body.user_id} tidak ditemukan.")

    allowed_roles = {"project_manager", "field_officer", "viewer"}
    if body.role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Role tidak valid. Pilih dari: {', '.join(sorted(allowed_roles))}"
        )

    member = ProjectMember(
        project_id=project_id,
        user_id=body.user_id,
        role=body.role,
        assigned_at=datetime.utcnow(),
        assigned_by=current_user.id,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="User ini sudah menjadi anggota proyek. Hapus dulu sebelum assign ulang."
        )
    db.refresh(member)
    return member


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mendapatkan daftar semua anggota yang di-assign ke proyek ini."""
    get_project_or_404(project_id, db, current_user)
    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Hapus user dari keanggotaan proyek.

    - Hanya **admin** dan **super_admin** yang dapat menghapus member.
    """
    require_admin(current_user)
    get_project_or_404(project_id, db, current_user)

    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="User bukan anggota proyek ini.")

    db.delete(member)
    db.commit()
    return {"message": f"User {user_id} berhasil dihapus dari proyek {project_id}."}


# ── Akses Khusus Lapangan / Surveyor (Field Survey Link & PIN) ──────────────

class FieldAuthRequest(BaseModel):
    pin: str
    surveyor_name: str


@router.get("/{project_id}/public-info")
def get_project_public_info(project_id: int, db: Session = Depends(get_db)):
    """
    Informasi ringkas publik proyek untuk halaman survei lapangan.
    Dapat diakses tanpa login untuk memuat nama proyek & lokasi.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")

    targets = project.targets_json or {}
    has_custom_pin = bool(targets.get("field_pin"))

    return {
        "id": project.id,
        "name": project.name,
        "location_name": project.location_name,
        "project_type": project.project_type,
        "description": project.description,
        "status": project.status,
        "has_custom_pin": has_custom_pin,
    }


@router.post("/{project_id}/field-auth")
def authenticate_field_access(
    project_id: int,
    body: FieldAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Verifikasi PIN proyek untuk surveyor lapangan tanpa akun login pribadi.
    Jika PIN valid, menerbitkan token sesi akses lapangan (berlaku 7 hari).
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyek tidak ditemukan.")

    # Ambil PIN yang dikonfigurasi di targets_json, default '1234'
    targets = project.targets_json or {}
    expected_pin = str(targets.get("field_pin", "1234")).strip()

    if body.pin.strip() != expected_pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="PIN Akses Proyek tidak cocok. Silakan tanyakan PIN yang benar kepada admin/pengelola proyek."
        )

    # Ambil user penanggung jawab (creator proyek) atau user admin untuk context session
    user = None
    if project.created_by:
        user = db.query(User).filter(User.id == project.created_by).first()
    if not user:
        user = db.query(User).filter(User.role.in_(["admin", "super_admin", "field_officer"])).first()
    if not user:
        user = db.query(User).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sistem belum memiliki user penanggung jawab aktif."
        )

    # Token sesi lapangan berlaku 7 hari agar nyaman digunakan surveyor selama di lokasi
    token = create_access_token(subject=user.email, expires_delta=timedelta(days=7))

    return {
        "access_token": token,
        "token_type": "bearer",
        "project_id": project.id,
        "project_name": project.name,
        "location_name": project.location_name,
        "surveyor_name": body.surveyor_name.strip(),
    }

