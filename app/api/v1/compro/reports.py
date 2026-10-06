from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.assessment import Assessment
from app.models.user import User
from app.services.shared.pdf_generator import generate_pdf_report

router = APIRouter(prefix="/reports", tags=["PDF Reports"])


@router.get("/{assessment_id}/pdf")
def download_pdf(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mengunduh laporan PDF resmi Rapid-FS.
    Hanya dapat diakses oleh user yang telah di-unlock (has_rapidfs_access == True) atau Admin.
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment tidak ditemukan.")

    is_admin = current_user.role in ["admin", "super_admin"]
    if not is_admin and assessment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak."
        )

    is_unlocked = is_admin or getattr(current_user, "has_rapidfs_access", False)
    if not is_unlocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak. Fitur unduh laporan resmi (PDF) hanya tersedia untuk akun yang telah diverifikasi Satu Bumi. Silakan hubungi kami.",
        )

    assessment_data = {
        "location_name": assessment.location_name,
        "area_ha": assessment.area_ha,
        "ecosystem_type": assessment.ecosystem_type,
        "project_duration_years": assessment.project_duration_years,
        "carbon_price_usd": assessment.carbon_price_usd,
        "feasibility_score": assessment.feasibility_score,
        "feasibility_category": assessment.feasibility_category,
        "agb_ton": assessment.agb_ton,
        "carbon_stock_tc": assessment.carbon_stock_tc,
        "co2e_ton": assessment.co2e_ton,
        "annual_emission_reduction": assessment.acc_total_credits
        / max(1, assessment.project_duration_years),
        "acc_total_credits": assessment.acc_total_credits,
        "gross_revenue_usd": assessment.gross_revenue_usd,
        "total_cost_usd": assessment.total_cost_usd,
        "net_revenue_usd": assessment.net_revenue_usd,
        "recommendations": assessment.recommendations_json or [],
    }

    pdf_content = generate_pdf_report(assessment_data)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Satubumi_RapidFS_{assessment_id}.pdf"
        },
    )
