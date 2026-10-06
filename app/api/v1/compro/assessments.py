
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user, get_current_user_optional
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.schemas.assessment import AssessmentResponse, AssessmentSubmitRequest

router = APIRouter(prefix="/assessments", tags=["Assessment History"])


def mask_assessment_if_locked(assessment: Assessment, is_unlocked: bool) -> AssessmentResponse:
    res = AssessmentResponse.model_validate(assessment)
    res.is_unlocked = is_unlocked
    if not is_unlocked:
        # Metrik dasar (agb_ton, carbon_stock_tc, co2e_ton) tetap tampil sebagai preview dasar
        res.acc_total_credits = None
        res.gross_revenue_usd = None
        res.total_cost_usd = None
        res.net_revenue_usd = None
        res.cost_breakdown_json = None
        res.recommendations_json = None
    return res


@router.post("", status_code=status.HTTP_201_CREATED)
def save_assessment(
    body: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Menyimpan hasil kalkulasi Rapid-FS ke database histori assessment.

    - **submitter_name**: Nama lengkap user (opsional jika sudah login)
    - **submitter_phone**: Nomor telepon user
    - **submitter_email**: Email user
    - **rapid_fs_result**: Hasil kalkulasi dari endpoint Rapid-FS

    Jika user sudah login, `user_id` otomatis diisi. Data kontak tetap bisa dioverride manual.
    """
    result = body.rapid_fs_result

    # Jika user login & tidak mengisi submitter_name/email, fallback ke profil user
    submitter_name = body.submitter_name
    submitter_email = body.submitter_email
    if current_user:
        if not submitter_name and current_user.full_name:
            submitter_name = current_user.full_name
        if not submitter_email and current_user.email:
            submitter_email = current_user.email

    new_assessment = Assessment(
        user_id=current_user.id if current_user else None,
        submitter_name=submitter_name,
        submitter_phone=body.submitter_phone,
        submitter_email=submitter_email,
        location_name=result.location_name,
        area_ha=result.area_ha,
        ecosystem_type=result.ecosystem_type,
        project_duration_years=result.project_duration_years,
        carbon_price_usd=result.carbon_price_usd,
        agb_ton=result.agb_ton,
        carbon_stock_tc=result.carbon_stock_tc,
        co2e_ton=result.co2e_ton,
        acc_total_credits=result.acc_total_credits,
        gross_revenue_usd=result.gross_revenue_usd,
        total_cost_usd=result.cost_breakdown.total_cost_usd if result.cost_breakdown else None,
        net_revenue_usd=result.net_revenue_usd,
        feasibility_score=result.feasibility_score,
        feasibility_category=result.feasibility_category,
        component_scores_json=result.component_scores.model_dump() if result.component_scores else None,
        cost_breakdown_json=result.cost_breakdown.model_dump() if result.cost_breakdown else None,
        geometry_geojson=result.geometry,
        recommendations_json=result.recommendations,
    )
    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)
    return {
        "id": new_assessment.id,
        "message": "Hasil assessment berhasil disimpan.",
        "submitter_name": new_assessment.submitter_name,
        "submitter_email": new_assessment.submitter_email,
    }


@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Mendapatkan daftar histori assessment.

    - **Admin**: Melihat semua assessment dari semua user beserta data kontak submitter (selalu unlocked).
    - **User biasa**: Hanya melihat assessment miliknya sendiri. Jika belum di-unlock oleh admin, metrik sensitif di-mask.
    """
    is_admin = current_user.role in ["admin", "super_admin"]
    is_unlocked = is_admin or getattr(current_user, "has_rapidfs_access", False)

    if is_admin:
        assessments = db.query(Assessment).order_by(Assessment.created_at.desc()).all()
    else:
        assessments = (
            db.query(Assessment)
            .filter(Assessment.user_id == current_user.id)
            .order_by(Assessment.created_at.desc())
            .all()
        )

    return [mask_assessment_if_locked(item, is_unlocked) for item in assessments]


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mendapatkan detail satu assessment berdasarkan ID.
    Admin bisa akses semua; user biasa hanya miliknya.
    Jika user belum memiliki akses Rapid-FS eksklusif, metrik sensitif di-mask (is_unlocked=False).
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan.")

    is_admin = current_user.role in ["admin", "super_admin"]
    if not is_admin and assessment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Akses ditolak.")

    is_unlocked = is_admin or getattr(current_user, "has_rapidfs_access", False)
    return mask_assessment_if_locked(assessment, is_unlocked)


@router.delete("/{assessment_id}", status_code=status.HTTP_200_OK)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Menghapus assessment berdasarkan ID.
    Admin bisa hapus semua; user biasa hanya miliknya.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan.")
    if (
        current_user.role not in ["admin", "super_admin"]
        and assessment.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Akses ditolak.")

    db.delete(assessment)
    db.commit()
    return {"message": "Assessment berhasil dihapus."}
