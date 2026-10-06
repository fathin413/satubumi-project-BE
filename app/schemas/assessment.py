from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.rapid_fs import RapidFSResult


class SubmitterInfo(BaseModel):
    """Data kontak user yang menggunakan fitur Rapid Score."""

    submitter_name: str | None = Field(
        None, max_length=255, description="Nama lengkap submitter"
    )
    submitter_phone: str | None = Field(
        None, max_length=50, description="Nomor telepon submitter"
    )
    submitter_email: str | None = Field(
        None, max_length=255, description="Email submitter"
    )


class AssessmentSubmitRequest(SubmitterInfo):
    """
    Request body untuk POST /assessments.
    Gabungan data kontak submitter + seluruh hasil kalkulasi Rapid-FS.
    """

    # Referensi hasil kalkulasi dari endpoint /rapid-fs/calculate
    rapid_fs_result: RapidFSResult


class AssessmentResponse(BaseModel):
    """Response schema untuk GET /assessments (list & detail)."""

    id: int
    user_id: int | None = None
    is_unlocked: bool = True

    # Data kontak submitter
    submitter_name: str | None = None
    submitter_phone: str | None = None
    submitter_email: str | None = None

    # Input proyek
    location_name: str
    area_ha: float
    ecosystem_type: str
    project_duration_years: int
    carbon_price_usd: float

    # Hasil karbon & finansial
    agb_ton: float | None = None
    carbon_stock_tc: float | None = None
    co2e_ton: float | None = None
    acc_total_credits: float | None = None
    gross_revenue_usd: float | None = None
    total_cost_usd: float | None = None
    net_revenue_usd: float | None = None

    # Skor kelayakan
    feasibility_score: float
    feasibility_category: str

    # Detail JSON
    component_scores_json: dict[str, Any] | None = None
    cost_breakdown_json: dict[str, Any] | None = None
    geometry_geojson: dict[str, Any] | None = None
    recommendations_json: list[str] | None = None

    created_at: datetime

    model_config = {"from_attributes": True}
